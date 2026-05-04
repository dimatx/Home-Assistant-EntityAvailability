"""The Entity Availability integration."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EntityAvailabilityCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

CARD_FILENAME = "entity-availability-card.js"
CARD_URL = f"/local/community/{DOMAIN}/{CARD_FILENAME}"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Entity Availability integration (once, before entries)."""
    await _async_install_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Entity Availability from a config entry."""
    coordinator = EntityAvailabilityCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(coordinator.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await async_setup_services(hass)

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_install_card(hass: HomeAssistant) -> None:
    """Copy card JS to www/community folder so it's served via /local/."""
    source = Path(__file__).parent / "frontend" / CARD_FILENAME
    if not source.exists():
        _LOGGER.warning("Card JS not found at %s", source)
        return

    www_dir = Path(hass.config.path("www")) / "community" / DOMAIN
    dest = www_dir / CARD_FILENAME

    try:
        www_dir.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or source.stat().st_mtime > dest.stat().st_mtime:
            await hass.async_add_executor_job(shutil.copy2, source, dest)
            _LOGGER.info("Installed %s to %s", CARD_FILENAME, dest)
    except OSError:
        _LOGGER.warning("Could not copy card JS to %s", dest)
        return

    # Register as Lovelace resource
    try:
        from homeassistant.components.lovelace import (  # noqa: PLC0415
            DOMAIN as LOVELACE_DOMAIN,
        )

        lovelace_info = hass.data.get(LOVELACE_DOMAIN)
        resources = None
        if lovelace_info:
            if hasattr(lovelace_info, "resources"):
                resources = lovelace_info.resources
            elif isinstance(lovelace_info, dict):
                for dashboard in lovelace_info.values():
                    if hasattr(dashboard, "resources"):
                        resources = dashboard.resources
                        break
        if resources is None:
            resources = hass.data.get("lovelace_resources")

        if resources is not None:
            existing = [
                r for r in resources.async_items() if CARD_FILENAME in r.get("url", "")
            ]
            if not existing:
                await resources.async_create_item(
                    {"res_type": "module", "url": CARD_URL}
                )
                _LOGGER.info("Registered %s as Lovelace resource", CARD_URL)
        else:
            _LOGGER.info(
                "Add Lovelace resource manually: url: %s, type: module", CARD_URL
            )
    except Exception:  # noqa: BLE001
        _LOGGER.info(
            "Could not auto-register Lovelace resource. "
            "Add manually: url: %s, type: module",
            CARD_URL,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data.get(DOMAIN):
        async_unload_services(hass)

    return unload_ok
