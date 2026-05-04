/**
 * Entity Availability Card v1.0.0
 * Custom Lovelace card for the Home Assistant Entity Availability integration.
 *
 * This is a pre-built, self-contained version.
 * Home Assistant provides Lit on the frontend, so we use the globally available instance.
 */
const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace") ??
  customElements.get("hui-view") ??
  customElements.get("home-assistant")
);
if (!LitElement) {
  console.error("Entity Availability Card: Could not find LitElement base class");
}
const { html, css, nothing } = LitElement?.prototype?.constructor ?? {};

const CARD_VERSION = "1.0.0";

console.info(
  `%c ENTITY-AVAILABILITY-CARD %c v${CARD_VERSION} `,
  "color: white; background: #4caf50; font-weight: bold; padding: 2px 6px; border-radius: 3px 0 0 3px;",
  "color: #4caf50; background: #e8f5e9; font-weight: bold; padding: 2px 6px; border-radius: 0 3px 3px 0;"
);

const cardStyles = css`
  :host {
    --eac-green: #4caf50;
    --eac-yellow: #ff9800;
    --eac-red: #f44336;
    --eac-text-primary: var(--primary-text-color, #212121);
    --eac-text-secondary: var(--secondary-text-color, #727272);
    --eac-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --eac-card-bg: var(--card-background-color, #fff);
    --eac-bar-bg: var(--disabled-color, #bdbdbd);
    --eac-bar-fill: var(--eac-green);
  }

  ha-card {
    overflow: hidden;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 16px 12px;
    cursor: pointer;
    user-select: none;
  }

  .card-header:hover {
    opacity: 0.87;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .status-indicator {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);
  }

  .status-indicator.green {
    background-color: var(--eac-green);
    box-shadow: 0 0 6px var(--eac-green);
  }

  .status-indicator.yellow {
    background-color: var(--eac-yellow);
    box-shadow: 0 0 6px var(--eac-yellow);
  }

  .status-indicator.red {
    background-color: var(--eac-red);
    box-shadow: 0 0 6px var(--eac-red);
  }

  .group-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--eac-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-right {
    font-size: 14px;
    font-weight: 500;
    color: var(--eac-text-secondary);
    white-space: nowrap;
    margin-left: 12px;
  }

  .divider {
    height: 1px;
    background-color: var(--eac-divider);
    margin: 0 16px;
  }

  .device-list {
    padding: 8px 16px;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;
  }

  .device-list.collapsed {
    max-height: 0;
    opacity: 0;
    padding: 0 16px;
  }

  .device-list.expanded {
    max-height: 500px;
    opacity: 1;
  }

  .device-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    gap: 8px;
  }

  .device-item-left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .device-icon {
    font-size: 14px;
    flex-shrink: 0;
  }

  .device-name {
    font-size: 14px;
    color: var(--eac-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .device-reason {
    font-size: 12px;
    color: var(--eac-text-secondary);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .availability-section {
    padding: 12px 16px;
  }

  .availability-text {
    font-size: 14px;
    color: var(--eac-text-secondary);
    margin-bottom: 6px;
  }

  .availability-value {
    font-weight: 500;
    color: var(--eac-text-primary);
  }

  .timeline-bar {
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background-color: var(--eac-bar-bg);
    overflow: hidden;
    margin-top: 4px;
  }

  .timeline-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .timeline-fill.green {
    background-color: var(--eac-green);
  }

  .timeline-fill.yellow {
    background-color: var(--eac-yellow);
  }

  .timeline-fill.red {
    background-color: var(--eac-red);
  }

  .actions-section {
    padding: 8px 16px 12px;
  }

  .suppress-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: none;
    border-radius: 4px;
    background-color: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .suppress-btn:hover {
    opacity: 0.85;
  }

  .suppress-btn:active {
    opacity: 0.7;
  }

  .no-issues {
    padding: 8px 16px 12px;
    font-size: 13px;
    color: var(--eac-text-secondary);
    font-style: italic;
  }

  .error-message {
    padding: 16px;
    color: var(--error-color, #db4437);
    font-size: 14px;
  }

  .compact .card-header {
    padding: 12px 16px 8px;
  }

  .compact .device-item {
    padding: 4px 0;
  }

  .compact .availability-section {
    padding: 8px 16px;
  }

  .compact .actions-section {
    padding: 4px 16px 8px;
  }
`;

