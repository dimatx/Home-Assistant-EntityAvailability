# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-07

### Added
- Card: `entity_detail` option — `"off"` / `"tooltip"` / `"inline"` (replaces `show_entity_tooltips`)
- Card: `entity_filter` option — `"all"` / `"offline"` / `"online"` to filter entity list by health status
- Card: stale entity detection — grey dot + "Stale" for entities past the staleness threshold
- Card: human-readable durations and timestamps throughout (e.g. "2 hours ago", "today at 14:30")
- Sensor: `suppressed_until`, `stale_entities`, `offline_since` added to `GroupSummarySensor` attributes
- Translations: config flow help text added for all 10 supported languages

### Changed
- Card: entity status shows single-concern label (Suppressed / Offline for X / Stale / Low Battery / Online)
- Integration: card JS served directly from component directory, no longer copied to `www/`
- Integration: stale Lovelace resource entries cleaned up automatically on startup

### Fixed
- Card: custom element missing from card picker after fresh install
- Card: JS file loaded twice causing conflicts
- Card: entity tooltips clipped by overflow hidden
- Translations: non-English files were accidentally written in English

### Migration
- `show_entity_tooltips: true` automatically maps to `entity_detail: "tooltip"` — no action needed

## [0.1.1] - 2026-05-05

### Added
- Card: configurable entity sort order via `sort_by` option (`status`, `name_asc`, `name_desc`, `battery_asc`, `battery_desc`)
- Card: sort dropdown in visual editor
- 32 new unit tests covering all sort modes and edge cases

### Fixed
- `async_request_refresh` called without `await` inside a `@callback` debounce function, causing a `RuntimeWarning` about an unawaited coroutine — now scheduled via `hass.async_create_task()`

## [0.1.0] - 2026-05-04

### Changed
- Renamed integration from "Device Availability" to "Entity Availability"
- Renamed domain from `device_availability` to `entity_availability`
- Availability tracking uses 5-minute buckets (previously hourly)
- Battery monitoring requires explicit entity mapping via config flow step
- Low Battery sensor only created when battery threshold > 0
- Removed "All OK" binary sensor (redundant with "Any Offline")
- Battery entity selector shows all sensors (not filtered by device_class)
- Battery mapping uses suggested values — user can clear selections for non-battery entities
- Low Battery and Offline Entities sensors show "None" state when no issues (not empty/unknown)
- Lovelace card completely redesigned with dashboard-style layout

### Added
- Battery entity mapping step in config flow — auto-detects and lets user confirm/override
- Support for text battery states (`low`) in addition to numeric percentages
- "Any Offline" binary sensor (Problem device class) — ON when any entity is offline
- Group Summary sensor with total_entities, online, offline, suppressed, battery_powered, low_battery, entities, battery_levels attributes
- Low Battery Count sensor — numeric count for easy automation triggers
- Options flow includes battery mapping step
- Auto-detection of battery entities via device registry and naming convention
- Suppress/unsuppress services support `group` parameter for group-level operations
- Card: status icon (mdi:check-circle / alert-circle / close-circle) colored by group health
- Card: stats row with Online / Offline / Low Battery counts
- Card: all configured availability windows shown with colored progress bars
- Card: customizable bar colors and thresholds via visual editor (keys: `high`, `mid`, `low`)
- Card: expandable entity list with legend header, battery %, sorted by severity
- Card: optional suppress/unsuppress action buttons
- Card: suppressed entities banner
- Card: visual card editor with all options configurable
- Integration icon (icon.png, icon@2x.png) for HACS display
- Monitor entity availability with configurable groups
- Track offline, degraded, and suppressed entity states
- Availability tracking with configurable time windows (today, 3d, 5d, 7d)
- Suppress/unsuppress services for temporary exclusion from monitoring
- Sensors for offline count, offline entities list, degraded entities, and availability percentage
- Configurable bad states, cooldown period, staleness threshold, and battery threshold
- Persistent storage of availability data and suppression state
- Custom Lovelace card for visualizing entity availability
