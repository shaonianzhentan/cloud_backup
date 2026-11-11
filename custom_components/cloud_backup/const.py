from collections.abc import Callable
from homeassistant.util.hass_dict import HassKey

from .manifest import manifest

DOMAIN = manifest.domain
PLATFORMS = []

DATA_BACKUP_AGENT_LISTENERS: HassKey[list[Callable[[], None]]] = HassKey(
    f"{DOMAIN}.backup_agent_listeners"
)

# 备份代理展示名称（agent_id = f"{DOMAIN}.{AGENT_NAME}"）
AGENT_NAME = "七牛云备份"

# 配置字段
CONF_ACCESS_KEY = "access_key"
CONF_SECRET_KEY = "secret_key"
CONF_BUCKET_NAME = "bucket_name"
CONF_DELETE_LOCAL = "delete_local"

DEFAULT_DELETE_LOCAL = False
