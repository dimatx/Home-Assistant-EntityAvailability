"""Tests for Entity Availability services."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.entity_availability.const import DOMAIN
from custom_components.entity_availability.coordinator import EntityAvailabilityCoordinator
from custom_components.entity_availability.models import DeviceState
from custom_components.entity_availability.services import (
    ATTR_DURATION,
    ATTR_ENTITY_ID,
    SERVICE_SUPPRESS,
    SERVICE_UNSUPPRESS,
    async_setup_services,
)


@pytest.fixture
async def setup_services(mock_hass: HomeAssistant, mock_config_entry):
    """Set up services with a coordinator in hass.data."""
    hass = mock_hass
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._device_states = {
            "binary_sensor.device_a": DeviceState(
                entity_id="binary_sensor.device_a",
                is_offline=False,
            ),
            "binary_sensor.device_b": DeviceState(
                entity_id="binary_sensor.device_b",
                is_offline=True,
            ),
        }
        coord.data = None  # minimal data attribute for async_set_updated_data

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coord

    await async_setup_services(hass)
    return hass, coord


async def test_suppress_service(setup_services) -> None:
    """Test suppress service sets suppression on entity."""
    hass, coord = setup_services

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SUPPRESS,
        {ATTR_ENTITY_ID: "binary_sensor.device_a", ATTR_DURATION: 30},
        blocking=True,
    )

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.is_suppressed is True
    assert device_a.suppress_until is not None
    # Should be approximately 30 minutes from now
    expected_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    diff = abs((device_a.suppress_until - expected_until).total_seconds())
    assert diff < 5  # Allow 5 seconds tolerance


async def test_suppress_service_default_duration(setup_services) -> None:
    """Test suppress service uses default 60 min duration."""
    hass, coord = setup_services

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SUPPRESS,
        {ATTR_ENTITY_ID: "binary_sensor.device_a"},
        blocking=True,
    )

    device_a = coord.device_states["binary_sensor.device_a"]
    assert device_a.is_suppressed is True
    expected_until = datetime.now(timezone.utc) + timedelta(minutes=60)
    diff = abs((device_a.suppress_until - expected_until).total_seconds())
    assert diff < 5


async def test_unsuppress_service(setup_services) -> None:
    """Test unsuppress service clears suppression."""
    hass, coord = setup_services

    # First suppress
    coord.suppress_entity(
        "binary_sensor.device_b",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert coord.device_states["binary_sensor.device_b"].is_suppressed is True

    # Then unsuppress
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UNSUPPRESS,
        {ATTR_ENTITY_ID: "binary_sensor.device_b"},
        blocking=True,
    )

    device_b = coord.device_states["binary_sensor.device_b"]
    assert device_b.is_suppressed is False
    assert device_b.suppress_until is None


async def test_suppress_entity_not_found_logs_warning(
    setup_services, caplog
) -> None:
    """Test warning logged when entity not in any group."""
    hass, coord = setup_services

    with caplog.at_level(logging.WARNING):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SUPPRESS,
            {ATTR_ENTITY_ID: "sensor.nonexistent", ATTR_DURATION: 10},
            blocking=True,
        )

    assert "not found in any monitored group" in caplog.text


async def test_unsuppress_entity_not_found_logs_warning(
    setup_services, caplog
) -> None:
    """Test warning logged when unsuppressing unknown entity."""
    hass, coord = setup_services

    with caplog.at_level(logging.WARNING):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNSUPPRESS,
            {ATTR_ENTITY_ID: "sensor.nonexistent"},
            blocking=True,
        )

    assert "not found in any monitored group" in caplog.text


async def test_services_registered_only_once(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test services are not registered multiple times."""
    hass = mock_hass
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(hass, mock_config_entry)
        coord._device_states = {}
        coord.data = None

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coord

    await async_setup_services(hass)
    # Second call should not error
    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_SUPPRESS)
    assert hass.services.has_service(DOMAIN, SERVICE_UNSUPPRESS)


async def test_suppress_calls_async_set_updated_data(setup_services) -> None:
    """Test that suppress triggers data update notification."""
    hass, coord = setup_services

    with patch.object(coord, "async_set_updated_data") as mock_update:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SUPPRESS,
            {ATTR_ENTITY_ID: "binary_sensor.device_a", ATTR_DURATION: 10},
            blocking=True,
        )
        mock_update.assert_called_once()


async def test_unsuppress_calls_async_set_updated_data(setup_services) -> None:
    """Test that unsuppress triggers data update notification."""
    hass, coord = setup_services

    # First suppress
    coord.suppress_entity(
        "binary_sensor.device_a",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )

    with patch.object(coord, "async_set_updated_data") as mock_update:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNSUPPRESS,
            {ATTR_ENTITY_ID: "binary_sensor.device_a"},
            blocking=True,
        )
        mock_update.assert_called_once()
