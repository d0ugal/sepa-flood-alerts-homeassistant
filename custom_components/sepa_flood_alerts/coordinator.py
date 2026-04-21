"""Data coordinator for the SEPA Flood Alerts integration."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_RADIUS_KM,
    DOMAIN,
    SEPA_API_BASE,
    SEPA_API_KEY,
    SEVERITY_NAMES,
)

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
        easting, northing = _latlon_to_osgb36(
            self.hass.config.latitude, self.hass.config.longitude
        )
        radius_m = self._entry.data[CONF_RADIUS_KM] * 1000
        try:
            session = async_get_clientsession(self.hass)
            return await _fetch_alerts(session, easting, northing, radius_m)
        except Exception as err:
            raise UpdateFailed(f"Error fetching SEPA flood alerts: {err}") from err


async def _fetch_alerts(
    session, easting: int, northing: int, radius_m: int
) -> FloodAlertsData:
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


def _latlon_to_osgb36(lat: float, lon: float) -> tuple[int, int]:
    """Convert WGS84 lat/lon (degrees) to OSGB36 easting/northing (metres).

    Implements the standard OS Transverse Mercator algorithm via a Helmert
    datum transformation from WGS84 to Airy 1830 (OSGB36).
    """
    a_wgs, b_wgs = 6378137.000, 6356752.3141
    e2_wgs = 1 - (b_wgs / a_wgs) ** 2

    lat_r = math.radians(lat)
    lon_r = math.radians(lon)

    nu_wgs = a_wgs / math.sqrt(1 - e2_wgs * math.sin(lat_r) ** 2)
    x1 = nu_wgs * math.cos(lat_r) * math.cos(lon_r)
    y1 = nu_wgs * math.cos(lat_r) * math.sin(lon_r)
    z1 = nu_wgs * (1 - e2_wgs) * math.sin(lat_r)

    # Helmert parameters: WGS84 → OSGB36
    tx, ty, tz = -446.448, 125.157, -542.060
    rx = math.radians(-0.1502 / 3600)
    ry = math.radians(-0.2470 / 3600)
    rz = math.radians(-0.8421 / 3600)
    s = 1 + 20.4894e-6

    x2 = tx + s * (x1 - rz * y1 + ry * z1)
    y2 = ty + s * (rz * x1 + y1 - rx * z1)
    z2 = tz + s * (-ry * x1 + rx * y1 + z1)

    # Cartesian → Airy 1830 geodetic
    a_airy, b_airy = 6377563.396, 6356256.909
    e2_airy = 1 - (b_airy / a_airy) ** 2

    lon2_r = math.atan2(y2, x2)
    p = math.sqrt(x2**2 + y2**2)
    lat2_r = math.atan2(z2, p * (1 - e2_airy))
    for _ in range(10):
        nu = a_airy / math.sqrt(1 - e2_airy * math.sin(lat2_r) ** 2)
        lat2_new = math.atan2(z2 + e2_airy * nu * math.sin(lat2_r), p)
        if abs(lat2_new - lat2_r) < 1e-12:
            break
        lat2_r = lat2_new

    # Transverse Mercator projection (National Grid)
    a, b, e2 = a_airy, b_airy, e2_airy
    n0, e0 = -100000.0, 400000.0
    f0 = 0.9996012717
    lat0_r = math.radians(49.0)
    lon0_r = math.radians(-2.0)

    n = (a - b) / (a + b)
    nu = a * f0 / math.sqrt(1 - e2 * math.sin(lat2_r) ** 2)
    rho = a * f0 * (1 - e2) / (1 - e2 * math.sin(lat2_r) ** 2) ** 1.5
    eta2 = nu / rho - 1

    M = (
        b
        * f0
        * (
            (1 + n + 5 / 4 * n**2 + 5 / 4 * n**3) * (lat2_r - lat0_r)
            - (3 * n + 3 * n**2 + 21 / 8 * n**3)
            * math.sin(lat2_r - lat0_r)
            * math.cos(lat2_r + lat0_r)
            + (15 / 8 * n**2 + 15 / 8 * n**3)
            * math.sin(2 * (lat2_r - lat0_r))
            * math.cos(2 * (lat2_r + lat0_r))
            - (35 / 24 * n**3)
            * math.sin(3 * (lat2_r - lat0_r))
            * math.cos(3 * (lat2_r + lat0_r))
        )
    )

    t = math.tan(lat2_r)
    c = math.cos(lat2_r)
    dl = lon2_r - lon0_r

    northing = (
        M
        + n0
        + nu / 2 * math.sin(lat2_r) * c * dl**2
        + nu / 24 * math.sin(lat2_r) * c**3 * (5 - t**2 + 9 * eta2) * dl**4
        + nu / 720 * math.sin(lat2_r) * c**5 * (61 - 58 * t**2 + t**4) * dl**6
    )
    easting = (
        e0
        + nu * c * dl
        + nu / 6 * c**3 * (nu / rho - t**2) * dl**3
        + nu
        / 120
        * c**5
        * (5 - 18 * t**2 + t**4 + 14 * eta2 - 58 * t**2 * eta2)
        * dl**5
    )

    return round(easting), round(northing)
