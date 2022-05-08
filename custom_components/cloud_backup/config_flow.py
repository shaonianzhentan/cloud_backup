from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .manifest import manifest
from .qiniu import Qiniu

DOMAIN = manifest.domain
DATA_SCHEMA = vol.Schema({
    vol.Required("access_key"): str,
    vol.Required("secret_key"): str,
    vol.Required("bucket_name"): str
})

class SimpleConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        errors = {}
        if user_input is not None:
            # validate
            access_key = user_input.get('access_key')
            secret_key = user_input.get('secret_key')
            bucket_name = user_input.get('bucket_name')
            qn = Qiniu(access_key, secret_key, bucket_name)
            qn.get_list()
            errors['base'] = 'fail'

            # validate success
            if errors.get('base', '') == '':
                return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)