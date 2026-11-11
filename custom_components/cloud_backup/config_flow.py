from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ACCESS_KEY,
    CONF_BUCKET_NAME,
    CONF_DELETE_LOCAL,
    CONF_SECRET_KEY,
    DEFAULT_DELETE_LOCAL,
    DOMAIN,
)
from .manifest import manifest
from .qiniu import Qiniu

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_KEY): str,
        vol.Required(CONF_SECRET_KEY): str,
        vol.Required(CONF_BUCKET_NAME): str,
    }
)


class SimpleConfigFlow(ConfigFlow, domain=DOMAIN):
    """配置七牛云凭据。"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """处理初始配置步骤。"""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            access_key = user_input[CONF_ACCESS_KEY].strip()
            secret_key = user_input[CONF_SECRET_KEY].strip()
            bucket_name = user_input[CONF_BUCKET_NAME].strip()
            qn = Qiniu(self.hass, access_key, secret_key, bucket_name)
            try:
                validated = await self.hass.async_add_executor_job(qn.validate)
            except Exception:  # noqa: BLE001
                validated = False
            if not validated:
                errors["base"] = "fail"
            else:
                return self.async_create_entry(
                    title=DOMAIN,
                    data={
                        CONF_ACCESS_KEY: access_key,
                        CONF_SECRET_KEY: secret_key,
                        CONF_BUCKET_NAME: bucket_name,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """返回选项流。"""
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """选项：是否上传后删除本地备份。"""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """管理选项。"""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DELETE_LOCAL,
                    default=self.config_entry.options.get(
                        CONF_DELETE_LOCAL, DEFAULT_DELETE_LOCAL
                    ),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
