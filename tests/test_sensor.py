"""Tests for Entity Availability sensor entities."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.entity_availability.coordinator import EntityAvailabilityCoordinator
from custom_components.entity_availability.models import DeviceState
from custom_components.entity_availability.sensor import (
    AvailabilitySensor,
    DegradedDevicesSensor,
    GroupSummarySensor,
    MAX_STATE_LENGTH,
    OfflineCountSensor,
    OfflineDevicesSensor,
)


@pytest.fixture
def mock_coordinator(mock_hass: HomeAssistant, mock_config_entry):
    """Create a mock coordinator with test device states."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, mock_config_entry)
        coord._device_states = {
            "binary_sensor.device_a": DeviceState(
                entity_id="binary_sensor.device_a",
                is_offline=False,
            ),
            "binary_sensor.device_b": DeviceState(
                entity_id="binary_sensor.device_b",
                is_offline=True,
                offline_since=datetime.now(timezone.utc) - timedelta(minutes=5),
            ),
            "binary_sensor.device_c": DeviceState(
                entity_id="binary_sensor.device_c",
                is_offline=False,
            ),
        }
    return coord


class TestOfflineCountSensor:
    """Tests for OfflineCountSensor."""

    def test_native_value_counts_offline(self, mock_coordinator, mock_hass):
        """Test native_value returns count of offline non-suppressed devices."""
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == 1

    def test_native_value_excludes_suppressed(self, mock_coordinator, mock_hass):
        """Test that suppressed devices are not counted."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_suppressed = True
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == 0

    def test_native_value_zero_when_all_online(self, mock_coordinator, mock_hass):
        """Test zero offline count when all devices are online."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = False
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == 0

    def test_native_value_counts_multiple_offline(self, mock_coordinator, mock_hass):
        """Test counting multiple offline devices."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_offline = True
        mock_coordinator._device_states["binary_sensor.device_a"].offline_since = (
            datetime.now(timezone.utc)
        )
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == 2

    def test_extra_state_attributes(self, mock_coordinator, mock_hass):
        """Test extra attributes contain offline device info."""
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert "binary_sensor.device_b" in attrs
        assert attrs["binary_sensor.device_b"]["offline"] is True

    def test_unique_id(self, mock_coordinator, mock_hass):
        """Test unique_id format."""
        sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        assert sensor.unique_id == "test_entry_id_offline_count"


class TestOfflineDevicesSensor:
    """Tests for OfflineDevicesSensor."""

    def test_native_value_shows_friendly_names(self, mock_coordinator, mock_hass):
        """Test that friendly names are shown for offline devices."""
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        # device_b is offline and has friendly_name "Device B"
        assert sensor.native_value == "Device B"

    def test_native_value_none_when_all_online(self, mock_coordinator, mock_hass):
        """Test 'None' string when no devices offline."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = False
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == "None"

    def test_native_value_truncation(self, mock_coordinator, mock_hass):
        """Test that very long lists are truncated."""
        # Add many offline devices with long names
        for i in range(50):
            entity_id = f"binary_sensor.device_{i:03d}"
            mock_coordinator._device_states[entity_id] = DeviceState(
                entity_id=entity_id,
                is_offline=True,
            )
            mock_hass.states.async_set(
                entity_id, STATE_UNAVAILABLE,
                {"friendly_name": f"Very Long Device Name Number {i:03d}"},
            )

        # Add entity to monitored list so it's accessible
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        value = sensor.native_value
        assert len(value) <= MAX_STATE_LENGTH
        assert value.endswith("...")

    def test_native_value_excludes_suppressed(self, mock_coordinator, mock_hass):
        """Test suppressed devices excluded from list."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_suppressed = True
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == "None"

    def test_extra_state_attributes_has_entities_list(
        self, mock_coordinator, mock_hass
    ):
        """Test extra attributes contain full entity list."""
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert "entities" in attrs
        assert "count" in attrs
        assert attrs["count"] == 1
        assert "binary_sensor.device_b" in attrs["entities"]

    def test_friendly_name_fallback(self, mock_coordinator, mock_hass):
        """Test fallback friendly name when no friendly_name attribute."""
        # Remove the state so it falls back to entity_id parsing
        mock_hass.states.async_remove("binary_sensor.device_b")
        sensor = OfflineDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        # Fallback: entity_id.split(".")[-1].replace("_", " ").title()
        assert sensor.native_value == "Device B"


class TestDegradedDevicesSensor:
    """Tests for DegradedDevicesSensor (Low Battery)."""

    def test_native_value_lists_low_battery(self, mock_coordinator, mock_hass):
        """Test native_value returns low battery device names."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_degraded = True
        mock_coordinator._device_states["binary_sensor.device_a"].battery_level = 15
        sensor = DegradedDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert "Device A (15%)" in sensor.native_value

    def test_native_value_empty_when_none_degraded(self, mock_coordinator, mock_hass):
        """Test empty string when no devices degraded."""
        sensor = DegradedDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == ""

    def test_excludes_suppressed_degraded(self, mock_coordinator, mock_hass):
        """Test suppressed degraded devices are excluded."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_degraded = True
        mock_coordinator._device_states["binary_sensor.device_a"].battery_level = 10
        mock_coordinator._device_states["binary_sensor.device_a"].is_suppressed = True
        sensor = DegradedDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == ""

    def test_extra_state_attributes_shows_battery(self, mock_coordinator, mock_hass):
        """Test that battery levels are reported in attributes."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_degraded = True
        mock_coordinator._device_states["binary_sensor.device_a"].battery_level = 15
        sensor = DegradedDevicesSensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert "devices" in attrs
        assert "count" in attrs
        assert attrs["count"] == 1
        assert attrs["devices"]["binary_sensor.device_a"] == "15%"


