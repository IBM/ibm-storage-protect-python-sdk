from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ibm_storage_protect.session import ClientSession


class BaseClient:
    """Base client for IBM Storage Protect SDK client implementations."""

    def __init__(self, session: 'ClientSession'):
        if not session.is_active:
            raise ValueError("Session must be active")
        self.__session = session

    @property
    def _session(self) -> 'ClientSession':
        """Get the current session instance."""
        return self.__session

    @_session.setter
    def _session(self, value: 'ClientSession'):
        """Set the session instance."""
        self.__session = value

    def _require_handle(self) -> int:
        handle = self._session.handle
        if handle is None:
            raise ValueError("Session handle is not available")
        return handle

