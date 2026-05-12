"""Chat-related tools for Pararam.io."""

import logging

import httpx
from fastmcp import FastMCP
from pararamio_aio.exceptions import (
    PararamioAuthenticationError,
    PararamioHTTPRequestError,
    PararamioRequestError,
    PararamioValidationError,
)
from pararamio_aio.models import Chat

from pararam_nexus_mcp.client import get_client
from pararam_nexus_mcp.helpers import error_response, success_response
from pararam_nexus_mcp.models import (
    ChatInfo,
    CreateChatPayload,
    GetChatPayload,
    SearchChatsPayload,
    ToolResponse,
)

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

    @mcp.tool()
    async def get_chat(chat_id: int) -> ToolResponse[GetChatPayload | None]:
        """Fetch a single chat's metadata by ID.

        Args:
            chat_id: Numeric chat ID.

        Returns:
            ToolResponse with the chat title, type, member counts, and description.
        """
        try:
            client = await get_client()
            logger.info('Fetching chat %s', chat_id)
            chat = await client.client.get_chat_by_id(chat_id)
            if chat is None:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='not found',
                )
            await chat.load()
            info = ChatInfo(
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
            return success_response(
                message=f'Chat {chat_id}: {info.title}',
                payload=GetChatPayload(chat=info),
            )
        except (
            PararamioAuthenticationError,
            PararamioHTTPRequestError,
            PararamioRequestError,
            PararamioValidationError,
            httpx.HTTPError,
        ) as e:
            logger.error('Failed to fetch chat %s: %s', chat_id, e)
            return error_response(message=f'Could not fetch chat {chat_id}', error=str(e))
        except Exception as e:
            logger.error('Unexpected error fetching chat %s: %s', chat_id, e, exc_info=True)
            return error_response(message='Unexpected error', error=str(e))

    @mcp.tool()
    async def create_private_chat(user_id: int) -> ToolResponse[CreateChatPayload | None]:
        """Create a personal (PM) chat with another user.

        Args:
            user_id: Numeric ID of the user to start a PM with.

        Returns:
            ToolResponse with the new chat's ID.
        """
        try:
            client = await get_client()
            logger.info('Creating private chat with user %s', user_id)
            chat = await Chat.create_private_chat(client.client, user_id)
            return success_response(
                message=f'Private chat with user {user_id} created (id={chat.id})',
                payload=CreateChatPayload(chat_id=chat.id, title=None, type='pm'),
            )
        except (
            PararamioAuthenticationError,
            PararamioHTTPRequestError,
            PararamioRequestError,
            PararamioValidationError,
            httpx.HTTPError,
        ) as e:
            logger.error('Failed to create private chat: %s', e)
            return error_response(message='Could not create private chat', error=str(e))
        except Exception as e:
            logger.error('Unexpected error creating private chat: %s', e, exc_info=True)
            return error_response(message='Unexpected error', error=str(e))

    @mcp.tool()
    async def create_group_chat(
        title: str,
        description: str = '',
        users: list[int] | None = None,
        organization_id: int | None = None,
    ) -> ToolResponse[CreateChatPayload | None]:
        """Create a group chat with the given title and member set.

        Args:
            title: Group chat title (required).
            description: Optional chat description.
            users: List of user IDs to invite. Empty/None creates an empty chat.
            organization_id: Organization to scope the chat to (optional).

        Returns:
            ToolResponse with the new chat's ID and title.
        """
        try:
            client = await get_client()
            logger.info('Creating group chat %r with %d users', title, len(users or []))
            chat = await client.client.create_chat(
                title=title,
                description=description,
                users=list(users or []),
                organization_id=organization_id,
            )
            return success_response(
                message=f'Group chat {title!r} created (id={chat.id})',
                payload=CreateChatPayload(chat_id=chat.id, title=title, type='group'),
            )
        except (
            PararamioAuthenticationError,
            PararamioHTTPRequestError,
            PararamioRequestError,
            PararamioValidationError,
            httpx.HTTPError,
        ) as e:
            logger.error('Failed to create group chat %r: %s', title, e)
            return error_response(message=f'Could not create group chat {title!r}', error=str(e))
        except Exception as e:
            logger.error('Unexpected error creating group chat %r: %s', title, e, exc_info=True)
            return error_response(message='Unexpected error', error=str(e))

    @mcp.tool()
    async def create_thread_chat(
        parent_chat_id: int,
        post_no: int,
        title: str | None = None,
    ) -> ToolResponse[CreateChatPayload | None]:
        """Create a branch (thread) chat rooted at a specific post in another chat.

        Requires the parent chat to have allow_branch=True. Errors otherwise.

        Args:
            parent_chat_id: ID of the chat to branch from.
            post_no: Post number to root the branch at.
            title: Optional title for the branch chat.

        Returns:
            ToolResponse with the new branch chat's ID.
        """
        try:
            client = await get_client()
            logger.info(
                'Creating branch chat from chat=%s post_no=%s title=%r',
                parent_chat_id,
                post_no,
                title,
            )
            parent = await client.client.get_chat_by_id(parent_chat_id)
            if parent is None:
                return error_response(
                    message=f'Parent chat {parent_chat_id} not found',
                    error='not found',
                )
            branch = await parent.create_branch(post_no=post_no, title=title or '')
            # Branch wraps the new child Chat plus parent linkage; the actual
            # chat id is `branch.chat.id`.
            branch_chat_id = int(branch.chat.id)
            return success_response(
                message=f'Branch chat created (id={branch_chat_id})',
                payload=CreateChatPayload(chat_id=branch_chat_id, title=title, type='thread'),
            )
        except (
            PararamioAuthenticationError,
            PararamioHTTPRequestError,
            PararamioRequestError,
            PararamioValidationError,
            httpx.HTTPError,
        ) as e:
            logger.error('Failed to create branch chat from %s/%s: %s', parent_chat_id, post_no, e)
            return error_response(message='Could not create branch chat', error=str(e))
        except Exception as e:
            logger.error('Unexpected error creating branch chat: %s', e, exc_info=True)
            return error_response(message='Unexpected error', error=str(e))
