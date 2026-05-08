"""Tests for combined group sensor entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_availability.combined_sensor import (
    MAX_STATE_LENGTH,
    CombinedGroupSensor,
    CombinedLowBatteryCountSensor,
    CombinedLowBatterySensor,
    CombinedOfflineEntitiesSensor,
    async_setup_entry,
)
from custom_components.entity_availability.const import (
    CONF_AVAILABILITY_WINDOWS,
    CONF_COMBINED_GROUPS,
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_GROUP_NAME,
    DEFAULT_AVAILABILITY_WINDOWS,
    DOMAIN,
    ENTRY_TYPE_COMBINED,
    ENTRY_TYPE_GROUP,
)
from custom_components.entity_availability.coordinator import (
    EntityAvailabilityCoordinator,
)
from custom_components.entity_availability.models import DeviceState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_group_entry(entry_id: str, name: str, entities: list[str]) -> MockConfigEntry:
    """Return a MockConfigEntry representing a monitor group."""
    return MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title=name,
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_GROUP,
            CONF_GROUP_NAME: name,
            CONF_ENTITIES: entities,
            CONF_AVAILABILITY_WINDOWS: DEFAULT_AVAILABILITY_WINDOWS,
        },
        entry_id=entry_id,
        unique_id=f"{DOMAIN}_{name.lower().replace(' ', '_')}",
    )


def _make_combined_entry(
    entry_id: str, name: str, combined_ids: list[str]
) -> MockConfigEntry:
    """Return a MockConfigEntry representing a combined group."""
    return MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title=name,
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_COMBINED,
            CONF_GROUP_NAME: name,
            CONF_COMBINED_GROUPS: combined_ids,
        },
        entry_id=entry_id,
        unique_id=f"{DOMAIN}_combined_{name.lower().replace(' ', '_')}",
    )


@pytest.fixture
def group_entry_a() -> MockConfigEntry:
    return _make_group_entry(
        "entry_a", "Group A", ["binary_sensor.a1", "binary_sensor.a2"]
    )


@pytest.fixture
def group_entry_b() -> MockConfigEntry:
    return _make_group_entry("entry_b", "Group B", ["binary_sensor.b1"])


@pytest.fixture
def combined_entry(group_entry_a, group_entry_b) -> MockConfigEntry:
    return _make_combined_entry("combined_1", "Combined", ["entry_a", "entry_b"])


@pytest.fixture
def coordinator_a(mock_hass: HomeAssistant, group_entry_a: MockConfigEntry):
    """Coordinator for group A with pre-populated device states."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, group_entry_a)
        coord._device_states = {
            "binary_sensor.a1": DeviceState(
                entity_id="binary_sensor.a1",
                is_offline=False,
            ),
            "binary_sensor.a2": DeviceState(
                entity_id="binary_sensor.a2",
                is_offline=True,
            ),
        }
    return coord


@pytest.fixture
def coordinator_b(mock_hass: HomeAssistant, group_entry_b: MockConfigEntry):
    """Coordinator for group B with pre-populated device states."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, group_entry_b)
        coord._device_states = {
            "binary_sensor.b1": DeviceState(
                entity_id="binary_sensor.b1",
                is_offline=False,
            ),
        }
    return coord


@pytest.fixture
def coordinators(coordinator_a, coordinator_b):
    return [coordinator_a, coordinator_b]


# ---------------------------------------------------------------------------
# CombinedSensorBase: subscription lifecycle
# ---------------------------------------------------------------------------


class TestCombinedSensorBase:
    """Tests for the base subscription/unsubscription mechanism."""

    def _make_sensor(self, hass, entry, coordinators):
        """Instantiate a minimal concrete subclass (CombinedGroupSensor)."""
        return CombinedGroupSensor(
            hass,
            entry,
            "Combined",
            "combined",
            coordinators,
            [c.entry.entry_id for c in coordinators],
        )

    async def test_async_added_subscribes_all_coordinators(
        self, mock_hass, combined_entry, coordinators
    ):
        """async_added_to_hass registers a listener on every coordinator."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._make_sensor(mock_hass, combined_entry, coordinators)

        fired = []

        def _fake_add_listener(callback):
            fired.append(True)
            # Return an unsub callable
            return lambda: None

        for coord in coordinators:
            coord.async_add_listener = _fake_add_listener

        await sensor.async_added_to_hass()
        assert len(fired) == len(coordinators)

    async def test_async_will_remove_calls_unsubs(
        self, mock_hass, combined_entry, coordinators
    ):
        """async_will_remove_from_hass calls every unsub and clears the list."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._make_sensor(mock_hass, combined_entry, coordinators)

        unsub_called = []

        def _unsub():
            unsub_called.append(True)

        # Manually inject unsub callbacks
        sensor._unsub_listeners = [_unsub, _unsub]
        await sensor.async_will_remove_from_hass()

        assert len(unsub_called) == 2
        assert sensor._unsub_listeners == []

    def test_active_coordinators_filters_unloaded(
        self, mock_hass, combined_entry, coordinators
    ):
        """_active_coordinators returns only coordinators still in hass.data."""
        # Only entry_a is loaded
        mock_hass.data[DOMAIN] = {"entry_a": coordinators[0]}
        sensor = self._make_sensor(mock_hass, combined_entry, coordinators)
        active = sensor._active_coordinators()
        assert len(active) == 1
        assert active[0] is coordinators[0]

    def test_active_coordinators_returns_all_when_all_loaded(
        self, mock_hass, combined_entry, coordinators
    ):
        """All coordinators returned when all are loaded."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._make_sensor(mock_hass, combined_entry, coordinators)
        assert len(sensor._active_coordinators()) == 2


