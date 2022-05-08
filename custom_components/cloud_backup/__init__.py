import _thread
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import PLATFORMS
from .manifest import manifest
from .qiniu import Qiniu

BACKUP_DOMAIN = 'backup'
DOMAIN = manifest.domain
NAME = manifest.name
CONFIG_SCHEMA = cv.deprecated(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    access_key = data.get('access_key')
    secret_key = data.get('secret_key')
    bucket_name = data.get('bucket_name')
    qiniu = Qiniu(access_key, secret_key, bucket_name)
    
    async def async_handle_create_service(call) -> None:
        """Service handler for creating backups."""
        backup_manager = hass.data[BACKUP_DOMAIN]
        backup = await backup_manager.generate_backup()
        _thread.start_new_thread(qiniu.upload, (backup.path, hass))

    hass.services.async_register(DOMAIN, "create", async_handle_create_service)
    
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)