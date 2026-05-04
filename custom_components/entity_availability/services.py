"""Services for Entity Availability."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SUPPRESS = "suppress"
SERVICE_UNSUPPRESS = "unsuppress"

ATTR_ENTITY_ID = "entity_id"
ATTR_GROUP = "group"
ATTR_DURATION = "duration"

SUPPRESS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_GROUP): cv.string,
        vol.Optional(ATTR_DURATION, default=60): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=10080)
        ),
    }
)

UNSUPPRESS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_GROUP): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Entity Availability."""

    if hass.services.has_service(DOMAIN, SERVICE_SUPPRESS):
        return

    async def handle_suppress(call: ServiceCall) -> None:
        """Handle suppress service call."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        group = call.data.get(ATTR_GROUP)
        duration_minutes = call.data[ATTR_DURATION]
        until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

        if not entity_id and not group:
            _LOGGER.warning("Either entity_id or group must be provided")
            return

        if group and not entity_id:
            # Suppress all entities in the named group
            found = False
            for coordinator in hass.data.get(DOMAIN, {}).values():
                if coordinator.group_name == group:
                    found = True
                    for eid in coordinator.monitored_entities:
                        coordinator.suppress_entity(eid, until)
                    coordinator.async_set_updated_data(coordinator.data)
                    _LOGGER.info(
                        "Suppressed all entities in group '%s' until %s",
                        group,
                        until.isoformat(),
                    )
                    return
            if not found:
                _LOGGER.warning("Group '%s' not found", group)
            return

        for coordinator in hass.data.get(DOMAIN, {}).values():
            if entity_id in coordinator.monitored_entities:
                coordinator.suppress_entity(entity_id, until)
                coordinator.async_set_updated_data(coordinator.data)
                _LOGGER.info("Suppressed %s until %s", entity_id, until.isoformat())
                return

        _LOGGER.warning("Entity %s not found in any monitored group", entity_id)

    async def handle_unsuppress(call: ServiceCall) -> None:
        """Handle unsuppress service call."""
        entity_id = call.data.get(ATTR_ENTITY_ID)
        group = call.data.get(ATTR_GROUP)

        if not entity_id and not group:
            _LOGGER.warning("Either entity_id or group must be provided")
            return

        if group and not entity_id:
            # Unsuppress all entities in the named group
            found = False
            for coordinator in hass.data.get(DOMAIN, {}).values():
                if coordinator.group_name == group:
                    found = True
                    for eid in coordinator.monitored_entities:
                        coordinator.unsuppress_entity(eid)
                    coordinator.async_set_updated_data(coordinator.data)
                    _LOGGER.info("Unsuppressed all entities in group '%s'", group)
                    return
            if not found:
                _LOGGER.warning("Group '%s' not found", group)
            return

        for coordinator in hass.data.get(DOMAIN, {}).values():
            if entity_id in coordinator.monitored_entities:
                coordinator.unsuppress_entity(entity_id)
                coordinator.async_set_updated_data(coordinator.data)
                _LOGGER.info("Unsuppressed %s", entity_id)
                return

        _LOGGER.warning("Entity %s not found in any monitored group", entity_id)

    hass.services.async_register(
        DOMAIN, SERVICE_SUPPRESS, handle_suppress, schema=SUPPRESS_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNSUPPRESS, handle_unsuppress, schema=UNSUPPRESS_SCHEMA
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove services when the last config entry is unloaded."""
    hass.services.async_remove(DOMAIN, SERVICE_SUPPRESS)
    hass.services.async_remove(DOMAIN, SERVICE_UNSUPPRESS)
