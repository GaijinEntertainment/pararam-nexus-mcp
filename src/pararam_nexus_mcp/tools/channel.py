"""Channel control tools for Claude Code notifications."""

import logging

from fastmcp import Context, FastMCP

from pararam_nexus_mcp.channel import channel_manager
from pararam_nexus_mcp.config import config
from pararam_nexus_mcp.helpers import error_response, success_response
from pararam_nexus_mcp.models import ToolResponse

logger = logging.getLogger(__name__)


def register_channel_tools(mcp: FastMCP[None]) -> None:
    """Register channel control tools with the MCP server."""

    @mcp.tool()
    async def activate_channel(ctx: Context) -> ToolResponse[dict[str, object] | None]:
        """
        Activate the pararam.io channel to receive real-time message notifications.

        Starts a webhook listener that receives messages from pararam.io bot
        and pushes them as channel notifications to Claude Code.
        Requires PARARAM_BOT_SECRET to be configured.

        Args:
            ctx: MCP context (provides session for sending notifications)

        Returns:
            ToolResponse with channel activation status including host, port, and whitelisted users
        """
        if channel_manager.is_active:
            return success_response(
                message='Channel is already active',
                payload={
                    'status': 'active',
                    'host': config.pararam_channel_host,
                    'port': config.pararam_channel_port,
                    'whitelisted_users': config.whitelisted_users_list,
                },
            )

        if not config.pararam_bot_secret:
            return error_response(
                message='Channel not configured',
                error='PARARAM_BOT_SECRET environment variable is required to activate the channel',
            )

        try:
            await channel_manager.start(ctx.session)
            return success_response(
                message=f'Channel activated on {config.pararam_channel_host}:{config.pararam_channel_port}',
                payload={
                    'status': 'active',
                    'host': config.pararam_channel_host,
                    'port': config.pararam_channel_port,
                    'whitelisted_users': config.whitelisted_users_list,
                },
            )
        except ValueError as e:
            return error_response(message='Configuration error', error=str(e))
        except RuntimeError as e:
            return error_response(message='Failed to start channel', error=str(e))
        except Exception as e:  # COMMENT: Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error activating channel: %s', e, exc_info=True)
            return error_response(message='Unexpected error', error=str(e))

    @mcp.tool()
    async def deactivate_channel() -> ToolResponse[dict[str, str] | None]:
        """
        Deactivate the pararam.io channel and stop receiving notifications.

        Stops the webhook listener and consumer task.

        Returns:
            ToolResponse with deactivation status
        """
        if not channel_manager.is_active:
            return success_response(
                message='Channel is not active',
                payload={'status': 'inactive'},
            )

        try:
            await channel_manager.stop()
            return success_response(
                message='Channel deactivated',
                payload={'status': 'inactive'},
            )
        except Exception as e:  # COMMENT: Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error deactivating channel: %s', e, exc_info=True)
            return error_response(message='Failed to deactivate channel', error=str(e))

    @mcp.tool()
    async def channel_status() -> ToolResponse[dict[str, object] | None]:
        """
        Get the current status of the pararam.io channel.

        Returns:
            ToolResponse with channel status including activity state, configuration,
            whitelisted users, and event statistics (received, forwarded, filtered counts)
        """
        stats = channel_manager.stats
        return success_response(
            message=f'Channel is {"active" if channel_manager.is_active else "inactive"}',
            payload={
                'active': channel_manager.is_active,
                'host': config.pararam_channel_host,
                'port': config.pararam_channel_port,
                'whitelisted_users': config.whitelisted_users_list,
                'bot_configured': config.pararam_bot_secret is not None,
                'pre_exec': config.pararam_channel_pre_exec,
                'events_received': stats.events_received,
                'events_forwarded': stats.events_forwarded,
                'events_filtered': stats.events_filtered,
            },
        )
