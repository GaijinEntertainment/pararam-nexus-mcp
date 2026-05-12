"""Configuration management for Pararam Nexus MCP."""

from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal['full', 'limited']


class Config(BaseSettings):
    """Configuration for Pararam Nexus MCP server.

    Two authentication modes are supported, selected at startup:

    - **full** (default) — login + password + optional 2FA. All MCP tools
      are registered.
    - **limited** — set ``PARARAM_USER_TOKEN`` to an X-UserToken service
      token. Only the chat/message/post tools listed in the README are
      registered; file ops and broad search are excluded.

    The two modes are mutually exclusive — providing both
    ``PARARAM_USER_TOKEN`` and ``PARARAM_LOGIN``/``PARARAM_PASSWORD`` is a
    configuration error.
    """

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # Pararam.io credentials — required in full mode, must be empty in limited mode.
    pararam_login: str | None = Field(None, description='Pararam.io login (full mode)')
    pararam_password: str | None = Field(None, description='Pararam.io password (full mode)')
    pararam_2fa_key: str | None = Field(None, description='Pararam.io 2FA key (full mode, optional)')

    # Pararam.io service token — selects limited mode when set.
    pararam_user_token: str | None = Field(
        None,
        description='Pararam.io X-UserToken service token (limited mode)',
    )

    # Cookie storage (full mode only)
    pararam_cookie_file: Path = Field(
        default=Path('.pararam_cookies.json'),
        description='Path to store authentication cookies (full mode only)',
    )

    # MCP server settings
    mcp_server_name: str = Field(default='pararam-nexus-mcp', description='MCP server name')
    mcp_server_instructions: str = Field(
        default=(
            'Pararam Nexus MCP Server - Provides access to pararam.io messaging platform. '
            'You can search messages, get chat history, send messages with replies and quotes, '
            'manage chats, upload and download files, and search users.'
        ),
        description='MCP server instructions',
    )

    @property
    def mode(self) -> Mode:
        """Return 'limited' if a service token is set, else 'full'."""
        return 'limited' if self.pararam_user_token else 'full'

    def validate_credentials(self) -> None:
        """Validate that exactly one auth mode is fully configured.

        Raises:
            ValueError: If both modes are configured, neither mode is
                configured, or full mode is missing login/password.
        """
        if self.pararam_user_token:
            if self.pararam_login or self.pararam_password:
                raise ValueError(
                    'PARARAM_USER_TOKEN is mutually exclusive with '
                    'PARARAM_LOGIN/PARARAM_PASSWORD. Unset one or the other.'
                )
            return  # limited mode is fully configured

        if not self.pararam_login:
            raise ValueError(
                'PARARAM_LOGIN environment variable is required (or set PARARAM_USER_TOKEN for limited mode)'
            )
        if not self.pararam_password:
            raise ValueError(
                'PARARAM_PASSWORD environment variable is required (or set PARARAM_USER_TOKEN for limited mode)'
            )


# Global config instance
try:
    config = Config()
except ValidationError:
    # Config will fail if .env is missing or fields are invalid, which is expected during development
    # Will be validated at runtime in server.py
    config = Config(
        pararam_login=None,
        pararam_password=None,
        pararam_2fa_key=None,
        pararam_user_token=None,
    )
