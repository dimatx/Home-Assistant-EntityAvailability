"""Coordinator-aware entity bases that skip writes when state and attrs are unchanged.

Home Assistant writes a new history row every time ``async_write_ha_state`` is
called. ``CoordinatorEntity`` triggers that call on every coordinator tick
(every ``SCAN_INTERVAL`` seconds), regardless of whether the entity's value
actually changed. For sensors that aggregate offline counts, friendly-name
lists, or per-device dictionaries, the value is identical the vast majority of
ticks, so each refresh produces a redundant recorder row.

The mixin and base classes in this module compare the just-computed
``native_value``/``is_on`` and ``extra_state_attributes`` against the previously
published pair and short-circuit ``async_write_ha_state`` when both match.
The first write always goes through (the cache starts empty), so there is no
risk of an entity never publishing an initial value.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import EntityAvailabilityCoordinator

_UNSET: Any = object()


class WriteDedupMixin:
    """Cache the last published value and attrs and decide whether to write."""

    _ea_last_value: Any = _UNSET
    _ea_last_attrs: Any = _UNSET

    def _ea_current_value(self) -> Any:
        """Return the value subclasses publish (``native_value`` or ``is_on``)."""
        raise NotImplementedError

    def _ea_should_write(self) -> bool:
        """Return True when value or attrs differ from the cached pair."""
        value = self._ea_current_value()
        attrs = getattr(self, "extra_state_attributes", None)
        if value == self._ea_last_value and attrs == self._ea_last_attrs:
            return False
        self._ea_last_value = value
        self._ea_last_attrs = attrs
        return True


class DedupCoordinatorSensor(
    WriteDedupMixin,
    CoordinatorEntity[EntityAvailabilityCoordinator],
    SensorEntity,
):
    """``SensorEntity`` base that skips unchanged coordinator-driven writes."""

    def _ea_current_value(self) -> Any:
        return self.native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write only when the published value or attrs changed."""
        if self._ea_should_write():
            self.async_write_ha_state()


class DedupCoordinatorBinarySensor(
    WriteDedupMixin,
    CoordinatorEntity[EntityAvailabilityCoordinator],
    BinarySensorEntity,
):
    """``BinarySensorEntity`` base with the same dedup behavior."""

    def _ea_current_value(self) -> Any:
        return self.is_on

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write only when the published value or attrs changed."""
        if self._ea_should_write():
            self.async_write_ha_state()