class EntityAvailabilityCard extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _expanded: { state: true },
    };
  }

  static get styles() {
    return cardStyles;
  }

  static getConfigElement() {
    return document.createElement("entity-availability-card-editor");
  }

  static getStubConfig() {
    return {
      group: "my_devices",
      show_timeline: true,
      show_availability: true,
      compact: false,
    };
  }

  constructor() {
    super();
    this._config = {};
    this._expanded = false;
  }

  setConfig(config) {
    if (!config.group) {
      throw new Error("You must define a 'group' in the card configuration.");
    }
    this._config = {
      show_timeline: true,
      show_availability: true,
      compact: false,
      availability_window: "7d",
      ...config,
    };
  }

  getCardSize() {
    return this._config && this._config.compact ? 2 : 4;
  }

  shouldUpdate(changedProps) {
    if (changedProps.has("_config")) return true;
    if (!this.hass) return false;

    const entities = this._getEntityIds();
    const oldHass = changedProps.get("hass");
    if (!oldHass) return true;

    return Object.values(entities).some(
      (entityId) => oldHass.states[entityId] !== this.hass.states[entityId]
    );
  }

  render() {
    if (!this._config || !this.hass) {
      return html`<ha-card><div class="error-message">Card not configured.</div></ha-card>`;
    }

    if (!this._config.group) {
      return html`<ha-card><div class="error-message">No group configured. Please set 'group' in card configuration.</div></ha-card>`;
    }

    const entities = this._getEntityIds();
    const allOk = this._getEntity(entities.allOk);
    const offlineCountEntity = this._getEntity(entities.offlineCount);
    const offlineEntitiesEntity = this._getEntity(entities.offlineEntities);
    const lowBatteryEntity = this._getEntity(entities.lowBattery);
    const availabilityEntity = this._getAvailabilityEntity(entities);

    if (!allOk && !offlineCountEntity && !offlineEntitiesEntity && !lowBatteryEntity) {
      return html`<ha-card>
        <div class="error-message">
          No entities found for group "${this._config.group}".
          Expected entities like: sensor.entity_availability_${this._config.group}_offline_count
        </div>
      </ha-card>`;
    }

    const offlineCount = offlineCountEntity
      ? parseInt(offlineCountEntity.state, 10) || 0
      : 0;
    const isAllOk = allOk ? allOk.state === "on" : offlineCount === 0;

    const lowBatteryText = lowBatteryEntity ? lowBatteryEntity.state : "";
    const hasLowBattery = lowBatteryText && lowBatteryText !== "" && lowBatteryText !== "unknown" && lowBatteryText !== "unavailable";

    const statusColor =
      offlineCount > 0 ? "red" : hasLowBattery ? "yellow" : "green";

    let totalEntities = 0;
    if (offlineEntitiesEntity && offlineEntitiesEntity.attributes) {
      totalEntities = offlineEntitiesEntity.attributes.count ?? 0;
    }
    const healthyCount = Math.max(0, totalEntities - offlineCount);

    const offlineDevices = this._parseOfflineEntities(offlineEntitiesEntity);
    const lowBatteryDevices = this._parseLowBattery(lowBatteryEntity);
    const hasIssues = offlineDevices.length > 0 || lowBatteryDevices.length > 0;

    const availabilityPct = availabilityEntity
      ? parseFloat(availabilityEntity.state) || null
      : null;

    const title =
      this._config.title || this._formatGroupName(this._config.group);
    const compactClass = this._config.compact ? "compact" : "";

    const showDeviceList = hasIssues && (this._expanded || !isAllOk);

    return html`
      <ha-card class="${compactClass}">
        <div class="card-header" @click=${this._toggleExpand}>
          <div class="header-left">
            <div class="status-indicator ${statusColor}"></div>
            <span class="group-title">${title}</span>
          </div>
          <div class="header-right">
            ${totalEntities > 0
              ? `${healthyCount}/${totalEntities} OK`
              : isAllOk
              ? "All OK"
              : "Issues detected"}
          </div>
        </div>

        ${hasIssues ? html`<div class="divider"></div>` : nothing}

        <div class="device-list ${showDeviceList ? "expanded" : "collapsed"}">
          ${offlineDevices.map(
            (device) => html`
              <div class="device-item">
                <div class="device-item-left">
                  <span class="device-icon">⚠️</span>
                  <span class="device-name">${device.name}</span>
                </div>
                <span class="device-reason">${device.reason}${device.duration ? ` ${device.duration}` : ""}</span>
              </div>
            `
          )}
          ${lowBatteryDevices.map(
            (device) => html`
              <div class="device-item">
                <div class="device-item-left">
                  <span class="device-icon">🔋</span>
                  <span class="device-name">${device.name}</span>
                </div>
                <span class="device-reason">${device.reason}</span>
              </div>
            `
          )}
        </div>

        ${!hasIssues && this._expanded
          ? html`<div class="no-issues">All entities are healthy.</div>`
          : nothing}

        ${this._config.show_availability && availabilityPct !== null
          ? html`
              <div class="divider"></div>
              <div class="availability-section">
                <div class="availability-text">
                  Availability:
                  <span class="availability-value"
                    >${availabilityPct.toFixed(1)}%</span
                  >
                  (${this._config.availability_window})
                </div>
                ${this._config.show_timeline
                  ? html`
                      <div class="timeline-bar">
                        <div
                          class="timeline-fill ${this._getAvailabilityColor(
                            availabilityPct
                          )}"
                          style="width: ${Math.min(
                            100,
                            Math.max(0, availabilityPct)
                          )}%"
                        ></div>
                      </div>
                    `
                  : nothing}
              </div>
            `
          : nothing}

        ${hasIssues
          ? html`
              <div class="divider"></div>
              <div class="actions-section">
                <button class="suppress-btn" @click=${this._handleSuppress}>
                  Suppress All
                </button>
              </div>
            `
          : nothing}
      </ha-card>
    `;
  }

  _getEntityIds() {
    const g = this._config.group;
    const prefix = `entity_availability_${g}`;
    return {
      allOk: `binary_sensor.${prefix}_group_health`,
      anyOffline: `binary_sensor.${prefix}_any_offline`,
      offlineCount: `sensor.${prefix}_offline_count`,
      offlineEntities: `sensor.${prefix}_offline_entities`,
      lowBattery: `sensor.${prefix}_low_battery`,
      groupSummary: `sensor.${prefix}_group_summary`,
      availabilityToday: `sensor.${prefix}_availability_today`,
      availability3d: `sensor.${prefix}_availability_3d`,
      availability5d: `sensor.${prefix}_availability_5d`,
      availability7d: `sensor.${prefix}_availability_7d`,
    };
  }

  _getEntity(entityId) {
    return this.hass && this.hass.states ? this.hass.states[entityId] : undefined;
  }

  _getAvailabilityEntity(entities) {
    const window = this._config.availability_window || "7d";
    if (window === "today") {
      return this._getEntity(entities.availabilityToday);
    }
    if (window === "3d") {
      return this._getEntity(entities.availability3d);
    }
    if (window === "5d") {
      return this._getEntity(entities.availability5d);
    }
    return this._getEntity(entities.availability7d);
  }

  _parseOfflineEntities(entity) {
    if (!entity) return [];
    const stateStr = entity.state;
    if (
      !stateStr ||
      stateStr === "" ||
      stateStr === "0" ||
      stateStr === "None" ||
      stateStr === "unknown" ||
      stateStr === "unavailable"
    ) {
      return [];
    }

    const names = stateStr
      .split(",")
      .map((n) => n.trim())
      .filter((n) => n !== "" && n !== "None");
    const entityList =
      entity.attributes && entity.attributes.entities
        ? entity.attributes.entities
        : [];

    return names.map((name, idx) => ({
      name,
      reason: "offline",
      duration: this._computeDuration(entityList[idx]),
    }));
  }

  _parseLowBattery(entity) {
    if (!entity) return [];
    const stateStr = entity.state;
    if (!stateStr || stateStr === "" || stateStr === "unknown" || stateStr === "unavailable") {
      return [];
    }
    return stateStr.split(",").map((n) => n.trim()).filter((n) => n !== "").map((name) => ({
      name,
      reason: "low battery",
    }));
  }

  _computeDuration(entityId) {
    if (!entityId || !this.hass || !this.hass.states[entityId]) return undefined;
    const lastChanged = this.hass.states[entityId].last_changed;
    if (!lastChanged) return undefined;

    const diff = Date.now() - new Date(lastChanged).getTime();
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  }

  _getAvailabilityColor(pct) {
    if (pct >= 99) return "green";
    if (pct >= 95) return "yellow";
    return "red";
  }

  _formatGroupName(group) {
    return group.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  _toggleExpand() {
    this._expanded = !this._expanded;
  }

  async _handleSuppress(e) {
    e.stopPropagation();
    if (!this.hass) return;

    try {
      const entities = this._getEntityIds();
      const offlineState = this.hass.states[entities.offlineEntities];
      const entityList = offlineState?.attributes?.entities || [];
      for (const entityId of entityList) {
        await this.hass.callService("entity_availability", "suppress", {
          entity_id: entityId,
          duration: 60,
        });
      }
    } catch (err) {
      console.error("Failed to call entity_availability.suppress:", err);
    }
  }
}

