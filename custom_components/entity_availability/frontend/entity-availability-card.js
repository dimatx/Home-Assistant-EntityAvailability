/**
 * Entity Availability Card v0.1.0
 * Custom Lovelace card for the Home Assistant Entity Availability integration.
 */
const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
const { html, nothing } = LitElement.prototype;

// Provide css tagged template - works whether or not HA exposes it on prototype
const css = LitElement.prototype.css || (() => {
  class CSSResult {
    constructor(cssText) {
      this.cssText = cssText;
      this._styleSheet = null;
    }
    get styleSheet() {
      if (this._styleSheet === null && window.CSSStyleSheet) {
        try {
          this._styleSheet = new CSSStyleSheet();
          this._styleSheet.replaceSync(this.cssText);
        } catch (e) {
          this._styleSheet = null;
        }
      }
      return this._styleSheet;
    }
    toString() { return this.cssText; }
  }
  return (strings, ...values) => new CSSResult(
    strings.reduce((acc, str, i) => acc + str + (values[i] != null ? String(values[i]) : ""), "")
  );
})();

const CARD_VERSION = "0.1.0";

console.info(
  `%c ENTITY-AVAILABILITY-CARD %c v${CARD_VERSION} %c — github.com/italo-lombardi `,
  "color: white; background: #4caf50; font-weight: bold; padding: 2px 6px; border-radius: 3px 0 0 3px;",
  "color: #4caf50; background: #e8f5e9; font-weight: bold; padding: 2px 6px;",
  "color: #9e9e9e; background: #e8f5e9; padding: 2px 6px; border-radius: 0 3px 3px 0;"
);

const AVAILABILITY_WINDOWS = [
  { key: "today", label: "Today" },
  { key: "3d", label: "3 Days" },
  { key: "5d", label: "5 Days" },
  { key: "7d", label: "7 Days" },
];

const STATUS_ICONS = {
  green: "mdi:check-circle",
  yellow: "mdi:alert-circle",
  red: "mdi:close-circle",
};

const STATUS_COLORS = {
  green: "#4caf50",
  yellow: "#ff9800",
  red: "#f44336",
};

