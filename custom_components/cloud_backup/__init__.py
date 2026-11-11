"""cloud_backup：将 Home Assistant 系统备份上传到七牛云。"""

from __future__ import annotations

from contextlib import suppress

import voluptuous as vol

from homeassistant.components.backup.const import DATA_MANAGER
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ACCESS_KEY,
    CONF_BUCKET_NAME,
    CONF_DELETE_LOCAL,
    CONF_SECRET_KEY,
    DATA_BACKUP_AGENT_LISTENERS,
    DOMAIN,
)
from .qiniu import Qiniu

# cloud_backup.create 服务：是否上传后删除本地备份
CREATE_SCHEMA = vol.Schema(
    {vol.Optional("delete"): cv.boolean}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置条目。"""
    # 确保监听列表存在，并通知 BackupManager 重新发现代理
    hass.data.setdefault(DATA_BACKUP_AGENT_LISTENERS, [])
    for listener in hass.data[DATA_BACKUP_AGENT_LISTENERS]:
        listener()

    if not hass.services.has_service(DOMAIN, "create"):
        hass.services.async_register(
            DOMAIN, "create", _async_create_service, schema=CREATE_SCHEMA
        )

    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置条目。"""
    for listener in hass.data.get(DATA_BACKUP_AGENT_LISTENERS, []):
        listener()
    if hass.services.has_service(DOMAIN, "create"):
        hass.services.async_remove(DOMAIN, "create")
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """配置更新后通知 BackupManager 刷新代理（删除本地等选项可能变化）。"""
    for listener in hass.data.get(DATA_BACKUP_AGENT_LISTENERS, []):
        listener()


async def _async_create_service(call) -> dict:
    """创建系统备份 → 上传到七牛云 → 按配置删除本地备份。

    流程：
    1. 通过 BackupManager 创建一个本地系统备份；
    2. 将生成的 .tar 文件上传到七牛云；
    3. 若服务参数 ``delete`` 或配置项 ``delete_local`` 为真，删除本地备份。
    """
    hass: HomeAssistant = call.hass
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("cloud_backup 未配置")
    entry = entries[0]
    data = {**entry.data, **entry.options}

    delete_local = call.data.get(
        "delete", data.get(CONF_DELETE_LOCAL, False)
    )

    manager = hass.data.get(DATA_MANAGER)
    if manager is None:
        raise HomeAssistantError("备份组件不可用")

    local_agent_id = next(iter(manager.local_backup_agents))
    # 仅创建本地备份，上传由本服务自行完成，避免依赖代理注册时机
    new_backup = await manager.async_create_backup(
        agent_ids=[local_agent_id],
        include_addons=None,
        include_all_addons=False,
        include_database=True,
        include_folders=None,
        include_homeassistant=True,
        name=None,
        password=None,
    )
    slug = new_backup.backup_job_id

    local_agent = manager.local_backup_agents[local_agent_id]
    local_path = local_agent.get_backup_path(slug)

    qn = Qiniu(
        hass,
        data[CONF_ACCESS_KEY],
        data[CONF_SECRET_KEY],
        data[CONF_BUCKET_NAME],
    )
    await hass.async_add_executor_job(qn.upload, str(local_path))

    if delete_local:
        await local_agent.async_delete_backup(slug)
        with suppress(Exception):
            manager.known_backups.discard(slug)

    return {"backup_id": slug, "uploaded": True, "delete_local": delete_local}