class TestAvailabilitySensor:
    """Tests for AvailabilitySensor."""

    def test_native_value_with_data(self, mock_coordinator, mock_hass):
        """Test availability percentage calculation."""
        now = datetime.now(timezone.utc)
        storage = mock_coordinator.availability_storage

        # Fill data for all entities - 24 hours of 100% for "today"
        for entity_id in mock_coordinator.monitored_entities:
            for i in range(24):
                t = now - timedelta(hours=i)
                storage.record_online(entity_id, 3600.0, t)

        sensor = AvailabilitySensor(
            mock_coordinator, "Test Group", "test_group", "today", "test_entry_id"
        )
        sensor.hass = mock_hass
        value = sensor.native_value
        assert value == 100.0

    def test_native_value_none_insufficient_data(self, mock_coordinator, mock_hass):
        """Test returns None when insufficient data."""
        sensor = AvailabilitySensor(
            mock_coordinator, "Test Group", "test_group", "today", "test_entry_id"
        )
        sensor.hass = mock_hass
        # No data recorded
        assert sensor.native_value is None

    def test_native_value_excludes_suppressed(self, mock_coordinator, mock_hass):
        """Test suppressed devices excluded from availability calc."""
        now = datetime.now(timezone.utc)
        storage = mock_coordinator.availability_storage

        # Only fill data for device_a
        for i in range(24):
            t = now - timedelta(hours=i)
            storage.record_online("binary_sensor.device_a", 3600.0, t)

        # Suppress device_a - so it won't be counted
        mock_coordinator._device_states["binary_sensor.device_a"].is_suppressed = True

        sensor = AvailabilitySensor(
            mock_coordinator, "Test Group", "test_group", "today", "test_entry_id"
        )
        sensor.hass = mock_hass
        # device_b and device_c have no data, so None for them
        # device_a is suppressed, so excluded
        assert sensor.native_value is None

    def test_extra_state_attributes_per_device(self, mock_coordinator, mock_hass):
        """Test per_device breakdown in attributes."""
        sensor = AvailabilitySensor(
            mock_coordinator, "Test Group", "test_group", "today", "test_entry_id"
        )
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert "per_device" in attrs

    def test_unique_id_includes_window(self, mock_coordinator, mock_hass):
        """Test unique_id includes window identifier."""
        sensor = AvailabilitySensor(
            mock_coordinator, "Test Group", "test_group", "7d", "test_entry_id"
        )
        assert sensor.unique_id == "test_entry_id_availability_7d"


class TestGroupSummarySensor:
    """Tests for GroupSummarySensor."""

    def test_native_value_is_total_count(self, mock_coordinator, mock_hass):
        """Test native_value returns total entity count."""
        sensor = GroupSummarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.native_value == 3

    def test_attributes_breakdown(self, mock_coordinator, mock_hass):
        """Test extra attributes contain full breakdown."""
        mock_coordinator._device_states["binary_sensor.device_a"].battery_level = 85
        sensor = GroupSummarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert attrs["total_entities"] == 3
        assert attrs["offline"] == 1  # device_b
        assert attrs["online"] == 2
        assert attrs["suppressed"] == 0
        assert attrs["battery_powered"] == 1  # device_a has battery_level
        assert attrs["low_battery"] == 0

    def test_attributes_with_suppressed(self, mock_coordinator, mock_hass):
        """Test that suppressed entities are counted correctly."""
        mock_coordinator._device_states["binary_sensor.device_c"].is_suppressed = True
        sensor = GroupSummarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert attrs["suppressed"] == 1
        assert attrs["online"] == 1  # total(3) - offline(1) - suppressed(1) = 1

    def test_attributes_low_battery_count(self, mock_coordinator, mock_hass):
        """Test low battery count in attributes."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_degraded = True
        mock_coordinator._device_states["binary_sensor.device_a"].battery_level = 10
        sensor = GroupSummarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert attrs["low_battery"] == 1
        assert attrs["battery_powered"] == 1

    def test_unique_id(self, mock_coordinator, mock_hass):
        """Test unique_id format."""
        sensor = GroupSummarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        assert sensor.unique_id == "test_entry_id_group_summary"
