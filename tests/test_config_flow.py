"""Tests for the Entity Availability config flow."""
from __future__ import annotations

from unittest.mock import patch


from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.entity_availability.const import (
    CONF_AVAILABILITY_WINDOWS,
    CONF_BAD_STATES,
    CONF_BATTERY_ENTITY_MAP,
    CONF_BATTERY_THRESHOLD,
    CONF_COOLDOWN,
    CONF_ENTITIES,
    CONF_GROUP_NAME,
    CONF_STALENESS_THRESHOLD,
    DEFAULT_AVAILABILITY_WINDOWS,
    DEFAULT_BAD_STATES,
    DEFAULT_COOLDOWN,
    DEFAULT_STALENESS_THRESHOLD,
    DOMAIN,
)


async def test_step_user_shows_form(hass: HomeAssistant) -> None:
    """Test that the first step shows the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_step_user_empty_group_name(hass: HomeAssistant) -> None:
    """Test validation error on empty group name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "   ",
            CONF_ENTITIES: ["binary_sensor.test"],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_GROUP_NAME: "empty_group_name"}


async def test_step_user_no_entities(hass: HomeAssistant) -> None:
    """Test validation error when no entities selected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "Test Group",
            CONF_ENTITIES: [],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_ENTITIES: "no_entities"}


async def test_step_user_valid_goes_to_monitoring(hass: HomeAssistant) -> None:
    """Test valid user input advances to monitoring step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "My Devices",
            CONF_ENTITIES: ["binary_sensor.test"],
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "monitoring"


async def test_step_monitoring_goes_to_advanced(hass: HomeAssistant) -> None:
    """Test monitoring step advances to advanced step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "My Devices",
            CONF_ENTITIES: ["binary_sensor.test"],
        },
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
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: User
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "Office Devices",
            CONF_ENTITIES: ["sensor.desk_lamp", "binary_sensor.motion"],
        },
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
        {
            CONF_BATTERY_THRESHOLD: 10,
            CONF_AVAILABILITY_WINDOWS: ["today", "7d"],
        },
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
            {
                "sensor.desk_lamp": "sensor.desk_lamp_battery",
            },
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
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "Office Devices",
            CONF_ENTITIES: ["sensor.desk_lamp"],
        },
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
            {
                CONF_BATTERY_THRESHOLD: 0,
                CONF_AVAILABILITY_WINDOWS: ["today", "7d"],
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_ENTITY_MAP] == {}


async def test_duplicate_prevention(hass: HomeAssistant) -> None:
    """Test that duplicate unique_id is prevented."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "My Group",
            CONF_ENTITIES: ["sensor.test"],
        },
    )
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

    # Second flow with same name should be aborted
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_GROUP_NAME: "My Group",
            CONF_ENTITIES: ["sensor.other"],
        },
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


async def test_options_flow_with_battery_mapping(hass: HomeAssistant, mock_config_entry) -> None:
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
        {
            "binary_sensor.device_a": "sensor.device_a_battery",
        },
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

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_GROUP_NAME: "Detection Test",
            CONF_ENTITIES: ["light.desk_lamp"],
        },
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
