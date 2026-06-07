"""Tests for write-dedup mixin and integration into sensor platforms."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.entity_availability.binary_sensor import AnyOfflineBinarySensor
from custom_components.entity_availability.combined_binary_sensor import (
    CombinedGroupAnyOfflineBinarySensor,
)
from custom_components.entity_availability.combined_sensor import CombinedGroupSensor
from custom_components.entity_availability.const import DOMAIN
from custom_components.entity_availability.coordinator import (
    EntityAvailabilityCoordinator,
)
from custom_components.entity_availability.models import DeviceState
from custom_components.entity_availability.sensor import OfflineCountSensor
from custom_components.entity_availability.write_dedup import (
    DedupCoordinatorBinarySensor,
    DedupCoordinatorSensor,
    WriteDedupMixin,
)


@pytest.fixture
def mock_coordinator(mock_hass: HomeAssistant, mock_config_entry):
    """Coordinator with one offline device."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, mock_config_entry)
        coord._device_states = {
            "binary_sensor.device_a": DeviceState(
                entity_id="binary_sensor.device_a",
                is_offline=False,
            ),
            "binary_sensor.device_b": DeviceState(
                entity_id="binary_sensor.device_b",
                is_offline=True,
                offline_since=datetime.now(timezone.utc) - timedelta(minutes=5),
            ),
        }
        yield coord


def test_mixin_first_call_writes() -> None:
    """First call always returns True because cache is _UNSET."""

    class _S(WriteDedupMixin):
        def __init__(self) -> None:
            self.value = 1
            self.extra_state_attributes: dict = {"a": 1}

        def _ea_current_value(self):
            return self.value

    s = _S()
    assert s._ea_should_write() is True
    # cache populated
    assert s._ea_should_write() is False


def test_mixin_value_change_writes() -> None:
    """Different value triggers write; same value does not."""

    class _S(WriteDedupMixin):
        def __init__(self) -> None:
            self.value = 1
            self.extra_state_attributes: dict = {}

        def _ea_current_value(self):
            return self.value

    s = _S()
    assert s._ea_should_write() is True
    assert s._ea_should_write() is False
    s.value = 2
    assert s._ea_should_write() is True
    assert s._ea_should_write() is False


def test_mixin_attrs_change_writes() -> None:
    """Same value but changed attrs still triggers write."""

    class _S(WriteDedupMixin):
        def __init__(self) -> None:
            self.value = 1
            self.extra_state_attributes: dict = {"a": 1}

        def _ea_current_value(self):
            return self.value

    s = _S()
    assert s._ea_should_write() is True
    assert s._ea_should_write() is False
    s.extra_state_attributes = {"a": 2}
    assert s._ea_should_write() is True


def test_mixin_no_attrs_property() -> None:
    """Subclass without extra_state_attributes uses None and still dedups."""

    class _S(WriteDedupMixin):
        def __init__(self) -> None:
            self.value = 1

        def _ea_current_value(self):
            return self.value

    s = _S()
    assert s._ea_should_write() is True
    assert s._ea_should_write() is False


def test_mixin_default_value_raises() -> None:
    """Base mixin's _ea_current_value is abstract."""
    with pytest.raises(NotImplementedError):
        WriteDedupMixin()._ea_current_value()


def test_dedup_coordinator_sensor_skips_unchanged(mock_coordinator) -> None:
    """`OfflineCountSensor._handle_coordinator_update` writes once, then dedups."""
    sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "eid")
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
    assert write.call_count == 1


def test_dedup_coordinator_sensor_writes_on_change(mock_coordinator) -> None:
    """Bringing a new device offline triggers a fresh write."""
    sensor = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "eid")
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_coordinator_update()
        # Take device_a offline; native_value goes 1 -> 2
        mock_coordinator.device_states["binary_sensor.device_a"].is_offline = True
        mock_coordinator.device_states[
            "binary_sensor.device_a"
        ].offline_since = datetime.now(timezone.utc)
        sensor._handle_coordinator_update()
    assert write.call_count == 2


