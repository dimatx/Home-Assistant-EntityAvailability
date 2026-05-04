"""Tests for the Entity Availability coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_availability.const import (
    CONF_AVAILABILITY_WINDOWS,
    CONF_BAD_STATES,
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
    SCAN_INTERVAL,
)
from custom_components.entity_availability.coordinator import EntityAvailabilityCoordinator
from custom_components.entity_availability.models import DeviceState


@pytest.fixture
def coordinator(hass: HomeAssistant, mock_config_entry) -> EntityAvailabilityCoordinator:
    """Create a coordinator with mocked storage."""
    with patch.object(
        EntityAvailabilityCoordinator,
        "_async_load_storage",
        new_callable=AsyncMock,
    ), patch.object(
        EntityAvailabilityCoordinator,
        "_async_save_storage",
        new_callable=AsyncMock,
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
    return coord


async def test_coordinator_init(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test coordinator initializes with correct config values."""
    coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
    assert coord.monitored_entities == [
        "binary_sensor.device_a",
        "binary_sensor.device_b",
        "binary_sensor.device_c",
    ]
    assert coord._bad_states == DEFAULT_BAD_STATES
    assert coord._cooldown == DEFAULT_COOLDOWN
    assert coord._staleness_threshold == DEFAULT_STALENESS_THRESHOLD
    assert coord._battery_threshold == DEFAULT_BATTERY_THRESHOLD
    assert coord.group_name == "Test Group"


async def test_state_change_online_device(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that online device is tracked correctly."""
    hass = mock_hass
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        data = await coord._async_update_data()

    # All devices are STATE_ON, so none should be offline
    for entity_id, device in coord.device_states.items():
        assert device.is_offline is False
        assert device.is_degraded is False


async def test_cooldown_device_stays_online_within_cooldown(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test device remains online during cooldown period."""
    hass = mock_hass
    # Set device_a to unavailable
    hass.states.async_set("binary_sensor.device_a", STATE_UNAVAILABLE)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None

        # First update - starts cooldown
        await coord._async_update_data()
        device_a = coord.device_states["binary_sensor.device_a"]
        assert device_a.cooldown_start is not None
        assert device_a.is_offline is False  # Still within cooldown


async def test_cooldown_device_goes_offline_after_cooldown(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test device goes offline after cooldown expires."""
    hass = mock_hass
    hass.states.async_set("binary_sensor.device_a", STATE_UNAVAILABLE)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None

        # First update - sets cooldown_start
        await coord._async_update_data()
        device_a = coord.device_states["binary_sensor.device_a"]
        assert device_a.is_offline is False

        # Simulate time passing beyond cooldown (60s default)
        device_a.cooldown_start = datetime.now(timezone.utc) - timedelta(seconds=61)
        await coord._async_update_data()

        assert device_a.is_offline is True
        assert device_a.offline_since is not None


async def test_device_recovery_after_offline(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test device recovery is tracked correctly."""
    hass = mock_hass
    hass.states.async_set("binary_sensor.device_a", STATE_UNAVAILABLE)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None

        # Force device offline
        await coord._async_update_data()
        device_a = coord.device_states["binary_sensor.device_a"]
        device_a.cooldown_start = datetime.now(timezone.utc) - timedelta(seconds=120)
        await coord._async_update_data()
        assert device_a.is_offline is True

        # Now bring it back online
        hass.states.async_set("binary_sensor.device_a", STATE_ON)
        await coord._async_update_data()
        assert device_a.is_offline is False
        assert device_a.last_recovery is not None
        assert device_a.last_downtime_seconds is not None
        assert device_a.cooldown_start is None


async def test_staleness_detection(
    mock_hass: HomeAssistant, mock_config_data
) -> None:
    """Test that stale devices are detected as degraded."""
    hass = mock_hass
    # Override staleness threshold to 10 minutes
    staleness_config_data = dict(mock_config_data)
    staleness_config_data[CONF_STALENESS_THRESHOLD] = 10

    staleness_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Group",
        data=staleness_config_data,
        entry_id="test_entry_staleness",
        unique_id=f"{DOMAIN}_test_staleness",
    )

    # Set last_changed to 15 minutes ago
    old_time = datetime.now(timezone.utc) - timedelta(minutes=15)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, staleness_entry)
        coord._last_update = None

        # Set state then replace with a State that has old last_changed
        hass.states.async_set(
            "binary_sensor.device_a",
            STATE_ON,
            {"friendly_name": "Device A"},
        )
        hass.states._states["binary_sensor.device_a"] = State(
            "binary_sensor.device_a",
            STATE_ON,
            {"friendly_name": "Device A"},
            last_changed=old_time,
            last_updated=old_time,
        )

        await coord._async_update_data()

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.is_degraded is True
    assert device_a.is_offline is False


