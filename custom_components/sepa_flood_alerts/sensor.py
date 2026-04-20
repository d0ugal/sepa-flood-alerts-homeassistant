"""Sensor platform for the SEPA Flood Alerts integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FloodAlertsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FloodAlertsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SepaFloodSeveritySensor(coordinator, entry)])


class SepaFloodSeveritySensor(CoordinatorEntity[FloodAlertsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Flood severity"

    def __init__(self, coordinator: FloodAlertsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_flood_severity"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"SEPA Flood Alerts ({entry.data['postcode']})",
        )

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "None"
        return self.coordinator.data.max_severity_name

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        return {
            "alerts": [
                {
                    "area_name": a.area_name,
                    "severity_name": a.severity_name,
                    "message": a.message,
                    "updated_time": a.updated_time,
                }
                for a in self.coordinator.data.alerts[:10]
            ],
        }
