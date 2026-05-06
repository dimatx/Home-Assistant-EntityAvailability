# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.0] - 2026-05-06

### Added
- Card: `entity_detail` option (`"off"` / `"tooltip"` / `"inline"`) replaces `show_entity_tooltips` boolean
  - `"tooltip"`: hover tooltip showing Entity ID, Area, HA State + duration, Condition, Battery, Suppressed Until
  - `"inline"`: same detail always visible as a block under each entity row; when combined with `compact: true`, shows only HA State + duration (ideal for "last seen" at a glance)
- Card: `entity_filter` option (`"all"` / `"offline"` / `"online"`) — filter entity list by health status
  - `"offline"`: shows only problem entities (offline, stale, low battery)
  - `"online"`: shows only healthy entities
  - Section title and count update to reflect filter: "Offline Entities (2/6)" / "Healthy Entities (4/6)"
- Card: stale entity detection — entities that haven't changed state beyond the staleness threshold shown with a grey dot and "Stale" status
- Card: suppressed entities now display "Suppressed" as their condition in the entity list (green dot) instead of showing their underlying state
- Card: timestamps beautified — durations show as "X minutes ago / X hours ago / X days ago", suppression expiry shows as "today at HH:MM" or "May 10" or "May 10, 2027"
- Sensor: `GroupSummarySensor` attributes now include `suppressed_until` (map of entity → ISO datetime), `stale_entities` (list), and `offline_since` (map of entity → ISO datetime)
- Model: `DeviceState` now tracks `is_stale` boolean field
- Translations: added `data_description` help text to Advanced Settings step in all 10 supported languages (en, da, de, es, fr, it, nb, nl, pl, pt, sv) with native-speaker review

### Changed
- Card: entity status column shows single-concern condition (Suppressed / Offline for X / Stale / Low Battery / Online) — detailed HA state available via `entity_detail`
- Card: offline duration shown inline (e.g., "Offline for 2 hours") instead of raw state
- Integration: Lovelace card now served directly from component directory at `/entity_availability/entity-availability-card.js` (no longer copies to `www/`)
- Integration: card registration moved to `async_setup_entry` with a module-level `_CARD_INSTALLED` guard to prevent re-registration on config entry reload
- Integration: duplicate Lovelace resource entries are cleaned up automatically on startup

### Fixed
- Card: custom element not appearing in the Lovelace card picker — fixed by deferring LitElement lookup to `customElements.whenDefined("ha-panel-lovelace")`
- Card: double-load of the JS file caused by both `add_extra_js_url` and a Lovelace resource entry — removed `add_extra_js_url`
- Card: entity tooltips clipped by `overflow: hidden` on `ha-card` and `.entity-list` — fixed with `overflow: visible`
- Card: `<option>` `.selected` Lit binding removed (not supported); `<select>.value` binding is sufficient
- Translations: all non-English translation files were accidentally written in English — replaced with properly translated content

### Migration
- `show_entity_tooltips: true` automatically maps to `entity_detail: "tooltip"` — existing cards are not broken

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
