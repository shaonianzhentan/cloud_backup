from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import PLATFORMS
from .manifest import manifest
from .qiniu import Qiniu

DOMAIN = manifest.domain
NAME = manifest.name
CONFIG_SCHEMA = cv.deprecated(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    access_key = data.get('access_key')
    secret_key = data.get('secret_key')
    bucket_name = data.get('bucket_name')
    qiniu = Qiniu(hass, access_key, secret_key, bucket_name)

    async def async_handle_service(call):
        backup_manager = hass.data['backup']
        if backup_manager.backing_up == False:
            backup = await backup_manager.generate_backup()
            # print(backup.path)
            key = await hass.async_add_executor_job(qiniu.upload, backup.path)
            # print(key)
            hass.loop.create_task(hass.services.async_call('persistent_notification', 'create', {
                'title': '文件上传成功',
                'message': f'路径：<a href="https://portal.qiniu.com/kodo/bucket/resource-v2?bucketName={qiniu.bucket_name}" target="_blank">{key}</a>',
                'notification_id': 'cloud_backup'
            }))
            # 删除本地备份文件
            if call.data.get('delete', False) == True:
                hass.loop.create_task(backup_manager.remove_backup(backup.slug))

    hass.services.async_register(DOMAIN, "create", async_handle_service)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)