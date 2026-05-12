"""Pararam.io client wrapper with authentication and cookie management."""

import contextlib
import logging
from typing import Any

from pararamio_aio import AsyncFileCookieManager, AsyncPararamio, PararamioException

from pararam_nexus_mcp.auth import get_2fa_key
from pararam_nexus_mcp.config import config

logger = logging.getLogger(__name__)


class PararamClient:
    """Wrapper for AsyncPararamio with cookie storage and session management. Singleton."""

    _instance: PararamClient | None = None

    def __new__(cls) -> PararamClient:
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the Pararam client."""
        if self._initialized:
            return
        self._client: AsyncPararamio | None = None
        # Cookie manager is only used in full mode; limited (token) mode never
        # persists session data.
        self._cookie_manager: AsyncFileCookieManager | None = (
            None
            if config.mode == 'limited'
            else AsyncFileCookieManager(str(config.pararam_cookie_file))
        )
        self._initialized: bool = True

    async def __aenter__(self) -> PararamClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect and authenticate to pararam.io."""
        if self._client is not None:
            return

        logger.info('Connecting to pararam.io (%s mode)', config.mode)

        if config.mode == 'limited':
            # Token mode: AsyncPararamio sets the X-UserToken header itself and
            # never needs cookies, login, or 2FA.
            client_context = AsyncPararamio(user_token=config.pararam_user_token)
        else:
            tfa_key = get_2fa_key(config.pararam_2fa_key)
            client_context = AsyncPararamio(
                login=config.pararam_login,
                password=config.pararam_password,
                key=tfa_key,
                cookie_manager=self._cookie_manager,
            )

        # Enter async context manager to initialize session. In full mode
        # AsyncPararamio loads cookies from cookie_manager and authenticates
        # only if needed; in limited mode it just opens the httpx session.
        try:
            self._client = await client_context.__aenter__()
            logger.info('Successfully connected to pararam.io')
        except PararamioException as e:
            logger.error('Connection failed: %s', e)
            raise RuntimeError(f'Failed to connect to pararam.io: {e!s}') from e

    async def disconnect(self) -> None:
        """Disconnect from pararam.io."""
        if self._client is not None:
            logger.info('Disconnecting from pararam.io')
            with contextlib.suppress(Exception):
                await self._client.__aexit__(None, None, None)
            self._client = None

    @property
    def client(self) -> AsyncPararamio:
        """Get the underlying AsyncPararamio client."""
        if self._client is None:
            raise RuntimeError('Client not connected. Call connect() first.')
        return self._client


async def get_client() -> PararamClient:
    """Get or create singleton client instance."""
    client = PararamClient()

    # Connect if not already connected
    if client._client is None:
        await client.connect()

    return client
