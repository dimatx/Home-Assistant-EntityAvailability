"""Tests for Entity Availability integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_availability import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.entity_availability.const import (
    CONF_COMBINED_GROUPS,
    CONF_ENTRY_TYPE,
    CONF_GROUP_NAME,
    DOMAIN,
    ENTRY_TYPE_COMBINED,
)
from custom_components.entity_availability.coordinator import (
    EntityAvailabilityCoordinator,
)


async def test_async_setup_entry(mock_hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful setup of a config entry."""
    hass = mock_hass
    mock_config_entry.add_to_hass(hass)

    with (
        patch.object(
            EntityAvailabilityCoordinator,
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ) as mock_refresh,
        patch(
            "custom_components.entity_availability.async_setup_services",
            new_callable=AsyncMock,
        ) as mock_services,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ) as mock_forward,
    ):
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
    with (
        patch.object(
            EntityAvailabilityCoordinator,
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.entity_availability.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
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

    with (
        patch.object(
            EntityAvailabilityCoordinator,
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.entity_availability.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
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

    with (
        patch.object(
            EntityAvailabilityCoordinator,
            "async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.entity_availability.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
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


# ---------------------------------------------------------------------------
# Combined entry setup / unload
# ---------------------------------------------------------------------------


def _make_combined_entry(
    entry_id: str, name: str, combined_ids: list[str]
) -> MockConfigEntry:
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


async def test_combined_setup_does_not_store_coordinator(
    mock_hass: HomeAssistant,
) -> None:
    """Combined entry setup does NOT put a coordinator into hass.data[DOMAIN]."""
    hass = mock_hass
    combined = _make_combined_entry("combined_id", "My Combined", [])
    combined.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        result = await async_setup_entry(hass, combined)

    assert result is True
    # No coordinator stored under the combined entry_id
    assert "combined_id" not in hass.data.get(DOMAIN, {})


async def test_combined_unload_entry(mock_hass: HomeAssistant) -> None:
    """Combined entry unloads cleanly without touching hass.data[DOMAIN]."""
    hass = mock_hass
    combined = _make_combined_entry("combined_id3", "My Combined", [])
    combined.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        await async_setup_entry(hass, combined)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_unload:
        result = await async_unload_entry(hass, combined)

    assert result is True
    mock_unload.assert_called_once_with(combined, PLATFORMS)
