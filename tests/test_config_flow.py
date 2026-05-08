"""Tests for the Entity Availability config flow."""

from __future__ import annotations

from unittest.mock import patch


from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_availability.const import (
    CONF_AVAILABILITY_WINDOWS,
    CONF_BAD_STATES,
    CONF_BATTERY_ENTITY_MAP,
    CONF_BATTERY_THRESHOLD,
    CONF_COMBINED_GROUPS,
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_GROUP_NAME,
    CONF_STALENESS_THRESHOLD,
    DEFAULT_AVAILABILITY_WINDOWS,
    DEFAULT_BAD_STATES,
    DEFAULT_COOLDOWN,
    DEFAULT_STALENESS_THRESHOLD,
    DOMAIN,
    ENTRY_TYPE_COMBINED,
    ENTRY_TYPE_GROUP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _init_flow(hass: HomeAssistant) -> dict:
    """Start a new config flow and return the initial result."""
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _step_group(
    hass: HomeAssistant, flow_id: str, name: str, entities: list
) -> dict:
    """Submit the type-selector and the group step in one go."""
    # First pick "group" entry type
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"entry_type": ENTRY_TYPE_GROUP}
    )
    assert result["step_id"] == "group"
    # Then fill in name + entities
    return await hass.config_entries.flow.async_configure(
        flow_id, {CONF_GROUP_NAME: name, CONF_ENTITIES: entities}
    )


# ---------------------------------------------------------------------------
# user step
# ---------------------------------------------------------------------------


async def test_step_user_shows_form(hass: HomeAssistant) -> None:
    """Test that the first step shows the type-selector form."""
    result = await _init_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_group_goes_to_group(hass: HomeAssistant) -> None:
    """Choosing 'group' advances to the group step."""
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_GROUP}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "group"


async def test_step_user_combined_aborts_without_enough_groups(
    hass: HomeAssistant,
) -> None:
    """Choosing 'combined_group' aborts when < 2 source groups exist."""
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "not_enough_groups"


# ---------------------------------------------------------------------------
# group step
# ---------------------------------------------------------------------------


async def test_step_group_empty_name(hass: HomeAssistant) -> None:
    """Validation error on blank group name."""
    result = await _init_flow(hass)
    # Get to group step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_GROUP}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_GROUP_NAME: "   ", CONF_ENTITIES: ["binary_sensor.test"]},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_GROUP_NAME: "empty_group_name"}


async def test_step_group_no_entities(hass: HomeAssistant) -> None:
    """Validation error when no entities selected."""
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_GROUP}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_GROUP_NAME: "Test Group", CONF_ENTITIES: []},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_ENTITIES: "no_entities"}


async def test_step_group_valid_goes_to_monitoring(hass: HomeAssistant) -> None:
    """Valid group input advances to monitoring step."""
    result = await _init_flow(hass)
    result = await _step_group(
        hass, result["flow_id"], "My Devices", ["binary_sensor.test"]
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "monitoring"


# ---------------------------------------------------------------------------
# monitoring / advanced / battery_mapping steps
# ---------------------------------------------------------------------------


async def test_step_monitoring_goes_to_advanced(hass: HomeAssistant) -> None:
    """Monitoring step advances to advanced step."""
    result = await _init_flow(hass)
    result = await _step_group(
        hass, result["flow_id"], "My Devices", ["binary_sensor.test"]
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BAD_STATES: DEFAULT_BAD_STATES,
            CONF_COOLDOWN: DEFAULT_COOLDOWN,
            CONF_STALENESS_THRESHOLD: DEFAULT_STALENESS_THRESHOLD,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"


async def test_full_config_flow_with_battery(hass: HomeAssistant) -> None:
    """Test complete flow with battery threshold > 0 shows battery mapping step."""
    result = await _init_flow(hass)

    # Step 1: type-selector + group
    result = await _step_group(
        hass,
        result["flow_id"],
        "Office Devices",
        ["sensor.desk_lamp", "binary_sensor.motion"],
    )
    assert result["step_id"] == "monitoring"

    # Step 2: Monitoring
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BAD_STATES: ["unavailable"],
            CONF_COOLDOWN: 120,
            CONF_STALENESS_THRESHOLD: 30,
        },
    )
    assert result["step_id"] == "advanced"

    # Step 3: Advanced (battery > 0)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BATTERY_THRESHOLD: 10, CONF_AVAILABILITY_WINDOWS: ["today", "7d"]},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "battery_mapping"

    # Step 4: Battery mapping
    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"sensor.desk_lamp": "sensor.desk_lamp_battery"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Office Devices"
    assert result["data"][CONF_BATTERY_THRESHOLD] == 10
    assert result["data"][CONF_BATTERY_ENTITY_MAP] == {
        "sensor.desk_lamp": "sensor.desk_lamp_battery",
        "binary_sensor.motion": "",
    }