const cardStyles = css`
  :host {
    --eac-green: #4caf50;
    --eac-yellow: #ff9800;
    --eac-red: #f44336;
    --eac-text-primary: var(--primary-text-color, #212121);
    --eac-text-secondary: var(--secondary-text-color, #727272);
    --eac-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --eac-bar-bg: var(--disabled-color, #bdbdbd);
  }

  ha-card {
    overflow: hidden;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 16px 12px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .header-icon {
    --mdc-icon-size: 24px;
    flex-shrink: 0;
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

  /* Stats Row */
  .stats-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
  }

  .stat-item {
    flex: 1;
    text-align: center;
    font-size: 13px;
    font-weight: 500;
  }

  .stat-item.online {
    color: var(--eac-green);
  }

  .stat-item.offline {
    color: var(--eac-red);
  }

  .stat-item.battery {
    color: var(--eac-yellow);
  }

  .stat-item.neutral {
    color: var(--eac-text-secondary);
  }

  .suppressed-banner {
    font-size: 12px;
    color: var(--eac-text-secondary);
    font-style: italic;
    text-align: center;
    padding: 4px 16px 8px;
  }

  /* Availability Section */
  .availability-section {
    padding: 10px 16px;
  }

  .availability-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .availability-row:last-child {
    margin-bottom: 0;
  }

  .availability-label {
    font-size: 13px;
    color: var(--eac-text-secondary);
    min-width: 50px;
  }

  .availability-bar {
    flex: 1;
    height: 8px;
    border-radius: 4px;
    background-color: var(--eac-bar-bg);
    overflow: hidden;
  }

  .availability-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  .availability-value {
    font-size: 13px;
    font-weight: 500;
    color: var(--eac-text-primary);
    min-width: 45px;
    text-align: right;
  }

  /* Entity List */
  .entity-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    cursor: pointer;
    user-select: none;
  }

  .entity-section-header:hover {
    opacity: 0.8;
  }

  .entity-section-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--eac-text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .chevron {
    transition: transform 0.3s ease;
    --mdc-icon-size: 18px;
  }

  .chevron.expanded {
    transform: rotate(180deg);
  }

  .entity-list {
    padding: 0 16px 12px;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;
  }

  .entity-list.collapsed {
    max-height: 0;
    opacity: 0;
    padding: 0 16px;
  }

  .entity-list.expanded {
    max-height: 2000px;
    opacity: 1;
  }

  .entity-legend {
    display: flex;
    align-items: center;
    padding: 0 0 6px;
    gap: 10px;
    border-bottom: 1px solid var(--eac-divider);
    margin-bottom: 4px;
  }

  .entity-legend-dot {
    width: 10px;
    flex-shrink: 0;
  }

  .entity-legend-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--eac-text-secondary);
    flex: 1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .entity-legend-status {
    font-size: 11px;
    font-weight: 600;
    color: var(--eac-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }

  .entity-legend-battery {
    font-size: 11px;
    font-weight: 600;
    color: var(--eac-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    min-width: 35px;
    text-align: right;
  }

  .entity-item {
    display: flex;
    align-items: center;
    padding: 5px 0;
    gap: 10px;
  }

  .entity-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .entity-dot.green { background-color: var(--eac-green); }
  .entity-dot.red { background-color: var(--eac-red); }
  .entity-dot.yellow { background-color: var(--eac-yellow); }

  .entity-name {
    font-size: 13px;
    color: var(--eac-text-primary);
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .entity-status {
    font-size: 12px;
    color: var(--eac-text-secondary);
    white-space: nowrap;
  }

  .entity-battery {
    font-size: 12px;
    color: var(--eac-text-secondary);
    white-space: nowrap;
    min-width: 35px;
    text-align: right;
  }

  /* Actions */
  .actions-section {
    padding: 8px 16px 12px;
    display: flex;
    justify-content: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .action-btn:hover { opacity: 0.85; }
  .action-btn:active { opacity: 0.7; }

  .action-btn.suppress {
    background-color: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
  }

  .action-btn.unsuppress {
    background-color: var(--secondary-background-color, #e0e0e0);
    color: var(--primary-text-color, #212121);
  }

  .error-message {
    padding: 16px;
    color: var(--error-color, #db4437);
    font-size: 14px;
  }

  .compact .card-header { padding: 12px 16px 8px; }
  .compact .stats-row { padding: 6px 16px; }
  .compact .availability-section { padding: 6px 16px; }
  .compact .entity-section-header { padding: 6px 16px; }
  .compact .actions-section { padding: 4px 16px 8px; }
`;

