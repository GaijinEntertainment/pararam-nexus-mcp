#!/usr/bin/env python3
"""
FastMCP-based Pararam Nexus MCP server implementation.
"""

import asyncio
import logging
import os
import sys

from fastmcp import FastMCP

from pararam_nexus_mcp.config import config
from pararam_nexus_mcp.formatting import PARARAM_FORMATTING_GUIDE, PARARAM_FORMATTING_REFERENCE
from pararam_nexus_mcp.tools.chats import register_chat_tools
from pararam_nexus_mcp.tools.posts import register_post_tools
from pararam_nexus_mcp.tools.users import register_user_tools

logger = logging.getLogger(__name__)

# Tool names available in limited (X-UserToken) mode. Everything else is
# stripped after registration. See README "Modes" section for rationale.
LIMITED_MODE_TOOLS: frozenset[str] = frozenset(
    {
        # Chat operations
        'get_chat',
        'create_private_chat',
        'create_group_chat',
        'create_thread_chat',
        # Post operations
        'get_chat_messages',
        'get_message_from_url',
        'get_reply_thread',
        'get_replies_to_post',
        'send_message',
        'edit_post',
        'delete_post',
    }
)

# Initialize FastMCP server
mcp = FastMCP(
    name=config.mcp_server_name,
    instructions=f'{config.mcp_server_instructions}\n\n{PARARAM_FORMATTING_GUIDE}',
)


@mcp.resource(
    'pararam://formatting',
    name='pararam_message_formatting',
    title='Pararam Message Formatting',
    description='Full Pararam message formatting reference for composing send_message and edit_post text.',
    mime_type='text/markdown',
)
def pararam_message_formatting() -> str:
    """Return the full Pararam message formatting reference."""
    return PARARAM_FORMATTING_REFERENCE


async def _prune_to_limited_tools(server: FastMCP[None]) -> list[str]:
    """In limited mode, drop every registered tool not in the allow-list.

    Returns the sorted list of tool names that remain registered.
    """
    tools = await server.list_tools()
    for tool in tools:
        if tool.name not in LIMITED_MODE_TOOLS:
            server.local_provider.remove_tool(tool.name)
    remaining = await server.list_tools()
    return sorted(t.name for t in remaining)


def main() -> None:
    """Main entry point for the Pararam Nexus MCP server."""
    try:
        # Validate configuration
        config.validate_credentials()

        # Set up logging (do this before the first logger.info call below)
        log_level = logging.DEBUG if os.getenv('DEBUG') else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

        # Register tools. User tools are full-mode-only — they aren't part of
        # the limited-mode spec, so skip the registration entirely to avoid
        # building Python objects we'll just discard.
        register_post_tools(mcp)
        register_chat_tools(mcp)
        if config.mode == 'full':
            register_user_tools(mcp)

        # In limited mode, prune to the allow-list. The prune runs once at
        # startup on a throwaway event loop; mcp.run() spins its own.
        if config.mode == 'limited':
            remaining = asyncio.run(_prune_to_limited_tools(mcp))
            logger.info(
                'Starting %s (limited mode, %d tools): %s',
                config.mcp_server_name,
                len(remaining),
                ', '.join(remaining),
            )
        else:
            logger.info(
                'Starting %s (full mode): '
                'Posts: search_messages, get_chat_messages, send_message, '
                'build_conversation_thread, upload_file_to_chat, get_message_from_url, '
                'get_post_attachments, download_post_attachment | '
                'Chats: search_chats | '
                'Users: search_users, get_user_info, get_user_team_status',
                config.mcp_server_name,
            )

        # Run the server - this blocks until interrupted
        mcp.run()

        sys.exit(0)
    except KeyboardInterrupt:
        # Clean exit on Ctrl-C without showing traceback
        print('\nShutting down...', file=sys.stderr)
        sys.exit(0)
    except ValueError as e:
        # Configuration errors - show user-friendly message
        print(f'\n❌ Configuration Error:\n{e!s}', file=sys.stderr)
        print('\n💡 Tip: Check your .env file and ensure all required credentials are set.', file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # COMMENT: Top-level handler to prevent silent crashes and ensure proper error logging
        if os.getenv('DEBUG'):
            # Show full traceback in debug mode
            raise
        # Show only the error message in production
        print(f'\n❌ Error starting server: {e!s}', file=sys.stderr)
        print('\n💡 Tip: Set DEBUG=true for detailed error information.', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