async def test_full_config_flow_no_battery(hass: HomeAssistant) -> None:
    """Test complete flow with battery threshold = 0 skips battery mapping."""
    result = await _init_flow(hass)

    result = await _step_group(
        hass, result["flow_id"], "Office Devices", ["sensor.desk_lamp"]
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BAD_STATES: ["unavailable"],
            CONF_COOLDOWN: 60,
            CONF_STALENESS_THRESHOLD: 0,
        },
    )

    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_BATTERY_THRESHOLD: 0, CONF_AVAILABILITY_WINDOWS: ["today", "7d"]},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_ENTITY_MAP] == {}


async def test_duplicate_prevention(hass: HomeAssistant) -> None:
    """Test that duplicate unique_id is prevented."""
    result = await _init_flow(hass)
    result = await _step_group(hass, result["flow_id"], "My Group", ["sensor.test"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BAD_STATES: DEFAULT_BAD_STATES,
            CONF_COOLDOWN: DEFAULT_COOLDOWN,
            CONF_STALENESS_THRESHOLD: DEFAULT_STALENESS_THRESHOLD,
        },
    )
    # battery_threshold = 0 → skip battery mapping
    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BATTERY_THRESHOLD: 0,
                CONF_AVAILABILITY_WINDOWS: DEFAULT_AVAILABILITY_WINDOWS,
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Second flow with same name should be aborted at group step
    result2 = await _init_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {"entry_type": ENTRY_TYPE_GROUP}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_GROUP_NAME: "My Group", CONF_ENTITIES: ["sensor.other"]},
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test options flow with battery threshold = 0 skips battery mapping."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ENTITIES: ["binary_sensor.device_a", "binary_sensor.device_b"],
            CONF_BAD_STATES: ["unavailable"],
            CONF_COOLDOWN: 90,
            CONF_STALENESS_THRESHOLD: 15,
            CONF_BATTERY_THRESHOLD: 0,
            CONF_AVAILABILITY_WINDOWS: ["today", "3d"],
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    assert mock_config_entry.data[CONF_COOLDOWN] == 90
    assert mock_config_entry.data[CONF_BATTERY_ENTITY_MAP] == {}


async def test_options_flow_with_battery_mapping(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test options flow with battery threshold > 0 shows battery mapping."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ENTITIES: ["binary_sensor.device_a", "binary_sensor.device_b"],
            CONF_BAD_STATES: ["unavailable"],
            CONF_COOLDOWN: 60,
            CONF_STALENESS_THRESHOLD: 0,
            CONF_BATTERY_THRESHOLD: 25,
            CONF_AVAILABILITY_WINDOWS: ["today"],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "battery_mapping"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"binary_sensor.device_a": "sensor.device_a_battery"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.data[CONF_BATTERY_ENTITY_MAP] == {
        "binary_sensor.device_a": "sensor.device_a_battery",
        "binary_sensor.device_b": "",
    }


async def test_battery_auto_detection(hass: HomeAssistant) -> None:
    """Test that battery entity auto-detection works in config flow."""
    # Set up a battery entity state so convention-based detection finds it
    hass.states.async_set("sensor.desk_lamp_battery", "85")

    result = await _init_flow(hass)
    result = await _step_group(
        hass, result["flow_id"], "Detection Test", ["light.desk_lamp"]
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BAD_STATES: DEFAULT_BAD_STATES,
            CONF_COOLDOWN: DEFAULT_COOLDOWN,
            CONF_STALENESS_THRESHOLD: DEFAULT_STALENESS_THRESHOLD,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BATTERY_THRESHOLD: 20,
            CONF_AVAILABILITY_WINDOWS: DEFAULT_AVAILABILITY_WINDOWS,
        },
    )
    # Should show battery_mapping with pre-detected value
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "battery_mapping"


