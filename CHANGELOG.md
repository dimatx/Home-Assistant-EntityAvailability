# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0-beta.2] - 2026-05-09

### Added
- Sensor: `recently_offline` — tracks entities that went offline within a configurable window (default 5 minutes); state is the friendly name list, attribute `entities` is the entity ID list
- Sensor: `recently_recovered` — tracks entities that recovered from offline within the same window; state is the friendly name list, attribute `entities` is the entity ID list
- Config: `recovery_window` setting (minutes) in Advanced Settings and Options flow — controls how long entities remain visible in both sensors after a state transition
- Action: `suppress_indefinitely` — suppress an entity or group with no expiry; cleared by the existing `unsuppress` action

### Fixed
- Indefinite suppressions (no expiry) now survive HA restarts
- `recently_offline_at` timestamps are now persisted to storage and restored on restart, so entities that went offline before a restart correctly appear in the `recently_offline` sensor within the configured window
- Changes to `recovery_window` in the Options flow now take effect immediately without requiring an integration reload

## [0.3.0-beta.1] - 2026-05-08

### Added
- Combined groups — select two or more existing groups and get a unified set of sensors that aggregate data across all of them
- Combined group sensors: offline count, offline entities list, low battery list, low battery count
- Binary sensor `any_offline` — turns ON when any entity in any included group is offline
- Card: combined groups now supported — card auto-detects group type and adapts its layout
- Card: combined group view shows per-group breakdown table (online / offline / low battery per group)
- Card editor: Group Slug field replaced with a dropdown populated from discovered groups; regular and combined groups shown in separate optgroups
- Card editor: controls that don't apply to combined groups (availability bars, filters, sort, entity detail, suppress buttons, color thresholds) are hidden automatically when a combined group is selected

### Fixed
- Automations no longer fire on HA restart for devices that were already offline before the restart
- Random false-positive triggers during HA startup (devices briefly appearing offline while HA loads) are now suppressed for the first 60 seconds after startup
- Suppress/unsuppress services are no longer unloaded while a combined group entry is still loaded

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