def test_dedup_coordinator_binary_sensor_skips_unchanged(mock_coordinator) -> None:
    """Binary sensor variant dedups too."""
    sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "eid")
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_coordinator_update()
        sensor._handle_coordinator_update()
    assert write.call_count == 1


def test_dedup_coordinator_binary_sensor_writes_on_change(mock_coordinator) -> None:
    """Flipping every device online flips is_on False -> True path."""
    sensor = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "eid")
    with patch.object(sensor, "async_write_ha_state") as write:
        sensor._handle_coordinator_update()
        # Bring device_b back online
        mock_coordinator.device_states["binary_sensor.device_b"].is_offline = False
        sensor._handle_coordinator_update()
    assert write.call_count == 2


def test_dedup_subclasses_provide_current_value(mock_coordinator) -> None:
    """Sensor subclass returns native_value, binary subclass returns is_on."""
    s = OfflineCountSensor(mock_coordinator, "Test Group", "test_group", "eid")
    assert isinstance(s, DedupCoordinatorSensor)
    assert s._ea_current_value() == s.native_value

    b = AnyOfflineBinarySensor(mock_coordinator, "Test Group", "test_group", "eid")
    assert isinstance(b, DedupCoordinatorBinarySensor)
    assert b._ea_current_value() == b.is_on


@pytest.mark.asyncio
async def test_combined_sensor_dedup(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Combined sensor's added-to-hass listener dedups using the mixin."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, mock_config_entry)
        coord._device_states = {
            "binary_sensor.device_a": DeviceState(
                entity_id="binary_sensor.device_a",
                is_offline=True,
                offline_since=datetime.now(timezone.utc),
            ),
        }

    mock_hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coord

    combined_entry = MockConfigEntry(
        version=1, domain=DOMAIN, title="Combined", data={}, entry_id="combined_eid"
    )
    sensor = CombinedGroupSensor(
        mock_hass,
        combined_entry,
        "Combined",
        "combined",
        [coord],
        [mock_config_entry.entry_id],
    )

    captured: list = []

    def _fake_add_listener(cb):
        captured.append(cb)

        def _unsub():
            return None

        return _unsub

    coord.async_add_listener = MagicMock(side_effect=_fake_add_listener)
    with patch.object(sensor, "async_write_ha_state") as write:
        await sensor.async_added_to_hass()
        assert captured, "listener registered"
        callback_fn = captured[0]
        callback_fn()  # first invocation -> write
        callback_fn()  # unchanged -> skip
        # Mutate value
        coord.device_states["binary_sensor.device_a"].is_offline = False
        callback_fn()  # changed -> write
    assert write.call_count == 2

    await sensor.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_combined_binary_sensor_dedup(
    mock_hass: HomeAssistant, mock_config_entry
) -> None:
    """Combined binary sensor's added-to-hass listener dedups."""
    with patch.object(
        EntityAvailabilityCoordinator, "_async_save_storage", new_callable=AsyncMock
    ):
        coord = EntityAvailabilityCoordinator(mock_hass, mock_config_entry)
        coord._device_states = {
            "binary_sensor.device_a": DeviceState(
                entity_id="binary_sensor.device_a",
                is_offline=True,
                offline_since=datetime.now(timezone.utc),
            ),
        }

    mock_hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coord

    combined_entry = MockConfigEntry(
        version=1, domain=DOMAIN, title="Combined", data={}, entry_id="combined_eid_b"
    )
    sensor = CombinedGroupAnyOfflineBinarySensor(
        mock_hass,
        combined_entry,
        "Combined",
        "combined",
        [coord],
        [mock_config_entry.entry_id],
    )

    captured: list = []

    def _fake_add_listener(cb):
        captured.append(cb)
        return lambda: None

    coord.async_add_listener = MagicMock(side_effect=_fake_add_listener)
    with patch.object(sensor, "async_write_ha_state") as write:
        await sensor.async_added_to_hass()
        callback_fn = captured[0]
        callback_fn()
        callback_fn()
        coord.device_states["binary_sensor.device_a"].is_offline = False
        callback_fn()
    assert write.call_count == 2

    await sensor.async_will_remove_from_hass()
