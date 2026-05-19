"""Binary sensor platform for Entity Availability."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_ENTRY_TYPE, CONF_GROUP_NAME, DOMAIN, ENTRY_TYPE_COMBINED
from .coordinator import EntityAvailabilityCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Entity Availability binary sensors."""
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_COMBINED:
        from .combined_binary_sensor import async_setup_entry as _combined

        await _combined(hass, entry, async_add_entities)
        return

    coordinator: EntityAvailabilityCoordinator = hass.data[DOMAIN][entry.entry_id]
    group_name = entry.data[CONF_GROUP_NAME]
    group_slug = group_name.lower().replace(" ", "_")

    async_add_entities(
        [
            AnyOfflineBinarySensor(coordinator, group_name, group_slug, entry.entry_id),
        ]
    )


class AnyOfflineBinarySensor(
    CoordinatorEntity[EntityAvailabilityCoordinator], BinarySensorEntity
):
    """Binary sensor: ON when at least one entity is offline (problem detected)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EntityAvailabilityCoordinator,
        group_name: str,
        group_slug: str,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_any_offline"
        self.entity_id = f"binary_sensor.entity_availability_{group_slug}_any_offline"
        self._attr_name = "Any Offline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=f"Entity Availability - {group_name}",
            manufacturer="Entity Availability",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return True if any non-suppressed entity is offline."""
        for device in self.coordinator.device_states.values():
            if device.is_suppressed:
                continue
            if device.is_offline:
                return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return offline entity details."""
        offline_entities = [
            d.entity_id
            for d in self.coordinator.device_states.values()
            if d.is_offline and not d.is_suppressed
        ]
        return {
            "offline_entities": offline_entities,
            "offline_count": len(offline_entities),
        }
