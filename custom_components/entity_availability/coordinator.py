"""DataUpdateCoordinator for Entity Availability."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_BAD_STATES,
    CONF_BATTERY_ENTITY_MAP,
    CONF_BATTERY_THRESHOLD,
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_STALENESS_THRESHOLD,
    DEFAULT_BAD_STATES,
    DEFAULT_BATTERY_THRESHOLD,
    DEFAULT_COOLDOWN,
    DEFAULT_STALENESS_THRESHOLD,
    SCAN_INTERVAL,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .models import EntityAvailabilityData, DeviceState
from .storage import AvailabilityStorage

_LOGGER = logging.getLogger(__name__)

# Debounce state changes - wait this long before processing
_STATE_CHANGE_DEBOUNCE = 2  # seconds

# Save storage every N updates (5 min = 10 updates at 30s interval)
_SAVE_INTERVAL_UPDATES = 10


class EntityAvailabilityCoordinator(DataUpdateCoordinator[EntityAvailabilityData]):
    """Coordinator that monitors device states and tracks availability."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Entity Availability - {entry.title}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
            config_entry=entry,
        )
        self.entry = entry
        self._entities: list[str] = entry.data.get(CONF_ENTITIES, [])
        self._bad_states: list[str] = entry.data.get(
            CONF_BAD_STATES, DEFAULT_BAD_STATES
        )
        self._cooldown: int = entry.data.get(CONF_COOLDOWN, DEFAULT_COOLDOWN)
        self._staleness_threshold: int = entry.data.get(
            CONF_STALENESS_THRESHOLD, DEFAULT_STALENESS_THRESHOLD
        )
        self._battery_threshold: int = entry.data.get(
            CONF_BATTERY_THRESHOLD, DEFAULT_BATTERY_THRESHOLD
        )
        self._availability_storage = AvailabilityStorage()
        self._store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}_{entry.entry_id}"
        )
        self._last_update: datetime | None = None
        self._unsub_state_change: CALLBACK_TYPE | None = None
        self._debounce_cancel: CALLBACK_TYPE | None = None
        self._device_states: dict[str, DeviceState] = {}
        self._suppressed: dict[str, datetime | None] = {}
        self._update_count: int = 0
        self._dirty: bool = False

    @property
    def monitored_entities(self) -> list[str]:
        """Return list of monitored entity IDs."""
        return self._entities

    @property
    def device_states(self) -> dict[str, DeviceState]:
        """Return current device states."""
        return self._device_states

    @property
    def availability_storage(self) -> AvailabilityStorage:
        """Return the availability storage."""
        return self._availability_storage

    @property
    def group_name(self) -> str:
        """Return the group name."""
        return self.entry.title

    def suppress_entity(self, entity_id: str, until: datetime | None = None) -> None:
        """Suppress alerts for an entity."""
        if entity_id in self._device_states:
            self._device_states[entity_id].is_suppressed = True
            self._device_states[entity_id].suppress_until = until
        self._suppressed[entity_id] = until
        self._dirty = True

    def unsuppress_entity(self, entity_id: str) -> None:
        """Resume monitoring for an entity."""
        if entity_id in self._device_states:
            self._device_states[entity_id].is_suppressed = False
            self._device_states[entity_id].suppress_until = None
        self._suppressed.pop(entity_id, None)
        self._dirty = True

    async def async_config_entry_first_refresh(self) -> None:
        """Load stored data and do first refresh."""
        await self._async_load_storage()
        await super().async_config_entry_first_refresh()
        self._setup_state_listeners()

    async def async_shutdown(self) -> None:
        """Clean up on unload."""
        if self._unsub_state_change is not None:
            self._unsub_state_change()
            self._unsub_state_change = None
        if self._debounce_cancel is not None:
            self._debounce_cancel()
            self._debounce_cancel = None
        # Final save
        if self._dirty:
            await self._async_save_storage()

    async def _async_load_storage(self) -> None:
        """Load persisted availability data."""
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            if "availability" in stored:
                self._availability_storage = AvailabilityStorage.from_dict(
                    stored["availability"]
                )
            if "suppressed" in stored:
                for entity_id, until_str in stored["suppressed"].items():
                    if until_str:
                        try:
                            until = datetime.fromisoformat(until_str)
                            if until > datetime.now(timezone.utc):
                                self._suppressed[entity_id] = until
                        except (ValueError, TypeError):
                            pass

    async def _async_save_storage(self) -> None:
        """Persist availability data."""
        data = {
            "availability": self._availability_storage.to_dict(),
            "suppressed": {
                entity_id: until.isoformat() if until else None
                for entity_id, until in self._suppressed.items()
            },
        }
        await self._store.async_save(data)
        self._dirty = False

    @callback
    def _setup_state_listeners(self) -> None:
        """Set up state change listeners for monitored entities."""
        if self._unsub_state_change is not None:
            self._unsub_state_change()

        self._unsub_state_change = async_track_state_change_event(
            self.hass, self._entities, self._handle_state_change
        )

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """Handle state change for a monitored entity (debounced)."""
        # Cancel any pending debounce timer
        if self._debounce_cancel is not None:
            self._debounce_cancel()

        @callback
        def _debounced_refresh(_now: Any) -> None:
            """Trigger a coordinator refresh after debounce."""
            self._debounce_cancel = None
            self.hass.async_create_task(self.async_request_refresh())

        # Schedule a debounced refresh
        self._debounce_cancel = async_call_later(
            self.hass, _STATE_CHANGE_DEBOUNCE, _debounced_refresh
        )

    async def _async_update_data(self) -> EntityAvailabilityData:
        """Update device states and availability."""
        now = datetime.now(timezone.utc)
        elapsed = (
            (now - self._last_update).total_seconds()
            if self._last_update
            else SCAN_INTERVAL
        )
        self._last_update = now

        # Cap elapsed to avoid huge jumps after HA restart or sleep
        # Maximum reasonable elapsed is 2x the scan interval
        elapsed = min(elapsed, SCAN_INTERVAL * 2)

        for entity_id in self._entities:
            state = self.hass.states.get(entity_id)
            if entity_id not in self._device_states:
                self._device_states[entity_id] = DeviceState(entity_id=entity_id)

            device = self._device_states[entity_id]

            # Restore suppression from loaded data
            if entity_id in self._suppressed and not device.is_suppressed:
                device.is_suppressed = True
                device.suppress_until = self._suppressed[entity_id]

            # Check suppression expiry
            if device.is_suppressed and device.suppress_until:
                if now >= device.suppress_until:
                    device.is_suppressed = False
                    device.suppress_until = None
                    self._suppressed.pop(entity_id, None)

            # Skip suppressed devices for availability tracking
            if device.is_suppressed:
                continue

            # Determine if device is in a bad state
            is_bad = state is None or state.state in self._bad_states

            # Battery check
            device.battery_level = self._get_battery_level(entity_id)
            battery_low = (
                self._battery_threshold > 0
                and device.battery_level is not None
                and device.battery_level < self._battery_threshold
            )

            # Staleness check
            is_stale = False
            if self._staleness_threshold > 0 and state and state.last_changed:
                age = (now - state.last_changed).total_seconds() / 60
                if age > self._staleness_threshold:
                    is_stale = True
                device.last_changed = state.last_changed

            # Cooldown logic
            if is_bad:
                if device.cooldown_start is None:
                    device.cooldown_start = now
                cooldown_elapsed = (now - device.cooldown_start).total_seconds()
                if cooldown_elapsed >= self._cooldown:
                    if not device.is_offline:
                        device.is_offline = True
                        device.offline_since = device.cooldown_start
                else:
                    # Still in cooldown - record as online
                    self._availability_storage.record_online(entity_id, elapsed, now)
            else:
                # Device is online
                if device.is_offline:
                    device.last_recovery = now
                    if device.offline_since:
                        device.last_downtime_seconds = (
                            now - device.offline_since
                        ).total_seconds()
                    device.is_offline = False
                    device.offline_since = None
                device.cooldown_start = None
                self._availability_storage.record_online(entity_id, elapsed, now)

            # Record offline time (offline seconds are implicitly tracked
            # as total_seconds - online_seconds in the bucket)
            if device.is_offline:
                self._availability_storage.record_offline(entity_id, elapsed, now)

            # Degraded = not offline but battery low or stale
            device.is_degraded = (not device.is_offline) and (battery_low or is_stale)

        # Mark as dirty; save periodically (every ~5 min)
        self._dirty = True
        self._update_count += 1
        if self._update_count >= _SAVE_INTERVAL_UPDATES:
            self._update_count = 0
            await self._async_save_storage()

        return EntityAvailabilityData(
            devices=self._device_states,
            buckets=self._availability_storage.buckets,
        )

    def _get_battery_level(self, entity_id: str) -> int | None:
        """Get battery level for an entity using configured mapping or auto-detection."""
        battery_map = self.entry.data.get(CONF_BATTERY_ENTITY_MAP)
        if battery_map is not None and entity_id in battery_map:
            mapped = battery_map[entity_id]
            if not mapped:
                return None
            bat_state = self.hass.states.get(mapped)
            if bat_state and bat_state.state not in ("unavailable", "unknown", None):
                return self._parse_battery_state(bat_state.state)
            return None

        # Auto-detection fallback: no map or entity not in map
        state = self.hass.states.get(entity_id)
        if state and state.attributes:
            battery = state.attributes.get("battery_level") or state.attributes.get(
                "battery"
            )
            if battery is not None:
                return self._parse_battery_state(str(battery).replace("%", ""))

        battery_from_registry = self._get_battery_from_device_registry(entity_id)
        if battery_from_registry is not None:
            return battery_from_registry

        parts = entity_id.split(".", 1)
        if len(parts) == 2:
            battery_entity = f"sensor.{parts[1]}_battery"
            bat_state = self.hass.states.get(battery_entity)
            if bat_state and bat_state.state not in ("unavailable", "unknown", None):
                return self._parse_battery_state(bat_state.state)

        return None

    @staticmethod
    def _parse_battery_state(value: str) -> int | None:
        """Parse a battery state string into an integer level."""
        if value.lower() == "low":
            return 0
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _get_battery_from_device_registry(self, entity_id: str) -> int | None:
        """Look up battery level via the device registry."""
        ent_reg = er.async_get(self.hass)

        entry = ent_reg.async_get(entity_id)
        if not entry or not entry.device_id:
            return None

        # Find all entities on the same device with battery device class
        for ent in er.async_entries_for_device(ent_reg, entry.device_id):
            if ent.entity_id == entity_id:
                continue
            if ent.original_device_class == SensorDeviceClass.BATTERY or (
                ent.device_class == SensorDeviceClass.BATTERY
            ):
                bat_state = self.hass.states.get(ent.entity_id)
                if bat_state and bat_state.state not in (
                    "unavailable",
                    "unknown",
                    None,
                ):
                    level = self._parse_battery_state(bat_state.state)
                    if level is not None:
                        return level

        return None
