"""Pydantic models for MCP tool responses."""

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


# Base response model
class ToolResponse[T](BaseModel):
    """Base response model for all tools.

    Always wraps tool responses with standardized success/error/message fields.
    """

    success: bool = Field(..., description='Whether the operation was successful')
    message: str = Field(..., description='Human-readable summary of the result')
    error: str | None = Field(default=None, description='Error message if operation failed')
    payload: T | None = Field(default=None, description='The actual response data')


# Forward declare AttachmentInfo for use in PostInfo
class FileInfo(BaseModel):
    """Information about a file attachment."""

    guid: str = Field(..., description='Unique identifier for the file')
    name: str = Field(..., description='Filename')
    size: int = Field(..., description='File size in bytes')
    url: str | None = Field(None, description='URL to access the file')
    mime_type: str = Field(..., description='MIME type of the file')


# Forward declare PostInfo for use in other models
class PostInfo(BaseModel):
    """Information about a post."""

    post_no: int = Field(..., description='Post number')
    text: str = Field(..., description='Post content')
    user_name: str = Field(..., description='Name of the author')
    user_id: int | None = Field(None, description='ID of the author')
    time_created: str = Field(..., description='When post was created')
    reply_no: int | None = Field(None, description='Post number this replies to')
    type: str = Field(default='post', description='Post type: "post", "file", or "event"')
    file: FileInfo | None = Field(
        None, description='File attachment if post is a file type. Use get_post_attachments for additional files'
    )


class ChatMessageInfo(BaseModel):
    """Message with chat information."""

    post_no: int = Field(..., description='Message number')
    text: str = Field(..., description='Message content')
    user_name: str = Field(..., description='Name of the sender')
    user_id: int | None = Field(None, description='ID of the sender')
    chat_id: int = Field(..., description='ID of the chat')
    chat_name: str = Field(..., description='Name of the chat')
    time_created: str = Field(..., description='When message was created')
    reply_no: int | None = Field(None, description='Post number this replies to')
    type: str = Field(default='post', description='Post type: "post", "file", or "event"')
    file: FileInfo | None = Field(
        None, description='File attachment if post is a file type. Use get_post_attachments for additional files'
    )


class SearchMessagesPayload(BaseModel):
    """Payload for search_messages response."""

    query: str = Field(..., description='The search query used')
    total_count: int = Field(..., description='Total number of matches found')
    returned_count: int = Field(..., description='Number of results returned')
    messages: list[ChatMessageInfo] = Field(..., description='List of messages found')


class SearchMessagesResponse(BaseModel):
    """Response from search_messages tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    query: str = Field(..., description='The search query used')
    total_count: int = Field(..., description='Total number of matches found')
    returned_count: int = Field(..., description='Number of results returned')
    messages: list[ChatMessageInfo] = Field(..., description='List of messages found')


class GetChatMessagesPayload(BaseModel):
    """Payload for get_chat_messages response."""

    chat_id: str = Field(..., description='ID of the chat')
    count: int = Field(..., description='Number of messages returned')
    messages: list[PostInfo] = Field(..., description='List of messages')


class GetChatMessagesResponse(BaseModel):
    """Response from get_chat_messages tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    chat_id: str = Field(..., description='ID of the chat')
    count: int = Field(..., description='Number of messages returned')
    messages: list[PostInfo] = Field(..., description='List of messages')


class SendMessagePayload(BaseModel):
    """Payload for send_message response."""

    post_no: int = Field(..., description='ID of the sent message')
    chat_id: str = Field(..., description='ID of the chat')
    text: str = Field(..., description='Message content sent')
    time_created: str = Field(..., description='When message was created')


