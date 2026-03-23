"""Configuration management for Pararam Nexus MCP."""

from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Configuration for Pararam Nexus MCP server."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # Pararam.io credentials
    pararam_login: str = Field(..., description='Pararam.io login')
    pararam_password: str = Field(..., description='Pararam.io password')
    pararam_2fa_key: str | None = Field(None, description='Pararam.io 2FA key (optional)')

    # Cookie storage
    pararam_cookie_file: Path = Field(
        default=Path('.pararam_cookies.json'),
        description='Path to store authentication cookies',
    )

    # Channel settings (bot webhook)
    pararam_bot_secret: str | None = Field(None, description='Pararam.io bot secret key (full key including URL key)')
    pararam_channel_host: str = Field(default='127.0.0.1', description='Webhook listener host')
    pararam_channel_port: int = Field(default=8443, description='Webhook listener port')
    pararam_whitelisted_users: str = Field(
        default='',
        description='Whitelisted user unique_names for channel notifications (comma-separated)',
    )
    pararam_channel_pre_exec: str | None = Field(
        None,
        description='Shell command to run before starting the channel (e.g. rathole tunnel)',
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
    def whitelisted_users_list(self) -> list[str]:
        """Parse comma-separated whitelisted users string into list."""
        if not self.pararam_whitelisted_users:
            return []
        return [u.strip() for u in self.pararam_whitelisted_users.split(',') if u.strip()]

    def validate_credentials(self) -> None:
        """Validate that required credentials are provided."""
        if not self.pararam_login:
            raise ValueError('PARARAM_LOGIN environment variable is required')
        if not self.pararam_password:
            raise ValueError('PARARAM_PASSWORD environment variable is required')


# Global config instance
try:
    config = Config()
except ValidationError:
    # Config will fail if .env is missing or fields are invalid, which is expected during development
    # Will be validated at runtime in server.py
    config = Config(
        pararam_login='',
        pararam_password='',
        pararam_2fa_key=None,
    )
