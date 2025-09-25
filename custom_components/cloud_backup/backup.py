from collections.abc import AsyncIterator, Callable, Coroutine
from homeassistant.components.backup import BackupAgent, AgentBackup
from homeassistant.core import HomeAssistant, callback
from typing import Any

from logging import getLogger
from .const import DATA_BACKUP_AGENT_LISTENERS, DOMAIN

LOGGER = getLogger(__package__)

async def async_get_backup_agents(
    hass: HomeAssistant,
) -> list[BackupAgent]:
    """Return a list of backup agents."""
    if not hass.config_entries.async_loaded_entries(DOMAIN):
        LOGGER.debug("No config entry found or entry is not loaded")
        return []
    return [ExampleBackupAgent()]


@callback
def async_register_backup_agents_listener(
    hass: HomeAssistant,
    *,
    listener: Callable[[], None],
    **kwargs: Any,
) -> Callable[[], None]:
    """Register a listener to be called when agents are added or removed.

    :return: A function to unregister the listener.
    """
    hass.data.setdefault(DATA_BACKUP_AGENT_LISTENERS, []).append(listener)

    @callback
    def remove_listener() -> None:
        """Remove the listener."""
        hass.data[DATA_BACKUP_AGENT_LISTENERS].remove(listener)

    return remove_listener


async def async_pre_backup(hass: HomeAssistant) -> None:
    """Perform operations before a backup starts."""
    pass

async def async_post_backup(hass: HomeAssistant) -> None:
    """Perform operations after a backup finishes."""
    pass

class ExampleBackupAgent(BackupAgent):
    """Backup agent interface."""

    domain = DOMAIN
    name = "七牛云备份"
    unique_id = "qiniu_cloud_backup"

    async def async_download_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[bytes]:
        """Download a backup file.

        Raises BackupNotFound if the backup does not exist.

        :param backup_id: The ID of the backup that was returned in async_list_backups.
        :return: An async iterator that yields bytes.
        """

    async def async_upload_backup(
        self,
        *,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
        backup: AgentBackup,
        **kwargs: Any,
    ) -> None:
        """Upload a backup.

        :param open_stream: A function returning an async iterator that yields bytes.
        :param backup: Metadata about the backup that should be uploaded.
        """
        print(backup)

    async def async_delete_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete a backup file.

        Raises BackupNotFound if the backup does not exist.

        :param backup_id: The ID of the backup that was returned in async_list_backups.
        """

    async def async_list_backups(self, **kwargs: Any) -> list[AgentBackup]:
        """List backups."""

    async def async_get_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> AgentBackup:
        """Return a backup.

        Raises BackupNotFound if the backup does not exist.
        """