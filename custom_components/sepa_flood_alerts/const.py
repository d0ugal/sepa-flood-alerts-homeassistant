"""Constants for the SEPA Flood Alerts integration."""

DOMAIN = "sepa_flood_alerts"

CONF_POSTCODE = "postcode"
CONF_EASTING = "easting"
CONF_NORTHING = "northing"
CONF_RADIUS_KM = "radius_km"

SEPA_API_BASE = "https://eu2-apigateway.htkhorizon.com/sepa/ffims/v1"
# Public integrator key from the SEPA FFIMS API test suite
SEPA_API_KEY = "21RKbqIHvu9bKct9QW5ba2do6DGCcRzH17IXnJdU"

SEVERITY_NAMES: dict[int, str] = {
    1: "Severe Flood Warning",
    2: "Flood Warning",
    3: "Flood Alert",
}
