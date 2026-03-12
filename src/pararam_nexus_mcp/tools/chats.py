"""Chat-related tools for Pararam.io."""

import logging

import httpx
from fastmcp import FastMCP
from pararamio_aio._core import (
    PararamioAuthenticationError,
    PararamioHTTPRequestError,
    PararamioRequestError,
    PararamioValidationError,
)

from pararam_nexus_mcp.client import get_client
from pararam_nexus_mcp.helpers import error_response, success_response
from pararam_nexus_mcp.models import ChatInfo, SearchChatsPayload, ToolResponse

logger = logging.getLogger(__name__)


def register_chat_tools(mcp: FastMCP[None]) -> None:
    """Register chat-related tools with the MCP server."""

    @mcp.tool()
    async def search_chats(
        query: str,
        limit: int = 20,
    ) -> ToolResponse[SearchChatsPayload | None]:
        """
        Search for chats by name or description.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 20, applied client-side)

        Returns:
            ToolResponse with SearchChatsPayload containing chat list including chat ID, name, type, and member count
        """
        try:
            client = await get_client()

            logger.info(f'Searching chats with query: {query}')

            # Use search_chats (no limit parameter in API, we'll limit client-side)
            chats = await client.client.search_chats(query)

            if not chats:
                return success_response(
                    message=f'No chats found matching query: {query}',
                    payload=SearchChatsPayload(
                        query=query,
                        count=0,
                        chats=[],
                    ),
                )

            # Apply client-side limit
            chats = chats[:limit]

            # Format results
            formatted_chats = []
            for chat in chats:
                # Load chat data to access fields
                await chat.load()

                formatted_chats.append(
                    ChatInfo(
                        id=chat.id,
                        title=chat.title or 'Untitled',
                        type=chat.type or 'unknown',
                        members_count=len(chat.thread_users_all) if chat.thread_users_all else 0,
                        posts_count=chat.posts_count or 0,
                        last_read_post_no=chat.last_read_post_no or 0,
                        thread_users=chat.thread_users or [],
                        thread_admins=chat.thread_admins or [],
                        thread_guests=chat.thread_guests or [],
                        thread_groups=chat.thread_groups or [],
                        description=chat.description or '',
                    )
                )

            message_text = f"Found {len(formatted_chats)} chats matching '{query}'"

            return success_response(
                message=message_text,
                payload=SearchChatsPayload(
                    query=query,
                    count=len(formatted_chats),
                    chats=formatted_chats,
                ),
            )

        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while searching chats: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while searching chats: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while searching chats: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while searching chats: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while searching chats: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )
