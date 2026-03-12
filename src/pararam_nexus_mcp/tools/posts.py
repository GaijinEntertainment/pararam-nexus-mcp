"""Post-related tools for Pararam.io."""

import base64
import logging
import re
import tempfile
from pathlib import Path

import httpx
from fastmcp import FastMCP
from mcp.types import ImageContent
from pararamio_aio._core import (
    PararamioAuthenticationError,
    PararamioHTTPRequestError,
    PararamioRequestError,
    PararamioValidationError,
)

from pararam_nexus_mcp.client import get_client
from pararam_nexus_mcp.helpers import error_response, success_response
from pararam_nexus_mcp.models import (
    BuildConversationThreadPayload,
    ChatMessageInfo,
    DownloadAttachmentErrorResponse,
    DownloadAttachmentResponse,
    FileInfo,
    GetChatMessagesPayload,
    GetMessageFromUrlPayload,
    GetPostAttachmentsPayload,
    PostInfo,
    SearchMessagesPayload,
    SendMessagePayload,
    ToolResponse,
    UploadFilePayload,
)

logger = logging.getLogger(__name__)


def get_post_type(post) -> str:  # type: ignore[no-untyped-def]
    """Get post type from post attributes.

    Args:
        post: Post object from pararamio_aio

    Returns:
        Post type: "file", "event", or "post"
    """
    if post.is_event:
        return 'event'
    if post.is_file:
        return 'file'
    return 'post'


def extract_file_from_post(post) -> FileInfo | None:  # type: ignore[no-untyped-def]
    """Extract primary file attachment from post metadata.

    Args:
        post: Post object from pararamio_aio

    Returns:
        AttachmentInfo if post has a file, None otherwise
    """
    if not post.is_file or not post.meta:
        return None

    # Check for single file in meta['file']
    if 'file' in post.meta:
        file_data = post.meta.get('file')
        if isinstance(file_data, dict):
            return FileInfo(
                guid=str(file_data.get('guid', '')),
                name=str(file_data.get('name', '')),
                size=int(file_data.get('size', 0)),
                url=str(file_data.get('url')) if file_data.get('url') else None,
                mime_type=str(file_data.get('mime_type', '')),
            )

    return None


async def extract_attachments_from_post(post, chat=None) -> tuple[bool, list[FileInfo]]:  # type: ignore[no-untyped-def]
    """Extract attachments from post metadata.

    Args:
        post: Post object from pararamio_aio
        chat: Optional Chat object to load attachment posts by UUID

    Returns:
        Tuple of (has_attachments, attachments_list)
    """
    attachments_list: list[FileInfo] = []
    has_attachments = False

    if post.is_file and post.meta:
        # Check for single file in meta['file']
        if 'file' in post.meta:
            file_data = post.meta.get('file')
            if isinstance(file_data, dict):
                has_attachments = True
                attachments_list.append(
                    FileInfo(
                        guid=str(file_data.get('guid', '')),
                        name=str(file_data.get('name', '')),
                        size=int(file_data.get('size', 0)),
                        url=str(file_data.get('url')) if file_data.get('url') else None,
                        mime_type=str(file_data.get('mime_type', '')),
                    )
                )

        # Check for attachments in meta['attachments']
        # Note: This may contain only UUID strings or full file objects (dicts)
        # UUID strings correspond to other posts that contain the actual file
        if 'attachments' in post.meta:
            attachments_raw = post.meta.get('attachments')
            if isinstance(attachments_raw, list) and len(attachments_raw) > 0:
                has_attachments = True
                # Try to extract full metadata if available (dict objects)
                for attachment_item in attachments_raw:
                    if isinstance(attachment_item, dict):
                        # Full metadata available
                        attachments_list.append(
                            FileInfo(
                                guid=str(attachment_item.get('guid', '')),
                                name=str(attachment_item.get('name', '')),
                                size=int(attachment_item.get('size', 0)),
                                url=str(attachment_item.get('url')) if attachment_item.get('url') else None,
                                mime_type=str(attachment_item.get('mime_type', '')),
                            )
                        )
                    elif isinstance(attachment_item, str) and chat:
                        # Only UUID available - need to load the attachment post
                        # The UUID corresponds to post.uuid of another post
                        try:
                            # Try to find and load the post by UUID
                            attachment_post = await chat.get_post_by_uuid(attachment_item)
                            if attachment_post:
                                await attachment_post.load()
                                # Extract file info from the attachment post
                                if attachment_post.is_file and attachment_post.meta and 'file' in attachment_post.meta:
                                    file_data = attachment_post.meta.get('file')
                                    if isinstance(file_data, dict):
                                        attachments_list.append(
                                            FileInfo(
                                                guid=str(file_data.get('guid', '')),
                                                name=str(file_data.get('name', '')),
                                                size=int(file_data.get('size', 0)),
                                                url=str(file_data.get('url')) if file_data.get('url') else None,
                                                mime_type=str(file_data.get('mime_type', '')),
                                            )
                                        )
                        except Exception as e:
                            # If we can't load the attachment post, create minimal AttachmentInfo
                            logger.warning(f'Failed to load attachment post {attachment_item}: {e}')
                            attachments_list.append(
                                FileInfo(
                                    guid=attachment_item,
                                    name='',
                                    size=0,
                                    url=None,
                                    mime_type='',
                                )
                            )
                    elif isinstance(attachment_item, str):
                        # Only UUID available but no chat provided - create minimal AttachmentInfo
                        attachments_list.append(
                            FileInfo(
                                guid=attachment_item,
                                name='',
                                size=0,
                                url=None,
                                mime_type='',
                            )
                        )

    return has_attachments, attachments_list