class SendMessageResponse(BaseModel):
    """Response from send_message tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    success: bool = Field(..., description='Whether the operation was successful')
    post_no: int = Field(..., description='ID of the sent message')
    chat_id: str = Field(..., description='ID of the chat')
    text: str = Field(..., description='Message content sent')
    time_created: str = Field(..., description='When message was created')


# Chat-related models
class ChatInfo(BaseModel):
    """Information about a chat."""

    id: int = Field(..., description='Chat ID')
    title: str = Field(..., description='Chat name')
    type: str = Field(..., description='Chat type')
    members_count: int = Field(..., description='Number of members')
    posts_count: int = Field(..., description='Number of posts in the chat')
    last_read_post_no: int = Field(..., description='Last read post number')
    thread_users: list[int] = Field(..., description='List of user IDs (members)')
    thread_admins: list[int] = Field(..., description='List of admin user IDs')
    thread_guests: list[int] = Field(..., description='List of guest user IDs')
    thread_groups: list[int] = Field(..., description='List of group IDs')
    description: str = Field(..., description='Chat description')


class SearchChatsPayload(BaseModel):
    """Payload for search_chats response."""

    query: str = Field(..., description='The search query used')
    count: int = Field(..., description='Number of chats returned')
    chats: list[ChatInfo] = Field(..., description='List of chats found')


class SearchChatsResponse(BaseModel):
    """Response from search_chats tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    query: str = Field(..., description='The search query used')
    count: int = Field(..., description='Number of chats returned')
    chats: list[ChatInfo] = Field(..., description='List of chats found')


class BuildConversationThreadPayload(BaseModel):
    """Payload for build_conversation_thread response."""

    chat_id: str = Field(..., description='ID of the chat')
    root_message_id: str = Field(..., description='Root message ID')
    messages_loaded: int = Field(..., description='Total number of messages loaded from chat')
    total_in_thread: int = Field(..., description='Number of messages in the thread')
    posts: list[PostInfo] = Field(..., description='List of posts in the thread')


class BuildConversationThreadResponse(BaseModel):
    """Response from build_conversation_thread tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    chat_id: str = Field(..., description='ID of the chat')
    root_message_id: str = Field(..., description='Root message ID')
    messages_loaded: int = Field(..., description='Total number of messages loaded from chat')
    total_in_thread: int = Field(..., description='Number of messages in the thread')
    posts: list[PostInfo] = Field(..., description='List of posts in the thread')


# File-related models
class UploadFilePayload(BaseModel):
    """Payload for upload_file_to_chat response."""

    file_id: str = Field(..., description='Unique identifier for the file')
    filename: str = Field(..., description='Name of the uploaded file')
    size: int = Field(..., description='File size in bytes')
    url: str = Field(..., description='URL to access the file')
    chat_id: str = Field(..., description='ID of the chat')


class UploadFileResponse(BaseModel):
    """Response from upload_file_to_chat tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    success: bool = Field(..., description='Whether file was uploaded successfully')
    file_id: str = Field(..., description='Unique identifier for the file')
    filename: str = Field(..., description='Name of the uploaded file')
    size: int = Field(..., description='File size in bytes')
    url: str = Field(..., description='URL to access the file')
    chat_id: str = Field(..., description='ID of the chat')


class GetMessageFromUrlPayload(BaseModel):
    """Payload for get_message_from_url response."""

    url: str = Field(..., description='Original URL')
    chat_id: str = Field(..., description='Extracted chat ID')
    chat_name: str = Field(..., description='Name of the chat')
    post: PostInfo = Field(..., description='Post information')


class GetMessageFromUrlResponse(BaseModel):
    """Response from get_message_from_url tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    url: str = Field(..., description='Original URL')
    chat_id: str = Field(..., description='Extracted chat ID')
    chat_name: str = Field(..., description='Name of the chat')
    post: PostInfo = Field(..., description='Post information')


class GetPostAttachmentsPayload(BaseModel):
    """Payload for get_post_attachments response."""

    chat_id: str = Field(..., description='ID of the chat')
    post_no: str = Field(..., description='Post number')
    post: PostInfo = Field(..., description='Post information')
    has_attachments: bool = Field(..., description='Whether post has attachments')
    attachments_count: int | None = Field(None, description='Number of attachments')
    attachments: list[FileInfo] = Field(..., description='List of attachments')


class GetPostAttachmentsResponse(BaseModel):
    """Response from get_post_attachments tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    chat_id: str = Field(..., description='ID of the chat')
    post_no: str = Field(..., description='Post number')
    has_attachments: bool = Field(..., description='Whether post has attachments')
    attachments_count: int | None = Field(None, description='Number of attachments')
    attachments: list[FileInfo] = Field(..., description='List of attachments')


