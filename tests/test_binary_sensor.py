"""Tests for Entity Availability binary sensor."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.entity_availability.binary_sensor import AnyOfflineBinarySensor
from custom_components.entity_availability.coordinator import EntityAvailabilityCoordinator
from custom_components.entity_availability.models import DeviceState


@pytest.fixture
def mock_coordinator(mock_hass: HomeAssistant, mock_config_entry):
    """Create coordinator with device states for binary sensor tests."""
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
                is_offline=False,
            ),
            "binary_sensor.device_c": DeviceState(
                entity_id="binary_sensor.device_c",
                is_offline=False,
            ),
        }
    return coord


class TestAnyOfflineBinarySensor:
    """Tests for AnyOfflineBinarySensor."""

    def test_is_off_when_all_online(self, mock_coordinator, mock_hass):
        """Test is_on is False when all entities are online."""
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.is_on is False

    def test_is_on_when_any_offline(self, mock_coordinator, mock_hass):
        """Test is_on is True when any entity is offline."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = True
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.is_on is True

    def test_is_on_when_multiple_offline(self, mock_coordinator, mock_hass):
        """Test is_on is True when multiple entities are offline."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_offline = True
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = True
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.is_on is True

    def test_suppressed_excluded(self, mock_coordinator, mock_hass):
        """Test suppressed offline entities don't trigger."""
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = True
        mock_coordinator._device_states["binary_sensor.device_b"].is_suppressed = True
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.is_on is False

    def test_is_off_with_no_devices(self, mock_coordinator, mock_hass):
        """Test is_on is False when no device states exist."""
        mock_coordinator._device_states = {}
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        assert sensor.is_on is False

    def test_unique_id(self, mock_coordinator, mock_hass):
        """Test unique_id format."""
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        assert sensor.unique_id == "test_entry_id_any_offline"

    def test_device_class_is_problem(self, mock_coordinator, mock_hass):
        """Test device class is PROBLEM."""
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM

    def test_extra_state_attributes(self, mock_coordinator, mock_hass):
        """Test extra attributes list offline entities."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_offline = True
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = True
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert attrs["offline_count"] == 2
        assert "binary_sensor.device_a" in attrs["offline_entities"]
        assert "binary_sensor.device_b" in attrs["offline_entities"]

    def test_extra_state_attributes_excludes_suppressed(self, mock_coordinator, mock_hass):
        """Test suppressed entities excluded from attributes."""
        mock_coordinator._device_states["binary_sensor.device_a"].is_offline = True
        mock_coordinator._device_states["binary_sensor.device_a"].is_suppressed = True
        mock_coordinator._device_states["binary_sensor.device_b"].is_offline = True
        sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "test_entry_id")
        sensor.hass = mock_hass
        attrs = sensor.extra_state_attributes
        assert attrs["offline_count"] == 1
        assert "binary_sensor.device_a" not in attrs["offline_entities"]
        assert "binary_sensor.device_b" in attrs["offline_entities"]
