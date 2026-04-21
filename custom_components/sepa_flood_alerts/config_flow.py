"""Config flow for the SEPA Flood Alerts integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import CONF_RADIUS_KM, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_RADIUS_KM = 15


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id("home")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self.hass.config.location_name or "Home",
                data={CONF_RADIUS_KM: int(user_input[CONF_RADIUS_KM])},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=50, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors={})
