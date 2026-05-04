"""The Entity Availability integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EntityAvailabilityCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

LOVELACE_CARD_URL = f"/{DOMAIN}/entity-availability-card.js"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Availability from a config entry."""
    coordinator = EntityAvailabilityCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register cleanup on unload
    entry.async_on_unload(coordinator.async_shutdown)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await async_setup_services(hass)

    # Register the frontend card resource
    await _async_register_card(hass)

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the custom Lovelace card as a static resource."""
    # Only register once across multiple config entries
    if f"{DOMAIN}_card_registered" in hass.data:
        return

    # Determine the path to the card JS file.
    # Priority 1: shipped inside the integration directory (HACS compatible)
    card_path = Path(__file__).parent / "frontend" / "entity-availability-card.js"

    if not card_path.exists():
        card_path = (
            Path(__file__).resolve().parent.parent.parent / "dist" / "entity-availability-card.js"
        )

    if not card_path.exists():
        card_path = Path(hass.config.path("www")) / "community" / DOMAIN / "entity-availability-card.js"

    if not card_path.exists():
        card_path = Path(hass.config.path("www")) / "entity-availability-card.js"

    if card_path.exists():
        # Register a static path so HA serves the file
        try:
            hass.http.register_static_path(
                LOVELACE_CARD_URL,
                str(card_path.resolve()),
                cache_headers=True,
            )
            _LOGGER.debug(
                "Registered entity-availability-card.js at %s", LOVELACE_CARD_URL
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "Could not register static path for entity-availability-card.js"
            )
            return
    else:
        _LOGGER.warning(
            "Could not find entity-availability-card.js. "
            "Expected at %s. Card will not be available in the dashboard.",
            card_path,
        )
        return

    # Add the resource to Lovelace so the card is automatically loaded
    try:
        # Access the lovelace resources collection (available when lovelace is in storage mode)
        resources = hass.data.get("lovelace_resources")
        if resources is not None:
            # Check if already registered
            existing = [
                r
                for r in resources.async_items()
                if r.get("url", "").startswith(LOVELACE_CARD_URL)
            ]
            if not existing:
                await resources.async_create_item(
                    {"res_type": "module", "url": LOVELACE_CARD_URL}
                )
                _LOGGER.info(
                    "Added entity-availability-card as Lovelace resource"
                )
        else:
            _LOGGER.debug(
                "Lovelace resources collection not available (YAML mode?). "
                "Add the following to your Lovelace resources manually: %s",
                LOVELACE_CARD_URL,
            )
    except Exception:  # noqa: BLE001
        _LOGGER.debug(
            "Could not auto-register Lovelace resource. "
            "Add the following to your Lovelace resources manually: "
            "url: %s, type: module",
            LOVELACE_CARD_URL,
        )

    hass.data[f"{DOMAIN}_card_registered"] = True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Remove services if this was the last entry
    if not hass.data.get(DOMAIN):
        async_unload_services(hass)

    return unload_ok
