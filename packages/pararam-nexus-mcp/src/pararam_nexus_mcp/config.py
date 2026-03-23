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