# ---------------------------------------------------------------------------
# CombinedGroupSensor
# ---------------------------------------------------------------------------


class TestCombinedGroupSensor:
    """Tests for CombinedGroupSensor."""

    def _sensor(self, hass, entry, coordinators):
        return CombinedGroupSensor(
            hass,
            entry,
            "Combined",
            "combined",
            coordinators,
            [c.entry.entry_id for c in coordinators],
        )

    def test_native_value_sums_offline(self, mock_hass, combined_entry, coordinators):
        """native_value is the total count of unsuppressed offline devices across groups."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        # a2 is offline, all others online
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 1

    def test_native_value_suppressed_excluded(
        self, mock_hass, combined_entry, coordinators
    ):
        """Suppressed offline devices are not counted."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a2"].is_suppressed = True
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 0

    def test_native_value_multiple_groups(
        self, mock_hass, combined_entry, coordinators
    ):
        """Offline devices from multiple groups are summed."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[1]._device_states["binary_sensor.b1"].is_offline = True
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 2

    def test_attributes_breakdown(self, mock_hass, combined_entry, coordinators):
        """extra_state_attributes has groups, totals and offline_entities."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        attrs = sensor.extra_state_attributes

        assert attrs["total_entities"] == 3  # a1, a2, b1
        assert attrs["offline"] == 1  # a2
        assert attrs["online"] == 2
        assert "binary_sensor.a2" in attrs["offline_entities"]
        assert "groups" in attrs
        assert "Group A" in attrs["groups"]
        assert "Group B" in attrs["groups"]

    def test_attributes_missing_groups(self, mock_hass, combined_entry, coordinators):
        """missing_groups attribute present when a source group is not in hass.data."""
        # Only load entry_a
        mock_hass.data[DOMAIN] = {"entry_a": coordinators[0]}
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        attrs = sensor.extra_state_attributes
        assert "missing_groups" in attrs
        assert "entry_b" in attrs["missing_groups"]

    def test_unique_id(self, mock_hass, combined_entry, coordinators):
        """unique_id uses entry_id + suffix."""
        mock_hass.data[DOMAIN] = {}
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.unique_id == "combined_1_combined_summary"


# ---------------------------------------------------------------------------
# CombinedOfflineEntitiesSensor
# ---------------------------------------------------------------------------