def register_post_tools(mcp: FastMCP[None]) -> None:
    """Register post-related tools with the MCP server."""

    @mcp.tool()
    async def search_messages(
        query: str,
        limit: int = 20,
        chat_ids: list[int] | None = None,
    ) -> ToolResponse[SearchMessagesPayload | None]:
        """
        Search for messages across all chats or in specific chats.

        Args:
            query: Search query string. Supports search filters (see below)
            limit: Maximum number of results to return (default: 20)
            chat_ids: Optional list of chat IDs to search within. If None, search in all chats.

        Search Syntax:
            Boolean Operators:
                By default, all terms are optional (OR), as long as one term matches.
                Search for "foo bar baz" finds any document containing foo OR bar OR baz.

                + (must be present) - Example: +fox (fox must be found)
                - (must not be present) - Example: -news (news must be excluded)
                Example: "quick brown +fox -news" (fox required, news excluded, quick/brown optional)

                AND, OR, NOT (also &&, ||, !) - Standard boolean operators
                NOTE: NOT takes precedence over AND, which takes precedence over OR
                Example: "(quick OR brown) AND fox"

            Grouping:
                Use parentheses to group terms: "(quick OR brown) AND fox"

            Wildcards:
                ? - Replace single character: "qu?ck"
                * - Replace zero or more characters: "bro*"

            Strict Search:
                Use quotes for exact phrase match: "some search phrase"

            Fuzziness:
                Use ~ for similar terms (Damerau-Levenshtein distance, max 2 changes):
                "quikc~ brwn~ foks~" or "quikc~1" (edit distance of 1)

            Proximity Search:
                Use ~N after phrase to allow words to be N positions apart:
                "fox quick"~5 (allows up to 5 words distance, any order)

        Search Filters:
            Format: search text /filter1 param1 param2 /filter2 param

            /users or /from - Find posts by specific users
                Example: /users @user1 @user2 or /from @user1 @user2

            /replyto or /reply - Find messages that are replies to specified users
                Example: /replyto @user1 @user2 or /reply @user1 @user2

            /to - Find messages that mention users OR are replies to them
                Example: /to @user1 @user2

            /file - Find files by name pattern
                Example: /file *filen?me*

            /from_date or /after - Find posts created after a date (YYYY-MM-DD, YYYY-MM, or YYYY)
                Example: /from_date 2016-01-22 or /after 2016-01 or /after 2016

            /to_date or /before - Find posts created before a date (YYYY-MM-DD, YYYY-MM, or YYYY)
                Example: /to_date 2016-01-22 or /before 2016-01 or /before 2016

            /tags - Find posts containing specific tags (strict match)
                Example: /tags hey may day or /tags #hey #may #day or #hey #may #day

            /has - Find posts based on content type:
                /has tag - Posts containing tags (e.g., #may)
                /has link - Posts containing URLs or markdown links
                /has email - Posts containing email addresses
                /has mention - Posts mentioning any user or user with role
                /has user - Posts containing user mentions or words starting with @
                /has group - Posts containing role mentions
                /has reply - Posts that are replies
                /has file - Posts with attached files
                /has block - Posts with text in blocks (>text or ```text)
                /has poll - Posts containing polls

        Returns:
            ToolResponse with SearchMessagesPayload containing search results with message text,
            sender, chat info, and timestamp
        """
        try:
            client = await get_client()

            logger.info(f'Searching messages with query: {query}, limit: {limit}, chat_ids: {chat_ids}')

            total_count, posts_iter = await client.client.search_posts(query, limit=limit, chat_ids=chat_ids)

            formatted_results = []
            loaded_chats: set[int] = set()
            async for post in posts_iter:
                await post.load()

                # Load chat data once per chat to get title
                if post.chat.id not in loaded_chats:
                    await post.chat.load()
                    loaded_chats.add(post.chat.id)

                post_type = get_post_type(post)
                if post_type == 'event':
                    continue

                user_name = 'Unknown'
                user_id = post.user_id if post.user_id else None
                if post.meta and 'user' in post.meta:
                    user_name = post.meta['user'].get('name', 'Unknown')

                file_info = extract_file_from_post(post)

                formatted_results.append(
                    ChatMessageInfo(
                        post_no=post.post_no,
                        text=post.text or '',
                        user_name=user_name,
                        user_id=user_id,
                        chat_id=post.chat.id,
                        chat_name=post.chat.title or 'Unknown',
                        time_created=str(post.time_created),
                        reply_no=post.reply_no,
                        type=post_type,
                        file=file_info,
                    )
                )

            result_message = (
                f'Found {total_count} messages matching "{query}", returning {len(formatted_results)} results'
            )
            return success_response(
                message=result_message,
                payload=SearchMessagesPayload(
                    query=query,
                    total_count=total_count,
                    returned_count=len(formatted_results),
                    messages=formatted_results,
                ),
            )

        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while searching messages: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while searching messages: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while searching messages: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while searching messages: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while searching messages: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def get_chat_messages(
        chat_id: str,
        limit: int = 50,
        before_message_id: str | None = None,
    ) -> ToolResponse[GetChatMessagesPayload | None]:
        """
        Get messages from a specific chat.

        Args:
            chat_id: ID of the chat to get messages from
            limit: Maximum number of messages to return (default: 50)
            before_message_id: Get messages before this message ID (for pagination).
                If provided, returns messages older than this ID.

        Returns:
            ToolResponse with GetChatMessagesPayload containing chat messages including sender, text, and timestamp
        """
        try:
            client = await get_client()

            logger.info(
                f'Getting messages from chat {chat_id}, limit: {limit}, before_message_id: {before_message_id}'
            )

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))
            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            # Load posts: if before_message_id is set, load range ending before it
            if before_message_id:
                end_no = int(before_message_id) - 1
                start_no = max(end_no - limit + 1, 1)
                messages = await chat.load_posts(start_post_no=start_no, end_post_no=end_no)
            else:
                # Get last 'limit' messages
                messages = await chat.load_posts(start_post_no=-limit, end_post_no=-1)

            if not messages:
                return error_response(
                    message=f'No messages found in chat {chat_id}',
                    error='No messages found',
                )

            # Format messages
            formatted_messages = []
            for post in messages:
                # Load full post data if not already loaded
                if not post.is_loaded:
                    await post.load()

                # Get post type
                post_type = get_post_type(post)

                user_name = 'Unknown'
                user_id = post.user_id if post.user_id else None
                if post.meta and 'user' in post.meta:
                    user_name = post.meta['user'].get('name', 'Unknown')

                # Extract primary file info
                file_info = extract_file_from_post(post)

                formatted_messages.append(
                    PostInfo(
                        post_no=post.post_no,
                        text=post.text or '',
                        user_name=user_name,
                        user_id=user_id,
                        time_created=str(post.time_created),
                        reply_no=post.reply_no,
                        type=post_type,
                        file=file_info,
                    )
                )

            chat_name = chat.title or 'Unknown'
            message_text = f"Retrieved {len(formatted_messages)} messages from chat '{chat_name}' (ID: {chat_id})"

            return success_response(
                message=message_text,
                payload=GetChatMessagesPayload(
                    chat_id=chat_id,
                    count=len(formatted_messages),
                    messages=formatted_messages,
                ),
            )

        except ValueError as e:
            logger.error('Invalid chat_id: %s', e)
            return error_response(
                message='Invalid chat ID',
                error=f'Invalid chat_id: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while getting chat messages: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while getting chat messages: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while getting chat messages: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while getting chat messages: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while getting chat messages: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def send_message(
        chat_id: str,
        text: str,
        reply_to_message_id: str | None = None,
        quote_text: str | None = None,
    ) -> ToolResponse[SendMessagePayload | None]:
        """
        Send a message to a chat.

        Args:
            chat_id: ID of the chat to send message to
            text: Message text to send
            reply_to_message_id: Post number to reply to (optional)
            quote_text: Text to quote from the replied message (optional, only used with reply_to_message_id)

        Returns:
            ToolResponse with SendMessagePayload containing sent message details including message ID and timestamp
        """
        try:
            client = await get_client()

            logger.info(f'Sending message to chat {chat_id}')

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))
            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            # Send message using Chat.send_message
            reply_no = int(reply_to_message_id) if reply_to_message_id else None
            sent_post = await chat.send_message(text, reply_to_post_no=reply_no, quote_text=quote_text)

            chat_name = chat.title or 'Unknown'
            message_text = f"Message sent successfully to chat '{chat_name}' (post #{sent_post.post_no})"

            return success_response(
                message=message_text,
                payload=SendMessagePayload(
                    post_no=sent_post.post_no,
                    chat_id=chat_id,
                    text=text,
                    time_created=str(sent_post.time_created),
                ),
            )

        except ValueError as e:
            logger.error('Invalid chat_id or reply_to_message_id: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while sending message: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while sending message: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while sending message: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while sending message: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while sending message: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def build_conversation_thread(
        chat_id: str,
        root_message_id: str,
        limit: int = 100,
    ) -> ToolResponse[BuildConversationThreadPayload | None]:
        """
        Build a conversation thread starting from a root message.

        Returns all messages that are replies to the root message or replies to those replies, recursively.

        Args:
            chat_id: ID of the chat
            root_message_id: Post number to use as root of the conversation
            limit: Maximum number of recent messages to load and search (default: 100)

        Returns:
            ToolResponse with BuildConversationThreadPayload containing flat list of all posts
            in the thread, sorted by post_no. Each post contains reply_to_post_no to
            reconstruct the tree structure.
        """
        try:
            client = await get_client()

            logger.info(f'Building conversation thread for chat {chat_id}, root message {root_message_id}')

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))
            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            root_post_no = int(root_message_id)

            # Load recent messages using lazy async iterator
            posts_map = {}
            messages_loaded = 0

            async for post in chat._lazy_posts_loader(start_post_no=-limit, end_post_no=-1):
                # Load full post data if not already loaded
                if not post.is_loaded:
                    await post.load()

                posts_map[post.post_no] = post
                messages_loaded += 1

            if not posts_map:
                return error_response(
                    message=f'No messages found in chat {chat_id}',
                    error='No messages found',
                )

            # Check if root message exists
            if root_post_no not in posts_map:
                return error_response(
                    message=f'Root message {root_message_id} not found in recent {limit} messages',
                    error='Root message not found',
                )

            # Find all posts that belong to this thread
            thread_posts = []

            def collect_thread_posts(post_no: int) -> None:
                """Recursively collect all posts in the thread."""
                if post_no not in posts_map:
                    return

                post = posts_map[post_no]
                thread_posts.append(post)

                # Find all replies to this post
                for candidate_no, candidate_post in posts_map.items():
                    if candidate_post.reply_no == post_no and candidate_post not in thread_posts:
                        collect_thread_posts(candidate_no)

            # Start collecting from root
            collect_thread_posts(root_post_no)

            # Sort by post_no
            thread_posts.sort(key=lambda p: p.post_no)

            # Format as Pydantic models
            formatted_posts = []
            for post in thread_posts:
                # Get post type
                post_type = get_post_type(post)

                user_name = 'Unknown'
                user_id = post.user_id if post.user_id else None
                if post.meta and 'user' in post.meta:
                    user_name = post.meta['user'].get('name', 'Unknown')

                # Extract primary file info
                file_info = extract_file_from_post(post)

                formatted_posts.append(
                    PostInfo(
                        post_no=post.post_no,
                        text=post.text or '',
                        user_name=user_name,
                        user_id=user_id,
                        time_created=str(post.time_created),
                        reply_no=post.reply_no,
                        type=post_type,
                        file=file_info,
                    )
                )

            chat_name = chat.title or 'Unknown'
            message_text = (
                f'Built conversation thread with {len(thread_posts)} messages from chat '
                f"'{chat_name}' starting at post #{root_message_id}"
            )

            return success_response(
                message=message_text,
                payload=BuildConversationThreadPayload(
                    chat_id=chat_id,
                    root_message_id=root_message_id,
                    messages_loaded=messages_loaded,
                    total_in_thread=len(thread_posts),
                    posts=formatted_posts,
                ),
            )

        except ValueError as e:
            logger.error('Invalid chat_id or root_message_id: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while building conversation thread: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while building conversation thread: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while building conversation thread: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while building conversation thread: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while building conversation thread: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def upload_file_to_chat(
        chat_id: str,
        file_path: str | None = None,
        file_content: str | None = None,
        filename: str | None = None,
        reply_to_message_id: str | None = None,
    ) -> ToolResponse[UploadFilePayload | None]:
        """
        Upload a file to a chat.

        Args:
            chat_id: ID of the chat to upload file to
            file_path: Absolute path to the file on local filesystem (mutually exclusive with file_content)
            file_content: Base64-encoded file content (mutually exclusive with file_path)
            filename: Filename to use when file_content is provided (required if file_content is set)
            reply_to_message_id: Post number to reply to (optional)

        Returns:
            ToolResponse with UploadFilePayload containing uploaded file details including file ID, name, size, and URL
        """
        temp_file_path: Path | None = None

        try:
            client = await get_client()

            # Validate input parameters
            if file_path and file_content:
                return error_response(
                    message='Invalid input',
                    error='Cannot specify both file_path and file_content. Use only one.',
                )
            if not file_path and not file_content:
                return error_response(
                    message='Invalid input',
                    error='Must specify either file_path or file_content.',
                )
            if file_content and not filename:
                return error_response(
                    message='Invalid input',
                    error='filename is required when using file_content.',
                )

            # Handle file_content - create temporary file
            if file_content:
                # At this point filename must be set due to validation above
                assert filename is not None

                logger.info(f'Uploading file from content to chat {chat_id}: {filename}')

                # Decode base64 content
                file_data = base64.b64decode(file_content)

                # Create temporary file with original filename
                temp_dir = Path(tempfile.gettempdir())
                temp_file_path = temp_dir / filename

                # Write binary content to temp file
                temp_file_path.write_bytes(file_data)

                upload_path = str(temp_file_path)
            else:
                logger.info(f'Uploading file from path to chat {chat_id}: {file_path}')
                upload_path = file_path  # type: ignore[assignment]

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))
            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            # Upload file using Chat.upload_file
            reply_no = int(reply_to_message_id) if reply_to_message_id else None
            uploaded_file = await chat.upload_file(upload_path, reply_no=reply_no)

            # Fallback to local file info when API response lacks fields
            actual_path = Path(upload_path)
            file_name = uploaded_file.name or actual_path.name
            file_size = uploaded_file.size or actual_path.stat().st_size

            chat_name = chat.title or 'Unknown'
            message_text = (
                f"File '{file_name}' uploaded successfully to chat '{chat_name}' ({file_size} bytes)"
            )

            return success_response(
                message=message_text,
                payload=UploadFilePayload(
                    file_id=uploaded_file.guid,
                    filename=file_name,
                    size=file_size,
                    url=uploaded_file.url,
                    chat_id=chat_id,
                ),
            )

        except FileNotFoundError as e:
            logger.error('File not found: %s', e)
            return error_response(
                message='File not found',
                error=f'File not found: {e!s}',
            )
        except ValueError as e:
            logger.error('Invalid chat_id or reply_to_message_id: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while uploading file: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while uploading file: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while uploading file: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while uploading file: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while uploading file: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )
        finally:
            # Clean up temporary file if created
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()

    @mcp.tool()
    async def get_message_from_url(
        url: str,
    ) -> ToolResponse[GetMessageFromUrlPayload | None]:
        """
        Get a specific message from a pararam.io URL.

        Args:
            url: Pararam.io URL (e.g., https://app.pararam.io/#/organizations/1/threads/12345#post_no-6789)

        Returns:
            ToolResponse with GetMessageFromUrlPayload containing message details including
            post_no, text, sender, and timestamp
        """
        try:
            logger.info(f'Parsing URL: {url}')

            # Parse chat_id from URL pattern: /threads/(\d+)
            chat_match = re.search(r'/threads/(\d+)', url)
            if not chat_match:
                return error_response(
                    message='Invalid URL format',
                    error='Could not extract chat ID from URL. Expected format: /threads/[NUMBER]',
                )

            chat_id = chat_match.group(1)

            # Parse post_no from URL pattern: #post_no-(\d+)
            post_match = re.search(r'#post_no-(\d+)', url)
            if not post_match:
                return error_response(
                    message='Invalid URL format',
                    error='Could not extract post number from URL. Expected format: #post_no-[NUMBER]',
                )

            post_no = int(post_match.group(1))

            logger.info(f'Extracted chat_id: {chat_id}, post_no: {post_no}')

            # Get client and chat

            client = await get_client()

            chat = await client.client.get_chat_by_id(int(chat_id))

            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            # Load a range of posts around the target post_no
            # Load from post_no to post_no to get just this one post
            messages = await chat.load_posts(start_post_no=post_no, end_post_no=post_no)

            if not messages:
                return error_response(
                    message=f'Post {post_no} not found in chat {chat_id}',
                    error='Post not found',
                )

            # Get the target post
            post = messages[0]

            # Load full post data if not already loaded
            if not post.is_loaded:
                await post.load()

            user_name = 'Unknown'
            user_id = post.user_id if post.user_id else None
            if post.meta and 'user' in post.meta:
                user_name = post.meta['user'].get('name', 'Unknown')

            # Get post type and extract primary file info
            post_type = get_post_type(post)
            file_info = extract_file_from_post(post)

            chat_name = chat.title or 'Unknown'
            message_text = f"Retrieved post #{post.post_no} from chat '{chat_name}' by {user_name}"

            return success_response(
                message=message_text,
                payload=GetMessageFromUrlPayload(
                    url=url,
                    chat_id=chat_id,
                    chat_name=chat_name,
                    post=PostInfo(
                        post_no=post.post_no,
                        text=post.text or '',
                        user_name=user_name,
                        user_id=user_id,
                        time_created=str(post.time_created),
                        reply_no=post.reply_no,
                        type=post_type,
                        file=file_info,
                    ),
                ),
            )

        except ValueError as e:
            logger.error('Invalid URL or chat_id: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while getting message from URL: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while getting message from URL: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while getting message from URL: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while getting message from URL: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while getting message from URL: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def get_post_attachments(
        chat_id: str,
        post_no: str,
    ) -> ToolResponse[GetPostAttachmentsPayload | None]:
        """
        Get list of attachments (files, images, documents) from a specific post.

        Args:
            chat_id: ID of the chat
            post_no: Post number

        Returns:
            ToolResponse with GetPostAttachmentsPayload containing list of attachments including
            file ID, name, size, and download URL
        """
        try:
            client = await get_client()

            logger.info(f'Getting attachments from post {post_no} in chat {chat_id}')

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))
            if not chat:
                return error_response(
                    message=f'Chat {chat_id} not found',
                    error='Chat not found',
                )

            # Load the specific post
            messages = await chat.load_posts(start_post_no=int(post_no), end_post_no=int(post_no))
            if not messages:
                return error_response(
                    message=f'Post {post_no} not found in chat {chat_id}',
                    error='Post not found',
                )

            post = messages[0]

            # Load post data if not loaded
            if not post.is_loaded:
                await post.load()

            # Get post info
            user_name = 'Unknown'
            user_id = post.user_id if post.user_id else None
            if post.meta and 'user' in post.meta:
                user_name = post.meta['user'].get('name', 'Unknown')

            # Get post type and extract primary file info
            post_type = get_post_type(post)
            file_info = extract_file_from_post(post)

            post_info = PostInfo(
                post_no=post.post_no,
                text=post.text or '',
                user_name=user_name,
                user_id=user_id,
                time_created=str(post.time_created),
                reply_no=post.reply_no,
                type=post_type,
                file=file_info,
            )

            # Quick check if post has any files
            if not post.is_file:
                return success_response(
                    message=f'Post #{post_no} in chat {chat_id} has no attachments',
                    payload=GetPostAttachmentsPayload(
                        chat_id=chat_id,
                        post_no=post_no,
                        post=post_info,
                        has_attachments=False,
                        attachments=[],
                    ),
                )

            # Load attachments
            await post.load_attachments()

            # Collect all files from both sources
            files = []

            # 1. Check post.file (main file attached to post)
            if post.file:
                files.append(post.file)

            # 2. Check attachment_files (additional attachments)
            additional_files = await post.attachment_files()
            if additional_files:
                files.extend(additional_files)

            # Double-check if we found any files
            if not files:
                return success_response(
                    message=f'Post #{post_no} in chat {chat_id} has no attachments',
                    payload=GetPostAttachmentsPayload(
                        chat_id=chat_id,
                        post_no=post_no,
                        post=post_info,
                        has_attachments=False,
                        attachments=[],
                    ),
                )

            # Format attachments
            attachments_list = []
            for file_attachment in files:
                attachments_list.append(
                    FileInfo(
                        guid=file_attachment.guid,
                        name=file_attachment.name,
                        size=file_attachment.size,
                        url=file_attachment.url,
                        mime_type=file_attachment.mime_type,
                    )
                )

            message_text = f'Found {len(attachments_list)} attachment(s) in post #{post_no} (chat {chat_id})'

            return success_response(
                message=message_text,
                payload=GetPostAttachmentsPayload(
                    chat_id=chat_id,
                    post_no=post_no,
                    post=post_info,
                    has_attachments=True,
                    attachments_count=len(attachments_list),
                    attachments=attachments_list,
                ),
            )

        except ValueError as e:
            logger.error('Invalid chat_id or post_no: %s', e)
            return error_response(
                message='Invalid input',
                error=f'Invalid input: {e!s}',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while getting post attachments: %s', e)
            return error_response(
                message='Authentication failed',
                error=f'Authentication error: {e!s}',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while getting post attachments: %s', e)
            return error_response(
                message='HTTP request failed',
                error=f'Request error: {e!s}',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while getting post attachments: %s', e)
            return error_response(
                message='API error occurred',
                error=f'API error: {e!s}',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while getting post attachments: %s', e)
            return error_response(
                message='Network error occurred',
                error=f'Network error: {e!s}',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while getting post attachments: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )

    @mcp.tool()
    async def download_post_attachment(
        chat_id: str,
        post_no: str,
        file_guid: str,
        output_path: str | None = None,
    ) -> ImageContent | DownloadAttachmentResponse | DownloadAttachmentErrorResponse:
        """
        Download a specific attachment from a post.

        If output_path is provided, saves file to disk and returns DownloadAttachmentResponse.
        If output_path is None and file type is supported, returns ImageContent for direct display.
        If output_path is None and file type is not supported, returns DownloadAttachmentErrorResponse.

        Supported file types for ImageContent:
        - Images: JPEG, PNG, GIF, WEBP
        - Documents: PDF, DOCX, DOC, TXT, RTF, ODT, HTML, EPUB
        - Spreadsheets: XLSX, XLS, CSV
        - Data: JSON, XML

        Args:
            chat_id: ID of the chat
            post_no: Post number
            file_guid: GUID of the file to download (from get_post_attachments)
            output_path: Optional absolute path where to save the file.
                If None, only supported file types can be displayed

        Returns:
            ImageContent for supported file types (direct display in Claude),
            DownloadAttachmentResponse model when saved to disk,
            DownloadAttachmentErrorResponse model for errors,
            or error string
        """
        try:
            client = await get_client()

            logger.info(f'Downloading attachment {file_guid} from post {post_no} in chat {chat_id}')

            # Get chat by ID
            chat = await client.client.get_chat_by_id(int(chat_id))

            if not chat:
                return DownloadAttachmentErrorResponse(
                    message=f'Chat {chat_id} not found',
                    success=False,
                    error='Chat not found',
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename='',
                    size=0,
                    mime_type='',
                )

            # Load the specific post
            messages = await chat.load_posts(start_post_no=int(post_no), end_post_no=int(post_no))
            if not messages:
                return DownloadAttachmentErrorResponse(
                    message=f'Post {post_no} not found in chat {chat_id}',
                    success=False,
                    error='Post not found',
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename='',
                    size=0,
                    mime_type='',
                )

            post = messages[0]

            # Load post data if not loaded
            if not post.is_loaded:
                await post.load()

            # Quick check if post has any files

            if not post.is_file:
                return DownloadAttachmentErrorResponse(
                    message=f'Post {post_no} has no attachments',
                    success=False,
                    error='Post has no attachments',
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename='',
                    size=0,
                    mime_type='',
                )

            # Load attachments
            await post.load_attachments()

            # Collect all files from both sources
            files = []

            # 1. Check post.file (main file attached to post)
            if post.file:
                files.append(post.file)

            # 2. Check attachment_files (additional attachments)
            additional_files = await post.attachment_files()
            if additional_files:
                files.extend(additional_files)

            # Find the file by GUID
            target_file = None
            for file_attachment in files:
                if file_attachment.guid == file_guid:
                    target_file = file_attachment
                    break

            if not target_file:
                return DownloadAttachmentErrorResponse(
                    message=f'File {file_guid} not found in post {post_no}',
                    success=False,
                    error='File not found',
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename='',
                    size=0,
                    mime_type='',
                )

            # Check file size limit (1MB = 1048576 bytes)
            max_size = 1048576  # 1MB
            if target_file.size > max_size:
                return DownloadAttachmentErrorResponse(
                    message=f"File '{target_file.name}' size ({target_file.size} bytes) exceeds 1MB limit",
                    success=False,
                    error='File size exceeds limit',
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename=target_file.name,
                    size=target_file.size,
                    mime_type=target_file.mime_type,
                    file_size=target_file.size,
                    max_size=max_size,
                )

            # Download the file - returns bytes
            file_data = await post.download_file(target_file.name)

            # If output_path provided, save to disk
            if output_path:
                file_path = Path(output_path)
                file_path.write_bytes(file_data)
                message_text = f"Downloaded '{target_file.name}' ({target_file.size} bytes) to {file_path.absolute()}"
                return DownloadAttachmentResponse(
                    message=message_text,
                    success=True,
                    chat_id=chat_id,
                    post_no=post_no,
                    file_guid=file_guid,
                    filename=target_file.name,
                    size=target_file.size,
                    downloaded_size=len(file_data),
                    saved_to=str(file_path.absolute()),
                )

            # If no output_path, return ImageContent for supported file types
            # Claude supports: images, PDFs, documents (DOCX, TXT, RTF, ODT, HTML, EPUB),
            # spreadsheets (XLSX, CSV), and other formats
            supported_mime_types = {
                # Images
                'image/jpeg',
                'image/jpg',
                'image/png',
                'image/gif',
                'image/webp',
                # Documents
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
                'application/msword',  # DOC
                'text/plain',
                'application/rtf',
                'application/vnd.oasis.opendocument.text',  # ODT
                'text/html',
                'application/epub+zip',
                # Spreadsheets
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
                'application/vnd.ms-excel',  # XLS
                'text/csv',
                # Data formats
                'application/json',
                'application/xml',
                'text/xml',
            }

            if target_file.mime_type and target_file.mime_type in supported_mime_types:
                logger.info(f'Returning as ImageContent: {target_file.name} ({target_file.mime_type})')

                # Create ImageContent with base64-encoded data
                file_base64 = base64.b64encode(file_data).decode('utf-8')
                return ImageContent(
                    type='image',
                    data=file_base64,
                    mimeType=target_file.mime_type,
                )

            # For unsupported file types, return info without base64 to avoid breaking chat
            message_text = (
                f"File '{target_file.name}' type '{target_file.mime_type}' cannot be displayed. "
                'Provide output_path parameter to download it.'
            )
            return DownloadAttachmentErrorResponse(
                message=message_text,
                success=False,
                error='File cannot be loaded by Claude',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename=target_file.name,
                size=target_file.size,
                mime_type=target_file.mime_type,
            )

        except ValueError as e:
            logger.error('Invalid chat_id or post_no: %s', e)
            return DownloadAttachmentErrorResponse(
                message='Invalid input',
                success=False,
                error=f'Invalid input: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except FileNotFoundError as e:
            logger.error('Output path not found: %s', e)
            return DownloadAttachmentErrorResponse(
                message='Output path not found',
                success=False,
                error=f'File path error: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except PararamioAuthenticationError as e:
            logger.error('Authentication failed while downloading attachment: %s', e)
            return DownloadAttachmentErrorResponse(
                message='Authentication failed',
                success=False,
                error=f'Authentication error: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed while downloading attachment: %s', e)
            return DownloadAttachmentErrorResponse(
                message='HTTP request failed',
                success=False,
                error=f'Request error: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error while downloading attachment: %s', e)
            return DownloadAttachmentErrorResponse(
                message='API error occurred',
                success=False,
                error=f'API error: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except httpx.HTTPError as e:
            logger.error('Network error while downloading attachment: %s', e)
            return DownloadAttachmentErrorResponse(
                message='Network error occurred',
                success=False,
                error=f'Network error: {e!s}',
                chat_id=chat_id,
                post_no=post_no,
                file_guid=file_guid,
                filename='',
                size=0,
                mime_type='',
            )
        except Exception as e:
            # Top-level handler to prevent MCP server crash on unexpected errors
            logger.error('Unexpected error while downloading attachment: %s', e, exc_info=True)
            return error_response(
                message='Unexpected error occurred',
                error=f'Unexpected error: {e!s}',
            )
