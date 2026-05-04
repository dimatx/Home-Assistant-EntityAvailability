"""Config flow for Entity Availability integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector

from .const import (
    AVAILABLE_WINDOWS,
    CONF_AVAILABILITY_WINDOWS,
    CONF_BAD_STATES,
    CONF_BATTERY_ENTITY_MAP,
    CONF_BATTERY_THRESHOLD,
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_GROUP_NAME,
    CONF_STALENESS_THRESHOLD,
    DEFAULT_AVAILABILITY_WINDOWS,
    DEFAULT_BAD_STATES,
    DEFAULT_BATTERY_THRESHOLD,
    DEFAULT_COOLDOWN,
    DEFAULT_STALENESS_THRESHOLD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class EntityAvailabilityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Availability."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Group name and entity selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            group_name = user_input[CONF_GROUP_NAME]
            entities = user_input[CONF_ENTITIES]

            if not group_name.strip():
                errors[CONF_GROUP_NAME] = "empty_group_name"
            elif not entities:
                errors[CONF_ENTITIES] = "no_entities"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{group_name.lower().replace(' ', '_')}"
                )
                self._abort_if_unique_id_configured()

                self._data[CONF_GROUP_NAME] = group_name
                self._data[CONF_ENTITIES] = entities
                return await self.async_step_monitoring()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_GROUP_NAME): str,
                vol.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Monitoring settings."""
        if user_input is not None:
            self._data[CONF_BAD_STATES] = user_input[CONF_BAD_STATES]
            self._data[CONF_COOLDOWN] = user_input[CONF_COOLDOWN]
            self._data[CONF_STALENESS_THRESHOLD] = user_input[CONF_STALENESS_THRESHOLD]
            return await self.async_step_advanced()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_BAD_STATES, default=DEFAULT_BAD_STATES
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["unavailable", "unknown"],
                        multiple=True,
                        custom_value=True,
                    )
                ),
                vol.Required(
                    CONF_COOLDOWN, default=DEFAULT_COOLDOWN
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, unit_of_measurement="seconds"
                    )
                ),
                vol.Required(
                    CONF_STALENESS_THRESHOLD, default=DEFAULT_STALENESS_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=1440, step=1, unit_of_measurement="minutes"
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="monitoring",
            data_schema=data_schema,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: Advanced settings."""
        if user_input is not None:
            self._data[CONF_BATTERY_THRESHOLD] = user_input[CONF_BATTERY_THRESHOLD]
            self._data[CONF_AVAILABILITY_WINDOWS] = user_input[
                CONF_AVAILABILITY_WINDOWS
            ]

            if self._data[CONF_BATTERY_THRESHOLD] > 0:
                return await self.async_step_battery_mapping()

            self._data[CONF_BATTERY_ENTITY_MAP] = {}
            return self.async_create_entry(
                title=self._data[CONF_GROUP_NAME],
                data=self._data,
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_BATTERY_THRESHOLD, default=DEFAULT_BATTERY_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=100, step=1, unit_of_measurement="%"
                    )
                ),
                vol.Required(
                    CONF_AVAILABILITY_WINDOWS, default=DEFAULT_AVAILABILITY_WINDOWS
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=AVAILABLE_WINDOWS,
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="advanced",
            data_schema=data_schema,
        )

    async def async_step_battery_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: Battery entity mapping."""
        if user_input is not None:
            # Build full map: entities in user_input have a battery, others don't
            battery_map = {}
            for entity_id in self._data[CONF_ENTITIES]:
                battery_map[entity_id] = user_input.get(entity_id, "")
            self._data[CONF_BATTERY_ENTITY_MAP] = battery_map
            return self.async_create_entry(
                title=self._data[CONF_GROUP_NAME],
                data=self._data,
            )

        schema_dict: dict[Any, Any] = {}
        for entity_id in self._data[CONF_ENTITIES]:
            detected = self._detect_battery_entity(entity_id)
            if detected:
                schema_dict[vol.Optional(entity_id, default=detected)] = (
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    )
                )
            else:
                schema_dict[vol.Optional(entity_id)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

        return self.async_show_form(
            step_id="battery_mapping",
            data_schema=vol.Schema(schema_dict),
        )

    def _detect_battery_entity(self, entity_id: str) -> str:
        """Auto-detect battery entity for a monitored entity."""
        ent_reg = er.async_get(self.hass)
        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            for ent in er.async_entries_for_device(ent_reg, entry.device_id):
                if ent.entity_id == entity_id:
                    continue
                if ent.original_device_class == SensorDeviceClass.BATTERY or (
                    ent.device_class == SensorDeviceClass.BATTERY
                ):
                    return ent.entity_id

        parts = entity_id.split(".", 1)
        if len(parts) == 2:
            battery_entity = f"sensor.{parts[1]}_battery"
            if self.hass.states.get(battery_entity):
                return battery_entity

        return ""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> EntityAvailabilityOptionsFlow:
        """Get the options flow for this handler."""
        return EntityAvailabilityOptionsFlow()


class EntityAvailabilityOptionsFlow(OptionsFlow):
    """Handle options flow for Entity Availability."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            self._data = {**self.config_entry.data, **user_input}

            if self._data.get(CONF_BATTERY_THRESHOLD, 0) > 0:
                return await self.async_step_battery_mapping()

            self._data[CONF_BATTERY_ENTITY_MAP] = {}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self._data
            )
            return self.async_create_entry(title="", data={})

        current = self.config_entry.data

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENTITIES, default=current.get(CONF_ENTITIES, [])
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(multiple=True)
                ),
                vol.Required(
                    CONF_BAD_STATES,
                    default=current.get(CONF_BAD_STATES, DEFAULT_BAD_STATES),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["unavailable", "unknown"],
                        multiple=True,
                        custom_value=True,
                    )
                ),
                vol.Required(
                    CONF_COOLDOWN, default=current.get(CONF_COOLDOWN, DEFAULT_COOLDOWN)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, unit_of_measurement="seconds"
                    )
                ),
                vol.Required(
                    CONF_STALENESS_THRESHOLD,
                    default=current.get(
                        CONF_STALENESS_THRESHOLD, DEFAULT_STALENESS_THRESHOLD
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=1440, step=1, unit_of_measurement="minutes"
                    )
                ),
                vol.Required(
                    CONF_BATTERY_THRESHOLD,
                    default=current.get(
                        CONF_BATTERY_THRESHOLD, DEFAULT_BATTERY_THRESHOLD
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=100, step=1, unit_of_measurement="%"
                    )
                ),
                vol.Required(
                    CONF_AVAILABILITY_WINDOWS,
                    default=current.get(
                        CONF_AVAILABILITY_WINDOWS, DEFAULT_AVAILABILITY_WINDOWS
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=AVAILABLE_WINDOWS,
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )

    async def async_step_battery_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Battery entity mapping step in options flow."""
        if user_input is not None:
            entities = self._data.get(
                CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
            )
            battery_map = {}
            for entity_id in entities:
                battery_map[entity_id] = user_input.get(entity_id, "")
            self._data[CONF_BATTERY_ENTITY_MAP] = battery_map
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self._data
            )
            return self.async_create_entry(title="", data={})

        existing_map = self.config_entry.data.get(CONF_BATTERY_ENTITY_MAP, {})
        entities = self._data.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )

        schema_dict: dict[Any, Any] = {}
        for entity_id in entities:
            default = existing_map.get(entity_id, "")
            if not default:
                default = self._detect_battery_entity(entity_id)
            if default:
                schema_dict[vol.Optional(entity_id, default=default)] = (
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    )
                )
            else:
                schema_dict[vol.Optional(entity_id)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

        return self.async_show_form(
            step_id="battery_mapping",
            data_schema=vol.Schema(schema_dict),
        )

    def _detect_battery_entity(self, entity_id: str) -> str:
        """Auto-detect battery entity for a monitored entity."""
        ent_reg = er.async_get(self.hass)
        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            for ent in er.async_entries_for_device(ent_reg, entry.device_id):
                if ent.entity_id == entity_id:
                    continue
                if ent.original_device_class == SensorDeviceClass.BATTERY or (
                    ent.device_class == SensorDeviceClass.BATTERY
                ):
                    return ent.entity_id

        parts = entity_id.split(".", 1)
        if len(parts) == 2:
            battery_entity = f"sensor.{parts[1]}_battery"
            if self.hass.states.get(battery_entity):
                return battery_entity

        return ""
