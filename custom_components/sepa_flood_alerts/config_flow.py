"""Config flow for the SEPA Flood Alerts integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_EASTING, CONF_NORTHING, CONF_POSTCODE, CONF_RADIUS_KM, DOMAIN
from .coordinator import resolve_postcode

_LOGGER = logging.getLogger(__name__)

DEFAULT_RADIUS_KM = 15


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].strip().upper()
            radius_km = int(user_input[CONF_RADIUS_KM])
            try:
                session = async_get_clientsession(self.hass)
                result = await resolve_postcode(session, postcode)
                if not result:
                    errors[CONF_POSTCODE] = "postcode_not_found"
                else:
                    easting = result["eastings"]
                    northing = result["northings"]
                    await self.async_set_unique_id(postcode)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=postcode,
                        data={
                            CONF_POSTCODE: postcode,
                            CONF_EASTING: easting,
                            CONF_NORTHING: northing,
                            CONF_RADIUS_KM: radius_km,
                        },
                    )
            except Exception:
                _LOGGER.exception("Error resolving postcode")
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_POSTCODE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
                vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=50, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
