#!/usr/bin/env python3
"""
FastMCP-based Pararam Nexus MCP server implementation.
"""

import logging
import os
import sys

from fastmcp import FastMCP

from pararam_nexus_mcp.config import config
from pararam_nexus_mcp.tools.chats import register_chat_tools
from pararam_nexus_mcp.tools.posts import register_post_tools
from pararam_nexus_mcp.tools.users import register_user_tools

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name=config.mcp_server_name,
    instructions=config.mcp_server_instructions,
)


def main() -> None:
    """Main entry point for the Pararam Nexus MCP server."""
    try:
        # Validate configuration
        config.validate_credentials()

        # Register all tools
        register_post_tools(mcp)
        register_chat_tools(mcp)
        register_user_tools(mcp)

        # Set up logging
        log_level = logging.DEBUG if os.getenv('DEBUG') else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

        logger.info(f'Starting {config.mcp_server_name}')
        logger.info(
            'Registered tools: '
            'Posts: search_messages, get_chat_messages, send_message, '
            'build_conversation_thread, upload_file_to_chat, get_message_from_url, '
            'get_post_attachments, download_post_attachment | '
            'Chats: search_chats | '
            'Users: search_users, get_user_info, get_user_team_status'
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