class EntityAvailabilityCard extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _entitiesExpanded: { state: true },
    };
  }

  static get styles() {
    return cardStyles;
  }

  static getConfigElement() {
    return document.createElement("entity-availability-card-editor");
  }

  static getStubConfig(hass) {
    const match = Object.keys(hass.states).find(
      (id) =>
        id.startsWith("sensor.entity_availability_") &&
        id.endsWith("_offline_count")
    );
    const group = match
      ? match.replace("sensor.entity_availability_", "").replace("_offline_count", "")
      : "my_devices";
    return {
      group,
      show_availability: true,
      show_entities: true,
      entities_expanded: false,
      show_actions: false,
      compact: false,
    };
  }

  constructor() {
    super();
    this._config = {};
    this._entitiesExpanded = false;
  }

  setConfig(config) {
    if (!config.group) {
      throw new Error("You must define a 'group' in the card configuration.");
    }
    this._config = {
      show_availability: true,
      show_entities: true,
      entities_expanded: false,
      show_actions: false,
      compact: false,
      ...config,
    };
    this._entitiesExpanded = this._config.entities_expanded;
  }

  getCardSize() {
    return this._config.compact ? 3 : 5;
  }

  shouldUpdate(changedProps) {
    if (changedProps.has("_config") || changedProps.has("_entitiesExpanded")) return true;
    if (!this.hass) return false;

    const oldHass = changedProps.get("hass");
    if (!oldHass) return true;

    const ids = this._getAllEntityIds();
    return ids.some((id) => oldHass.states[id] !== this.hass.states[id]);
  }

  render() {
    if (!this._config || !this.hass) {
      return html`<ha-card><div class="error-message">Card not configured.</div></ha-card>`;
    }

    if (!this._config.group) {
      return html`<ha-card><div class="error-message">No group configured.</div></ha-card>`;
    }

    const prefix = `entity_availability_${this._config.group}`;
    const summary = this._getEntity(`sensor.${prefix}_group_summary`);
    const offlineCountEntity = this._getEntity(`sensor.${prefix}_offline_count`);

    if (!summary && !offlineCountEntity) {
      return html`<ha-card>
        <div class="error-message">
          No entities found for group "${this._config.group}".
          Expected: sensor.${prefix}_offline_count
        </div>
      </ha-card>`;
    }

    const attrs = summary?.attributes || {};
    const total = attrs.total_entities || 0;
    const online = attrs.online || 0;
    const offline = attrs.offline || 0;
    const lowBattery = attrs.low_battery || 0;
    const suppressed = attrs.suppressed || 0;
    const entities = attrs.entities || [];
    const batteryLevels = attrs.battery_levels || {};

    const statusColor = offline > 0 ? "red" : lowBattery > 0 ? "yellow" : "green";
    const title = this._config.title || this._formatGroupName(this._config.group);
    const compactClass = this._config.compact ? "compact" : "";

    const statusText = offline > 0
      ? `${offline} Offline`
      : lowBattery > 0
      ? "Degraded"
      : "All OK";

    return html`
      <ha-card class="${compactClass}">
        ${this._renderHeader(title, statusColor, statusText)}
        <div class="divider"></div>
        ${this._renderStats(online, offline, lowBattery, suppressed)}
        ${suppressed > 0 ? html`<div class="suppressed-banner">${suppressed} entity${suppressed > 1 ? "ies" : ""} suppressed</div>` : nothing}
        ${this._config.show_availability ? this._renderAvailability(prefix) : nothing}
        ${this._config.show_entities ? this._renderEntityList(entities, batteryLevels, total) : nothing}
        ${this._config.show_actions ? this._renderActions(prefix) : nothing}
      </ha-card>
    `;
  }

  _renderHeader(title, statusColor, statusText) {
    return html`
      <div class="card-header">
        <div class="header-left">
          <ha-icon
            class="header-icon"
            icon="${STATUS_ICONS[statusColor]}"
            style="color: ${STATUS_COLORS[statusColor]}"
          ></ha-icon>
          <span class="group-title">${title}</span>
        </div>
        <div class="header-right">${statusText}</div>
      </div>
    `;
  }

  _renderStats(online, offline, lowBattery, suppressed) {
    return html`
      <div class="stats-row">
        <span class="stat-item ${online > 0 ? "online" : "neutral"}">Online: ${online}</span>
        <span class="stat-item ${offline > 0 ? "offline" : "neutral"}">Offline: ${offline}</span>
        <span class="stat-item ${lowBattery > 0 ? "battery" : "neutral"}">Low Battery: ${lowBattery}</span>
      </div>
    `;
  }

  _renderAvailability(prefix) {
    const windows = [];
    for (const w of AVAILABILITY_WINDOWS) {
      const entity = this._getEntity(`sensor.${prefix}_availability_${w.key}`);
      if (entity && entity.state !== "unavailable" && entity.state !== "unknown") {
        const pct = parseFloat(entity.state) || 0;
        windows.push({ label: w.label, pct });
      }
    }

    if (windows.length === 0) return nothing;

    return html`
      <div class="divider"></div>
      <div class="availability-section">
        ${windows.map(
          (w) => html`
            <div class="availability-row">
              <span class="availability-label">${w.label}</span>
              <div class="availability-bar">
                <div
                  class="availability-fill"
                  style="width: ${Math.min(100, Math.max(0, w.pct))}%; background-color: ${this._getAvailabilityBarColor(w.pct)}"
                ></div>
              </div>
              <span class="availability-value">${w.pct.toFixed(1)}%</span>
            </div>
          `
        )}
      </div>
    `;
  }

  _renderEntityList(entities, batteryLevels, total) {
    if (entities.length === 0 && total === 0) return nothing;

    const items = this._buildEntityItems(entities, batteryLevels);
    const expanded = this._entitiesExpanded;
    const hasBattery = items.some((i) => i.battery !== null);

    return html`
      <div class="divider"></div>
      <div class="entity-section-header" @click=${this._toggleEntities}>
        <span class="entity-section-title">
          Entities (${items.length})
        </span>
        <ha-icon
          class="chevron ${expanded ? "expanded" : ""}"
          icon="mdi:chevron-down"
        ></ha-icon>
      </div>
      <div class="entity-list ${expanded ? "expanded" : "collapsed"}">
        <div class="entity-legend">
          <span class="entity-legend-dot"></span>
          <span class="entity-legend-name">Entity</span>
          <span class="entity-legend-status">State</span>
          ${hasBattery ? html`<span class="entity-legend-battery">Bat.</span>` : nothing}
        </div>
        ${items.map(
          (item) => html`
            <div class="entity-item">
              <div class="entity-dot ${item.dotColor}"></div>
              <span class="entity-name">${item.name}</span>
              <span class="entity-status">${item.status}</span>
              ${hasBattery
                ? html`<span class="entity-battery">${item.battery !== null ? `${item.battery}%` : ""}</span>`
                : nothing}
            </div>
          `
        )}
      </div>
    `;
  }

  _renderActions(prefix) {
    return html`
      <div class="divider"></div>
      <div class="actions-section">
        <button class="action-btn suppress" @click=${this._handleSuppressAll}>
          Suppress All
        </button>
        <button class="action-btn unsuppress" @click=${this._handleUnsuppressAll}>
          Unsuppress All
        </button>
      </div>
    `;
  }

  _buildEntityItems(entities, batteryLevels) {
    const items = entities.map((entityId) => {
      const state = this.hass.states[entityId];
      const friendlyName = state?.attributes?.friendly_name || entityId.split(".").pop();
      const offlineEntities = this._getOfflineEntityIds();
      const isOffline = offlineEntities.includes(entityId);
      const battery = batteryLevels[entityId] ?? null;
      const batteryThreshold = 20;

      let dotColor = "green";
      let status = "Online";

      if (isOffline) {
        dotColor = "red";
        status = this._computeDuration(entityId) || "Offline";
      } else if (battery !== null && battery < batteryThreshold) {
        dotColor = "yellow";
        status = "Low Battery";
      }

      return { entityId, name: friendlyName, dotColor, status, battery, isOffline };
    });

    items.sort((a, b) => {
      if (a.isOffline && !b.isOffline) return -1;
      if (!a.isOffline && b.isOffline) return 1;
      if (a.dotColor === "yellow" && b.dotColor === "green") return -1;
      if (a.dotColor === "green" && b.dotColor === "yellow") return 1;
      return a.name.localeCompare(b.name);
    });

    return items;
  }

  _getOfflineEntityIds() {
    const prefix = `entity_availability_${this._config.group}`;
    const entity = this._getEntity(`sensor.${prefix}_offline_entities`);
    if (!entity || !entity.attributes) return [];
    return entity.attributes.entities || [];
  }

  _getEntity(entityId) {
    return this.hass?.states?.[entityId];
  }

  _getAllEntityIds() {
    const prefix = `entity_availability_${this._config.group}`;
    return [
      `sensor.${prefix}_group_summary`,
      `sensor.${prefix}_offline_count`,
      `sensor.${prefix}_offline_entities`,
      `sensor.${prefix}_low_battery`,
      `sensor.${prefix}_availability_today`,
      `sensor.${prefix}_availability_3d`,
      `sensor.${prefix}_availability_5d`,
      `sensor.${prefix}_availability_7d`,
      `binary_sensor.${prefix}_any_offline`,
    ];
  }

  _computeDuration(entityId) {
    const state = this.hass?.states?.[entityId];
    if (!state?.last_changed) return null;

    const diff = Date.now() - new Date(state.last_changed).getTime();
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  }

  _getAvailabilityColor(pct) {
    const t = this._config.availability_thresholds || { green: 99, yellow: 95 };
    if (pct >= t.green) return "green";
    if (pct >= t.yellow) return "yellow";
    return "red";
  }

  _getAvailabilityBarColor(pct) {
    const t = this._config.availability_thresholds || { green: 99, yellow: 95 };
    const c = this._config.availability_colors || { green: "#4caf50", yellow: "#ff9800", red: "#f44336" };
    if (pct >= t.green) return c.green;
    if (pct >= t.yellow) return c.yellow;
    return c.red;
  }

  _formatGroupName(group) {
    return group.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  _toggleEntities() {
    this._entitiesExpanded = !this._entitiesExpanded;
  }

  async _handleSuppressAll(e) {
    e.stopPropagation();
    const offlineIds = this._getOfflineEntityIds();
    for (const entityId of offlineIds) {
      await this.hass.callService("entity_availability", "suppress", {
        entity_id: entityId,
        duration: 60,
      });
    }
  }

  async _handleUnsuppressAll(e) {
    e.stopPropagation();
    const prefix = `entity_availability_${this._config.group}`;
    const summary = this._getEntity(`sensor.${prefix}_group_summary`);
    const entities = summary?.attributes?.entities || [];
    for (const entityId of entities) {
      await this.hass.callService("entity_availability", "unsuppress", {
        entity_id: entityId,
      });
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
      .editor-row input[type="text"] {
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
      .color-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
      }
      .color-row label {
        font-size: 13px;
        min-width: 80px;
      }
      .color-row input[type="color"] {
        width: 36px;
        height: 28px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        cursor: pointer;
        padding: 2px;
      }
      .color-row input[type="number"] {
        width: 60px;
        padding: 4px 6px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
      }
      .threshold-section {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .threshold-section > label {
        display: block;
        font-weight: 500;
        margin-bottom: 8px;
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
            @input=${(e) => this._updateConfig("group", e.target.value)}
            placeholder="e.g. security_devices"
          />
        </div>
        <div class="editor-row">
          <label>Title (optional)</label>
          <input
            type="text"
            .value=${this._config.title || ""}
            @input=${(e) => this._updateConfig("title", e.target.value || undefined)}
            placeholder="Custom card title"
          />
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.show_availability !== false}
              @change=${(e) => this._updateConfig("show_availability", e.target.checked)}
            />
            Show Availability Bars
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.show_entities !== false}
              @change=${(e) => this._updateConfig("show_entities", e.target.checked)}
            />
            Show Entity List
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.entities_expanded === true}
              @change=${(e) => this._updateConfig("entities_expanded", e.target.checked)}
            />
            Entity List Expanded by Default
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.show_actions === true}
              @change=${(e) => this._updateConfig("show_actions", e.target.checked)}
            />
            Show Suppress/Unsuppress Buttons
          </label>
        </div>
        <div class="editor-row checkbox">
          <label>
            <input
              type="checkbox"
              .checked=${this._config.compact === true}
              @change=${(e) => this._updateConfig("compact", e.target.checked)}
            />
            Compact Mode
          </label>
        </div>
        <div class="threshold-section">
          <label>Availability Bar Colors & Thresholds</label>
          <div class="color-row">
            <label>High ≥</label>
            <input
              type="number"
              min="0" max="100"
              .value=${(this._config.availability_thresholds?.green ?? 99).toString()}
              @input=${(e) => this._updateThreshold("green", e.target.value)}
            />
            <span>%</span>
            <input
              type="color"
              .value=${this._config.availability_colors?.green || "#4caf50"}
              @input=${(e) => this._updateColor("green", e.target.value)}
            />
          </div>
          <div class="color-row">
            <label>Mid ≥</label>
            <input
              type="number"
              min="0" max="100"
              .value=${(this._config.availability_thresholds?.yellow ?? 95).toString()}
              @input=${(e) => this._updateThreshold("yellow", e.target.value)}
            />
            <span>%</span>
            <input
              type="color"
              .value=${this._config.availability_colors?.yellow || "#ff9800"}
              @input=${(e) => this._updateColor("yellow", e.target.value)}
            />
          </div>
          <div class="color-row">
            <label>Low below</label>
            <input
              type="color"
              .value=${this._config.availability_colors?.red || "#f44336"}
              @input=${(e) => this._updateColor("red", e.target.value)}
            />
          </div>
        </div>
      </div>
    `;
  }

  _updateThreshold(level, value) {
    const thresholds = { ...(this._config.availability_thresholds || { green: 99, yellow: 95 }) };
    thresholds[level] = parseInt(value, 10) || 0;
    this._updateConfig("availability_thresholds", thresholds);
  }

  _updateColor(level, value) {
    const colors = { ...(this._config.availability_colors || { green: "#4caf50", yellow: "#ff9800", red: "#f44336" }) };
    colors[level] = value;
    this._updateConfig("availability_colors", colors);
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

customElements.define("entity-availability-card-editor", EntityAvailabilityCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "entity-availability-card",
  name: "Entity Availability Card",
  description: "Dashboard-style entity health monitoring with availability bars and entity list.",
  preview: true,
  documentationURL: "https://github.com/italo-lombardi/Home-Assistant-EntityAvailability",
});
