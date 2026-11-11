"""七牛云存储封装。"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from logging import getLogger

import qiniu
from homeassistant.const import __version__ as current_version
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.json import load_json

LOGGER = getLogger(__package__)


class Qiniu:
    """七牛云 Kodo 封装，负责上传 / 删除 / 列举 / 下载备份对象。"""

    def __init__(self, hass, access_key: str, secret_key: str, bucket_name: str) -> None:
        self.hass = hass
        self.auth = qiniu.Auth(access_key, secret_key)
        self.bucket_name = bucket_name
        self.bucket = qiniu.BucketManager(self.auth)
        try:
            uuid = load_json(os.path.abspath(f"{STORAGE_DIR}/core.uuid"))["data"]["uuid"]
        except Exception:  # noqa: BLE001 - 文件不存在时使用占位符
            uuid = "unknown"
        # 统一前缀：HomeAssistant/<实例UUID>/<HA版本>/，便于多实例/多版本隔离
        self.prefix = f"HomeAssistant/{uuid}/{current_version}/"

    def validate(self) -> bool:
        """验证密钥与 bucket 是否可用（列举前缀下的对象）。"""
        try:
            _, _, info = self.bucket.list(self.bucket_name, self.prefix, None, 1, None)
            return info.status_code == 200
        except Exception:  # noqa: BLE001
            LOGGER.exception("七牛云校验失败")
            return False

    def _key(self, localfile: str) -> str:
        today = time.strftime("%y_%m_%d_", time.localtime())
        return self.prefix + today + os.path.basename(localfile)

    def key_for(self, name: str) -> str:
        """根据文件名构造对象 key（含日期前缀）。"""
        today = time.strftime("%y_%m_%d_", time.localtime())
        return self.prefix + today + name

    def upload(self, localfile: str) -> str:
        """上传本地文件，返回对象 key。"""
        key = self._key(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        ret, info = qiniu.put_file(token, key, localfile)
        if info.status_code != 200 or ret is None:
            raise RuntimeError(f"七牛云上传失败: {info}")
        LOGGER.info("已上传备份到七牛云: %s", key)
        return key

    def upload_data(self, key: str, data: bytes) -> str:
        """上传内存中的字节数据（用于备份元数据）。"""
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        ret, info = qiniu.put_data(token, key, data)
        if info.status_code != 200 or ret is None:
            raise RuntimeError(f"七牛云上传元数据失败: {info}")
        return key

    def delete(self, key: str) -> None:
        """删除指定对象。"""
        _, info = self.bucket.delete(self.bucket_name, key)
        if info.status_code != 200:
            raise RuntimeError(f"七牛云删除失败: {info}")

    def list_keys(self) -> list[str]:
        """列出 prefix 下的所有对象 key。"""
        keys: list[str] = []
        marker: str | None = None
        while True:
            ret, _, info = self.bucket.list(
                self.bucket_name, self.prefix, marker, 1000, None
            )
            if info.status_code != 200 or ret is None:
                LOGGER.warning("列举七牛云对象失败: %s", info)
                break
            for item in ret.get("items", []):
                keys.append(item["key"])
            marker = ret.get("marker")
            if not marker:
                break
        return keys

    def _private_url(self, key: str) -> str:
        base_url = f"https://{self.bucket_name}.qiniudn.com/{key}"
        return self.auth.private_download_url(base_url, expires=3600)

    def download(self, key: str, localfile: str) -> None:
        """下载对象到本地文件。"""
        urllib.request.urlretrieve(self._private_url(key), localfile)

    def download_data(self, key: str) -> bytes:
        """下载对象为字节数据（用于读取备份元数据）。"""
        with urllib.request.urlopen(self._private_url(key)) as resp:
            return resp.read()

    def upload_backup_with_meta(
        self, localfile: str, metadata: dict, key: str | None = None
    ) -> str:
        """上传备份文件并把 AgentBackup 元数据作为 <key>.meta 一并上传。"""
        key = key or self._key(localfile)
        token = self.auth.upload_token(self.bucket_name, key, 3600)
        ret, info = qiniu.put_file(token, key, localfile)
        if info.status_code != 200 or ret is None:
            raise RuntimeError(f"七牛云上传失败: {info}")
        LOGGER.info("已上传备份到七牛云: %s", key)
        self.upload_data(key + ".meta", json.dumps(metadata).encode("utf-8"))
        return key
