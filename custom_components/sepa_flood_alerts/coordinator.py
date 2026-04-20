"""Data coordinator for the SEPA Flood Alerts integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_EASTING, CONF_NORTHING, CONF_RADIUS_KM, DOMAIN, SEPA_API_BASE, SEPA_API_KEY, SEVERITY_NAMES

_LOGGER = logging.getLogger(__name__)


@dataclass
class FloodAlert:
    area_id: str
    area_name: str
    message: str
    severity: int
    severity_name: str
    updated_time: str


@dataclass
class FloodAlertsData:
    alerts: list[FloodAlert]

    @property
    def max_severity(self) -> int | None:
        if not self.alerts:
            return None
        return min(a.severity for a in self.alerts)

    @property
    def max_severity_name(self) -> str:
        severity = self.max_severity
        if severity is None:
            return "None"
        return SEVERITY_NAMES.get(severity, "Unknown")


class FloodAlertsCoordinator(DataUpdateCoordinator[FloodAlertsData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self._entry = entry

    async def _async_update_data(self) -> FloodAlertsData:
        easting = self._entry.data[CONF_EASTING]
        northing = self._entry.data[CONF_NORTHING]
        radius_m = self._entry.data[CONF_RADIUS_KM] * 1000
        try:
            session = async_get_clientsession(self.hass)
            return await _fetch_alerts(session, easting, northing, radius_m)
        except Exception as err:
            raise UpdateFailed(f"Error fetching SEPA flood alerts: {err}") from err


async def _fetch_alerts(session, easting: int, northing: int, radius_m: int) -> FloodAlertsData:
    url = f"{SEPA_API_BASE}/warnings/location"
    params = {"x": easting, "y": northing, "radius": radius_m}
    headers = {"x-api-key": SEPA_API_KEY}
    async with session.get(url, params=params, headers=headers) as resp:
        resp.raise_for_status()
        data = await resp.json()
    alerts = []
    for item in data:
        severity = item.get("severity")
        if severity is None or int(severity) >= 4:
            continue
        alerts.append(
            FloodAlert(
                area_id=str(item["id"]),
                area_name=item["name"],
                message=item.get("message") or "",
                severity=int(severity),
                severity_name=SEVERITY_NAMES.get(int(severity), "Unknown"),
                updated_time=item.get("updatedTime") or "",
            )
        )
    alerts.sort(key=lambda a: a.severity)
    return FloodAlertsData(alerts=alerts)


async def resolve_postcode(session, postcode: str) -> dict:
    url = f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '%20')}"
    async with session.get(url) as resp:
        if resp.status == 404:
            return {}
        resp.raise_for_status()
        data = await resp.json()
    if data.get("status") != 200:
        return {}
    return data.get("result", {})