customElements.define("entity-availability-card", EntityAvailabilityCard);

// --- Card Editor ---

class EntityAvailabilityCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
    };
  }

  static get styles() {
    return css`
      .editor-row {
        margin-bottom: 12px;
      }
      .editor-row label {
        display: block;
        font-weight: 500;
        margin-bottom: 4px;
      }
      .editor-row input[type="text"],
      .editor-row select {
        width: 100%;
        padding: 8px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        box-sizing: border-box;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
      }
      .editor-row.checkbox label {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: normal;
      }
    `;
  }

  setConfig(config) {
    this._config = config;
  }

  render() {
    if (!this._config) return html``;

    return html`
      <div style="padding: 16px;">
        <div class="editor-row">
          <label>Group Slug</label>
          <input
            type="text"
            .value=${this._config.group || ""}
            @input=${this._groupChanged}
            placeholder="e.g. security_devices"
          />
        </div>
        <div class="editor-row">
          <label>Title (optional)</label>
          <input
            type="text"
            .value=${this._config.title || ""}
            @input=${this._titleChanged}
            placeholder="Custom card title"
          />
        </div>
        <div class="editor-row">
          <label>Availability Window</label>
          <select
            .value=${this._config.availability_window || "7d"}
            @change=${this._windowChanged}
          >
            <option value="today">Today</option>
            <option value="3d">3 Days</option>
            <option value="5d">5 Days</option>
            <option value="7d">7 Days</option>
          </select>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.show_availability !== false}
              @change=${this._availabilityToggled}
            />
            Show Availability
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.show_timeline !== false}
              @change=${this._timelineToggled}
            />
            Show Timeline Bar
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.compact === true}
              @change=${this._compactToggled}
            />
            Compact Mode
          </label>
        </div>
      </div>
    `;
  }

  _groupChanged(ev) {
    this._updateConfig("group", ev.target.value);
  }

  _titleChanged(ev) {
    this._updateConfig("title", ev.target.value || undefined);
  }

  _windowChanged(ev) {
    this._updateConfig("availability_window", ev.target.value);
  }

  _availabilityToggled(ev) {
    this._updateConfig("show_availability", ev.target.checked);
  }

  _timelineToggled(ev) {
    this._updateConfig("show_timeline", ev.target.checked);
  }

  _compactToggled(ev) {
    this._updateConfig("compact", ev.target.checked);
  }

  _updateConfig(key, value) {
    if (!this._config) return;
    const newConfig = { ...this._config, [key]: value };
    Object.keys(newConfig).forEach((k) => {
      if (newConfig[k] === undefined) delete newConfig[k];
    });
    this._config = newConfig;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

customElements.define(
  "entity-availability-card-editor",
  EntityAvailabilityCardEditor
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "entity-availability-card",
  name: "Entity Availability Card",
  description:
    "Shows entity health status with traffic-light indicators for a monitored group.",
  preview: true,
  documentationURL:
    "https://github.com/italo-lombardi/Home-Assistant-EntityAvailability",
});
