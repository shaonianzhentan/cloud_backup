"""七牛云备份代理（Home Assistant 2025.1+ BackupAgent 接口）。"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from homeassistant.components.backup import (
    AgentBackup,
    BackupAgent,
    BackupAgentError,
)
from homeassistant.components.backup.const import DATA_MANAGER
from homeassistant.core import HomeAssistant, callback

from .const import (
    AGENT_NAME,
    CONF_ACCESS_KEY,
    CONF_BUCKET_NAME,
    CONF_DELETE_LOCAL,
    CONF_SECRET_KEY,
    DATA_BACKUP_AGENT_LISTENERS,
    DOMAIN,
)
from .qiniu import Qiniu

LOGGER = getLogger(__package__)

# chunk 大小，用于流式读写
_CHUNK_SIZE = 1024 * 1024


async def async_get_backup_agents(hass: HomeAssistant) -> list[BackupAgent]:
    """返回七牛云备份代理（仅在配置条目已加载时）。"""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        LOGGER.debug("未加载 %s 的配置条目", DOMAIN)
        return []
    entry = entries[0]
    data = {**entry.data, **entry.options}
    return [QiniuBackupAgent(hass, data)]


@callback
def async_register_backup_agents_listener(
    hass: HomeAssistant,
    *,
    listener: Callable[[], None],
    **kwargs: Any,
) -> Callable[[], None]:
    """注册监听：当代理增删时通知 BackupManager 刷新。"""
    hass.data.setdefault(DATA_BACKUP_AGENT_LISTENERS, []).append(listener)

    @callback
    def remove_listener() -> None:
        """移除监听。"""
        hass.data[DATA_BACKUP_AGENT_LISTENERS].remove(listener)

    return remove_listener


class QiniuBackupAgent(BackupAgent):
    """七牛云备份代理。"""

    domain = DOMAIN
    name = AGENT_NAME

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        """初始化代理。"""
        super().__init__()
        self._hass = hass
        self._qiniu = Qiniu(
            hass,
            data[CONF_ACCESS_KEY],
            data[CONF_SECRET_KEY],
            data[CONF_BUCKET_NAME],
        )
        self._delete_local = bool(data.get(CONF_DELETE_LOCAL, False))

    async def async_upload_backup(
        self,
        *,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
        backup: AgentBackup,
        **kwargs: Any,
    ) -> None:
        """将备份流上传到七牛云。

        流程：先把流写入临时文件，再上传；上传成功后若配置了
        ``delete_local``，则删除本地备份（仅删本地，云端保留）。
        """
        with NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            stream = await open_stream()
            async for chunk in stream:
                tmp.write(chunk)

        try:
            key = self._qiniu.key_for(backup.backup_id + ".tar")
            await self._hass.async_add_executor_job(
                self._qiniu.upload_backup_with_meta,
                str(tmp_path),
                backup.as_dict(),
                key,
            )
        finally:
            with suppress(OSError):
                tmp_path.unlink()

        if self._delete_local:
            # 上传完成后异步删除本地副本，避免阻塞上传回调
            self._hass.async_create_task(self._delete_local_backup(backup.backup_id))

    async def _delete_local_backup(self, backup_id: str) -> None:
        """仅删除本地备份文件，保留云端副本。"""
        try:
            manager = self._hass.data[DATA_MANAGER]
            local_id = next(iter(manager.local_backup_agents))
            await manager.local_backup_agents[local_id].async_delete_backup(backup_id)
            with suppress(Exception):
                # 同步 BackupManager 的已知备份集合，避免 UI 残留
                manager.known_backups.discard(backup_id)
        except Exception as err:  # noqa: BLE001
            LOGGER.warning("删除本地备份失败 (%s): %s", backup_id, err)

    async def async_delete_backup(self, backup_id: str, **kwargs: Any) -> None:
        """从七牛云删除备份（同时删除元数据对象）。"""

        def _delete() -> None:
            self._qiniu.delete(backup_id)
            with suppress(Exception):
                self._qiniu.delete(backup_id + ".meta")

        await self._hass.async_add_executor_job(_delete)

    async def async_list_backups(self, **kwargs: Any) -> list[AgentBackup]:
        """列举七牛云上的备份。"""
        keys = await self._hass.async_add_executor_job(self._qiniu.list_keys)
        backups: list[AgentBackup] = []
        for key in keys:
            if key.endswith(".meta"):
                continue
            backups.append(await self._build_backup(key))
        return backups

    async def async_get_backup(
        self, backup_id: str, **kwargs: Any
    ) -> AgentBackup | None:
        """根据 key 返回单个备份。"""
        backups = await self.async_list_backups()
        for backup in backups:
            if backup.backup_id == backup_id:
                return backup
        return None

    async def _build_backup(self, key: str) -> AgentBackup:
        """由元数据对象构造 AgentBackup，缺失时回退为最小信息。"""
        try:
            raw = await self._hass.async_add_executor_job(
                self._qiniu.download_data, key + ".meta"
            )
            return AgentBackup.from_dict(json.loads(raw.decode("utf-8")))
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("读取备份元数据失败，使用占位信息: %s", err)
            return AgentBackup(
                addons=[],
                backup_id=key,
                date="unknown",
                database_included=False,
                extra_metadata={},
                folders=[],
                homeassistant_included=True,
                homeassistant_version=None,
                name=os.path.basename(key),
                protected=False,
                size=0,
            )

    async def async_download_backup(
        self, backup_id: str, **kwargs: Any
    ) -> AsyncIterator[bytes]:
        """从七牛云下载备份并以字节流返回。"""
        with NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            await self._hass.async_add_executor_job(
                self._qiniu.download, backup_id, str(tmp_path)
            )
            with open(tmp_path, "rb") as fh:
                while True:
                    chunk = await self._hass.async_add_executor_job(
                        fh.read, _CHUNK_SIZE
                    )
                    if not chunk:
                        break
                    yield chunk
        finally:
            with suppress(OSError):
                tmp_path.unlink()