async def test_battery_detection_from_attributes(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test battery level detection from entity attributes."""
    hass = mock_hass
    hass.states.async_set(
        "binary_sensor.device_a",
        STATE_ON,
        {"friendly_name": "Device A", "battery_level": 15},
    )

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.battery_level == 15
    assert device_a.is_degraded is True  # battery < 20 threshold


async def test_battery_detection_from_companion_entity(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test battery level detection from companion battery entity."""
    hass = mock_hass
    # No battery in attributes
    hass.states.async_set(
        "binary_sensor.device_a",
        STATE_ON,
        {"friendly_name": "Device A"},
    )
    # Add companion battery entity
    hass.states.async_set("sensor.device_a_battery", "10")

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.battery_level == 10
    assert device_a.is_degraded is True


async def test_suppression_skips_availability_tracking(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that suppressed devices are skipped during update."""
    hass = mock_hass
    hass.states.async_set("binary_sensor.device_a", STATE_UNAVAILABLE)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None

        # Initialize device states
        await coord._async_update_data()

        # Suppress device_a
        coord.suppress_entity(
            "binary_sensor.device_a",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )

        # Now update again - device_a should be skipped
        await coord._async_update_data()
        device_a = coord.device_states["binary_sensor.device_a"]
        assert device_a.is_suppressed is True


async def test_suppression_expiry(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that suppression expires when time is reached."""
    hass = mock_hass

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None

        await coord._async_update_data()

        # Suppress with a time in the past
        past_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        coord.suppress_entity("binary_sensor.device_a", past_time)
        device_a = coord.device_states["binary_sensor.device_a"]
        assert device_a.is_suppressed is True

        # Next update should clear suppression
        await coord._async_update_data()
        assert device_a.is_suppressed is False
        assert device_a.suppress_until is None


async def test_suppress_and_unsuppress(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test suppress and unsuppress methods."""
    hass = mock_hass

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        coord.suppress_entity("binary_sensor.device_b", future_time)
        assert coord.device_states["binary_sensor.device_b"].is_suppressed is True

        coord.unsuppress_entity("binary_sensor.device_b")
        assert coord.device_states["binary_sensor.device_b"].is_suppressed is False
        assert coord.device_states["binary_sensor.device_b"].suppress_until is None


async def test_suppress_nonexistent_entity(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test suppress on unknown entity does nothing."""
    hass = mock_hass

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

        # Should not raise
        coord.suppress_entity("sensor.does_not_exist", None)
        coord.unsuppress_entity("sensor.does_not_exist")


async def test_state_none_is_bad(
    mock_hass: HomeAssistant, mock_config_data
) -> None:
    """Test that entity with no state (None) is considered bad."""
    hass = mock_hass
    # Add an entity to the config that doesn't exist in states
    none_config_data = dict(mock_config_data)
    none_config_data[CONF_ENTITIES] = ["binary_sensor.nonexistent"]

    none_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Group",
        data=none_config_data,
        entry_id="test_entry_none",
        unique_id=f"{DOMAIN}_test_none",
    )

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, none_entry)
        coord._last_update = None
        await coord._async_update_data()

        device = coord.device_states["binary_sensor.nonexistent"]
        # First update: cooldown_start is set, but device is not yet offline
        assert device.cooldown_start is not None
        assert device.is_offline is False

        # After cooldown
        device.cooldown_start = datetime.now(timezone.utc) - timedelta(seconds=61)
        await coord._async_update_data()
        assert device.is_offline is True


async def test_unknown_state_is_bad(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that 'unknown' state is treated as bad."""
    hass = mock_hass
    hass.states.async_set("binary_sensor.device_a", STATE_UNKNOWN)

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

        device_a = coord.device_states["binary_sensor.device_a"]
        assert device_a.cooldown_start is not None


async def test_battery_detection_from_device_registry(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test battery level detection via device registry lookup."""
    hass = mock_hass
    hass.states.async_set(
        "binary_sensor.device_a",
        STATE_ON,
        {"friendly_name": "Device A"},
    )
    hass.states.async_set("sensor.device_a_bat_level", "42")

    mock_ent_entry = MagicMock()
    mock_ent_entry.device_id = "device_123"

    mock_bat_entry = MagicMock()
    mock_bat_entry.entity_id = "sensor.device_a_bat_level"
    mock_bat_entry.original_device_class = "battery"
    mock_bat_entry.device_class = "battery"

    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ), patch(
        "custom_components.entity_availability.coordinator.er.async_get"
    ) as mock_er, patch(
        "custom_components.entity_availability.coordinator.dr.async_get"
    ), patch(
        "custom_components.entity_availability.coordinator.er.async_entries_for_device"
    ) as mock_entries:
        mock_ent_reg = MagicMock()
        mock_ent_reg.async_get.return_value = mock_ent_entry
        mock_er.return_value = mock_ent_reg
        mock_entries.return_value = [mock_bat_entry]

        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._last_update = None
        await coord._async_update_data()

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.battery_level == 42