# ---------------------------------------------------------------------------
# Combined group config flow
# ---------------------------------------------------------------------------


async def _create_group_entry(
    hass: HomeAssistant, name: str, entities: list[str]
) -> MockConfigEntry:
    """Helper: create and register a real group config entry."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title=name,
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_GROUP,
            CONF_GROUP_NAME: name,
            CONF_ENTITIES: entities,
        },
        entry_id=f"entry_{name.lower().replace(' ', '_')}",
        unique_id=f"{DOMAIN}_{name.lower().replace(' ', '_')}",
    )
    entry.add_to_hass(hass)
    return entry


async def test_step_combined_shows_form(hass: HomeAssistant) -> None:
    """When >=2 group entries exist, combined step shows a form."""
    await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "combined"


async def test_step_combined_empty_name_error(hass: HomeAssistant) -> None:
    """Blank combined group name raises validation error."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    entry_b = await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "   ",
            CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_GROUP_NAME: "empty_group_name"}


async def test_step_combined_not_enough_groups_selected_error(
    hass: HomeAssistant,
) -> None:
    """Selecting < 2 groups raises validation error."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_GROUP_NAME: "My Combined", CONF_COMBINED_GROUPS: [entry_a.entry_id]},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_COMBINED_GROUPS: "not_enough_groups_selected"}


async def test_step_combined_creates_entry(hass: HomeAssistant) -> None:
    """Valid combined group input creates a config entry."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    entry_b = await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_GROUP_NAME: "My Combined",
                CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Combined"
    assert result["data"][CONF_ENTRY_TYPE] == ENTRY_TYPE_COMBINED
    assert result["data"][CONF_COMBINED_GROUPS] == [entry_a.entry_id, entry_b.entry_id]


async def test_step_combined_duplicate_prevention(hass: HomeAssistant) -> None:
    """Creating a combined group with the same name is aborted."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    entry_b = await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    # First combined entry
    result = await _init_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_GROUP_NAME: "My Combined",
                CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Second combined entry with the same name
    result2 = await _init_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], {"entry_type": ENTRY_TYPE_COMBINED}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_GROUP_NAME: "My Combined",
            CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
        },
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_combined_options_flow_shows_form(hass: HomeAssistant) -> None:
    """Options flow for a combined entry shows the init form."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    entry_b = await _create_group_entry(hass, "Group B", ["binary_sensor.b"])

    combined = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="My Combined",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_COMBINED,
            CONF_GROUP_NAME: "My Combined",
            CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
        },
        entry_id="combined_entry_id",
        unique_id=f"{DOMAIN}_combined_my_combined",
    )
    combined.add_to_hass(hass)

    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(combined.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(combined.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "combined_init"


async def test_combined_options_flow_updates_entry(hass: HomeAssistant) -> None:
    """Options flow for combined entry saves new name and groups."""
    entry_a = await _create_group_entry(hass, "Group A", ["binary_sensor.a"])
    entry_b = await _create_group_entry(hass, "Group B", ["binary_sensor.b"])
    entry_c = await _create_group_entry(hass, "Group C", ["binary_sensor.c"])

    combined = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="My Combined",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_COMBINED,
            CONF_GROUP_NAME: "My Combined",
            CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_b.entry_id],
        },
        entry_id="combined_entry_id2",
        unique_id=f"{DOMAIN}_combined_my_combined_v2",
    )
    combined.add_to_hass(hass)

    with patch(
        "custom_components.entity_availability.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(combined.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(combined.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "Renamed Combined",
            CONF_COMBINED_GROUPS: [entry_a.entry_id, entry_c.entry_id],
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert combined.data[CONF_GROUP_NAME] == "Renamed Combined"
    assert combined.data[CONF_COMBINED_GROUPS] == [entry_a.entry_id, entry_c.entry_id]
