"""Tests for Entity Availability integration setup and unload."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch


from homeassistant.core import HomeAssistant

from custom_components.entity_availability import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.entity_availability.const import DOMAIN
from custom_components.entity_availability.coordinator import EntityAvailabilityCoordinator


async def test_async_setup_entry(mock_hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful setup of a config entry."""
    hass = mock_hass
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        EntityAvailabilityCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ) as mock_refresh, patch(
        "custom_components.entity_availability.async_setup_services",
        new_callable=AsyncMock,
    ) as mock_services, patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as mock_forward:
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    assert isinstance(
        hass.data[DOMAIN][mock_config_entry.entry_id],
        EntityAvailabilityCoordinator,
    )
    mock_refresh.assert_called_once()
    mock_services.assert_called_once_with(hass)
    mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)


async def test_async_unload_entry(mock_hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful unload of a config entry."""
    hass = mock_hass
    mock_config_entry.add_to_hass(hass)

    # First set up
    with patch.object(
        EntityAvailabilityCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.entity_availability.async_setup_services",
        new_callable=AsyncMock,
    ), patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        await async_setup_entry(hass, mock_config_entry)

    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    # Now unload
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)


async def test_async_unload_entry_failure(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test unload returns False when platform unload fails."""
    hass = mock_hass
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        EntityAvailabilityCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.entity_availability.async_setup_services",
        new_callable=AsyncMock,
    ), patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        await async_setup_entry(hass, mock_config_entry)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    # Entry should NOT be removed from data since unload failed
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_creates_coordinator_with_correct_config(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that setup creates coordinator with correct configuration."""
    hass = mock_hass
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        EntityAvailabilityCoordinator,
        "async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.entity_availability.async_setup_services",
        new_callable=AsyncMock,
    ), patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        await async_setup_entry(hass, mock_config_entry)

    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert coordinator.monitored_entities == [
        "binary_sensor.device_a",
        "binary_sensor.device_b",
        "binary_sensor.device_c",
    ]
    assert coordinator.group_name == "Test Group"


async def test_platforms_defined() -> None:
    """Test that expected platforms are defined."""
    from homeassistant.const import Platform

    assert Platform.SENSOR in PLATFORMS
    assert Platform.BINARY_SENSOR in PLATFORMS
    assert len(PLATFORMS) == 2
