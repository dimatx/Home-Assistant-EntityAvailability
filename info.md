# Entity Availability for Home Assistant

Monitor entity availability across your Home Assistant setup. Track offline entities, uptime history, and degraded states with a custom dashboard card.

## Features

- Multi-group support — organize entities by function (Security, Climate, Media, etc.)
- Configurable bad states — define which states count as offline (`unavailable`, `unknown`, or custom)
- Cooldown timer — ignore brief blips before marking an entity offline
- Availability % sensors — track uptime over today, 3-day, 5-day, and 7-day windows
- Battery monitoring with manual mapping — supports numeric (%) and text states (`low`)
- Degraded entity detection — flag entities with low battery or stale data
- Maintenance/suppression mode — temporarily exclude entities from monitoring
- Custom Lovelace card — traffic-light status display with at-a-glance health overview
- Survives HA restarts — history persisted via HA Store, no recorder dependency

## Setup

1. Install via HACS
2. Go to **Settings → Devices & Services → Add Integration**
3. Search for **Entity Availability**
4. Follow the config flow to create your first entity group

> **Note:** Availability sensors will show as `unavailable` after first install. This is normal — they need time (at least 5 minutes) to collect data before reporting a percentage.

> This is an unofficial integration not affiliated with Home Assistant.