class TestCombinedOfflineEntitiesSensor:
    """Tests for CombinedOfflineEntitiesSensor."""

    def _sensor(self, hass, entry, coordinators):
        return CombinedOfflineEntitiesSensor(
            hass,
            entry,
            "Combined",
            "combined",
            coordinators,
            [c.entry.entry_id for c in coordinators],
        )

    def test_native_value_none_when_all_online(
        self, mock_hass, combined_entry, coordinators
    ):
        """Returns 'None' string when no devices are offline."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a2"].is_offline = False
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == "None"

    def test_native_value_uses_friendly_name(
        self, mock_hass, combined_entry, coordinators
    ):
        """Offline device shown with its friendly name."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        mock_hass.states.async_set(
            "binary_sensor.a2", STATE_UNAVAILABLE, {"friendly_name": "Sensor A2"}
        )
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert "Sensor A2" in sensor.native_value

    def test_native_value_truncates_at_255(
        self, mock_hass, combined_entry, coordinators
    ):
        """native_value is truncated to MAX_STATE_LENGTH chars."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        # Add many offline devices with long names
        for i in range(30):
            eid = f"binary_sensor.long_{i:03d}"
            coordinators[0]._device_states[eid] = DeviceState(
                entity_id=eid, is_offline=True
            )
            mock_hass.states.async_set(
                eid,
                STATE_UNAVAILABLE,
                {"friendly_name": f"Very Long Device Name Number {i:03d}"},
            )
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        value = sensor.native_value
        assert len(value) <= MAX_STATE_LENGTH
        assert value.endswith("...")

    def test_native_value_suppressed_excluded(
        self, mock_hass, combined_entry, coordinators
    ):
        """Suppressed devices not shown in offline list."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a2"].is_suppressed = True
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == "None"

    def test_extra_state_attributes(self, mock_hass, combined_entry, coordinators):
        """extra_state_attributes has entities list and count."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        attrs = sensor.extra_state_attributes
        assert "entities" in attrs
        assert "count" in attrs
        assert attrs["count"] == 1
        assert "binary_sensor.a2" in attrs["entities"]


# ---------------------------------------------------------------------------
# CombinedLowBatterySensor
# ---------------------------------------------------------------------------


class TestCombinedLowBatterySensor:
    """Tests for CombinedLowBatterySensor."""

    def _sensor(self, hass, entry, coordinators):
        return CombinedLowBatterySensor(
            hass,
            entry,
            "Combined",
            "combined",
            coordinators,
            [c.entry.entry_id for c in coordinators],
        )

    def test_native_value_none_when_no_low_battery(
        self, mock_hass, combined_entry, coordinators
    ):
        """Returns 'None' when no devices have low battery."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == "None"

    def test_native_value_shows_battery_level(
        self, mock_hass, combined_entry, coordinators
    ):
        """Low-battery devices shown with percentage."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a1"].is_degraded = True
        coordinators[0]._device_states["binary_sensor.a1"].battery_level = 12
        mock_hass.states.async_set(
            "binary_sensor.a1", STATE_ON, {"friendly_name": "Sensor A1"}
        )
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert "Sensor A1 (12%)" in sensor.native_value

    def test_extra_state_attributes(self, mock_hass, combined_entry, coordinators):
        """extra_state_attributes has devices map and count."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a1"].is_degraded = True
        coordinators[0]._device_states["binary_sensor.a1"].battery_level = 8
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        attrs = sensor.extra_state_attributes
        assert attrs["count"] == 1
        assert attrs["devices"]["binary_sensor.a1"] == "8%"


# ---------------------------------------------------------------------------
# CombinedLowBatteryCountSensor
# ---------------------------------------------------------------------------


class TestCombinedLowBatteryCountSensor:
    """Tests for CombinedLowBatteryCountSensor."""

    def _sensor(self, hass, entry, coordinators):
        return CombinedLowBatteryCountSensor(
            hass,
            entry,
            "Combined",
            "combined",
            coordinators,
            [c.entry.entry_id for c in coordinators],
        )

    def test_native_value_zero_when_none(self, mock_hass, combined_entry, coordinators):
        """Returns 0 when no low-battery devices."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 0

    def test_native_value_counts_across_groups(
        self, mock_hass, combined_entry, coordinators
    ):
        """Counts low-battery devices across all groups."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a1"].is_degraded = True
        coordinators[0]._device_states["binary_sensor.a1"].battery_level = 5
        coordinators[1]._device_states["binary_sensor.b1"].is_degraded = True
        coordinators[1]._device_states["binary_sensor.b1"].battery_level = 10
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 2

    def test_native_value_excludes_suppressed(
        self, mock_hass, combined_entry, coordinators
    ):
        """Suppressed low-battery devices not counted."""
        mock_hass.data[DOMAIN] = {
            "entry_a": coordinators[0],
            "entry_b": coordinators[1],
        }
        coordinators[0]._device_states["binary_sensor.a1"].is_degraded = True
        coordinators[0]._device_states["binary_sensor.a1"].battery_level = 5
        coordinators[0]._device_states["binary_sensor.a1"].is_suppressed = True
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.native_value == 0

    def test_unique_id(self, mock_hass, combined_entry, coordinators):
        """unique_id uses entry_id + suffix."""
        mock_hass.data[DOMAIN] = {}
        sensor = self._sensor(mock_hass, combined_entry, coordinators)
        assert sensor.unique_id == "combined_1_combined_low_battery_count"


# ---------------------------------------------------------------------------
# async_setup_entry: coordinator list
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Tests for the combined_sensor.async_setup_entry function."""

    async def test_setup_builds_coordinator_list_from_hass_data(
        self, mock_hass: HomeAssistant, group_entry_a, group_entry_b, combined_entry
    ):
        """Only coordinators present in hass.data[DOMAIN] are used."""
        coord_a = MagicMock(spec=EntityAvailabilityCoordinator)
        coord_a.entry = group_entry_a
        # entry_b not loaded — should be skipped
        mock_hass.data[DOMAIN] = {"entry_a": coord_a}

        group_entry_a.add_to_hass(mock_hass)
        group_entry_b.add_to_hass(mock_hass)
        combined_entry.add_to_hass(mock_hass)

        added = []

        def _fake_add(entities):
            added.extend(entities)

        await async_setup_entry(mock_hass, combined_entry, _fake_add)
        # Sensors were registered
        assert len(added) > 0