class DownloadAttachmentResponse(BaseModel):
    """Response from download_post_attachment tool when saved to disk."""

    message: str = Field(..., description='Human-readable summary of the result')
    success: bool = Field(..., description='Whether download was successful')
    chat_id: str = Field(..., description='ID of the chat')
    post_no: str = Field(..., description='Post number')
    file_guid: str = Field(..., description='Unique identifier for the file')
    filename: str = Field(..., description='Filename')
    size: int = Field(..., description='File size in bytes')
    downloaded_size: int = Field(..., description='Actual bytes downloaded')
    saved_to: str = Field(..., description='Absolute path where file was saved')


class DownloadAttachmentErrorResponse(BaseModel):
    """Response from download_post_attachment tool when file cannot be displayed."""

    message: str = Field(..., description='Human-readable summary of the error')
    success: bool = Field(..., description='Always False for errors')
    error: str = Field(..., description='Error type')
    chat_id: str = Field(..., description='ID of the chat')
    post_no: str = Field(..., description='Post number')
    file_guid: str = Field(..., description='Unique identifier for the file')
    filename: str = Field(..., description='Filename')
    size: int = Field(..., description='File size in bytes')
    mime_type: str = Field(..., description='MIME type of the file')
    file_size: int | None = Field(None, description='File size if size limit exceeded')
    max_size: int | None = Field(None, description='Maximum allowed size')


# User-related models
class UserInfo(BaseModel):
    """Information about a user."""

    id: int = Field(..., description='User ID')
    name: str = Field(..., description="User's display name")
    unique_name: str = Field(..., description="User's unique username")
    active: bool = Field(..., description='Whether user is active')
    is_bot: bool = Field(..., description='Whether user is a bot')
    organizations: list[int] = Field(..., description='List of organization IDs')


class SearchUsersPayload(BaseModel):
    """Payload for search_users response."""

    query: str = Field(..., description='The search query used')
    count: int = Field(..., description='Number of users returned')
    users: list[UserInfo] = Field(..., description='List of users found')


class SearchUsersResponse(BaseModel):
    """Response from search_users tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    query: str = Field(..., description='The search query used')
    count: int = Field(..., description='Number of users returned')
    users: list[UserInfo] = Field(..., description='List of users found')


class GetUserInfoPayload(BaseModel):
    """Payload for get_user_info response."""

    id: int = Field(..., description='User ID')
    name: str = Field(..., description="User's display name")
    unique_name: str = Field(..., description="User's unique username")
    active: bool = Field(..., description='Whether user is active')
    is_bot: bool = Field(..., description='Whether user is a bot')
    time_created: str = Field(..., description='When user account was created')
    time_updated: str = Field(..., description='When user account was last updated')
    timezone_offset_minutes: int = Field(..., description="User's timezone offset in minutes")
    organizations: list[int] = Field(..., description='List of organization IDs')


class UserDetailInfo(BaseModel):
    """Detailed information about a user."""

    message: str = Field(..., description='Human-readable summary of the result')
    id: int = Field(..., description='User ID')
    name: str = Field(..., description="User's display name")
    unique_name: str = Field(..., description="User's unique username")
    active: bool = Field(..., description='Whether user is active')
    is_bot: bool = Field(..., description='Whether user is a bot')
    time_created: str = Field(..., description='When user account was created')
    time_updated: str = Field(..., description='When user account was last updated')
    timezone_offset_minutes: int = Field(..., description="User's timezone offset in minutes")
    organizations: list[int] = Field(..., description='List of organization IDs')


class TeamStatus(BaseModel):
    """User's status in a team."""

    team_id: int = Field(..., description='Team ID')
    team_title: str = Field(..., description='Team name')
    team_slug: str = Field(..., description='Team slug/identifier')
    is_member: bool = Field(..., description='Whether user is a regular member')
    is_admin: bool = Field(..., description='Whether user is an admin')
    is_guest: bool = Field(..., description='Whether user is a guest')
    in_team: bool = Field(..., description='Whether user has any access to the team')


class GetUserTeamStatusPayload(BaseModel):
    """Payload for get_user_team_status response."""

    user_id: str = Field(..., description='User ID checked')
    teams_checked: int = Field(..., description='Number of teams checked')
    team_statuses: list[TeamStatus] = Field(..., description='List of team statuses')


class GetUserTeamStatusResponse(BaseModel):
    """Response from get_user_team_status tool."""

    message: str = Field(..., description='Human-readable summary of the result')
    user_id: str = Field(..., description='User ID checked')
    teams_checked: int = Field(..., description='Number of teams checked')
    team_statuses: list[TeamStatus] = Field(..., description='List of team statuses')
