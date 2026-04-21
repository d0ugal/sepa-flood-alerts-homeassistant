# SEPA Flood Alerts for Home Assistant

A Home Assistant custom integration that surfaces active [SEPA](https://www.sepa.org.uk/) (Scottish Environment Protection Agency) flood warnings as entities.

## Features

- **Binary sensor** — turns `on` when any active flood warning is in range
- **Sensor** — reports the worst active severity level
- Configurable search radius (default 15 km) around your Home Assistant home location
- Polls every 5 minutes

## Severity levels

| State | Meaning |
|-------|---------|
| `None` | No active warnings |
| `Flood Alert` | Flooding is possible — be prepared |
| `Flood Warning` | Flooding is expected — take action |
| `Severe Flood Warning` | Severe flooding — danger to life |

## Installation

### HACS

Add this repository as a custom integration in HACS.

### Manual

Copy `custom_components/sepa_flood_alerts/` into your Home Assistant `custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **SEPA Flood Alerts**
3. Set your search radius

The integration uses the latitude and longitude configured in your Home Assistant instance. The search radius (1–50 km, default 15 km) controls how far from your home location SEPA warning areas are included.

## Automation example

```yaml
automation:
  - alias: "Flood alert notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.sepa_flood_alert
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Flood Alert"
          message: "{{ state_attr('binary_sensor.sepa_flood_alert', 'severity') }} in your area."
```
