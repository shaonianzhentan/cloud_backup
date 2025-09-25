from collections.abc import Callable
from homeassistant.util.hass_dict import HassKey

from .manifest import manifest

DOMAIN = manifest.domain
PLATFORMS = []

DATA_BACKUP_AGENT_LISTENERS: HassKey[list[Callable[[], None]]] = HassKey(
    f"{DOMAIN}.backup_agent_listeners"
)