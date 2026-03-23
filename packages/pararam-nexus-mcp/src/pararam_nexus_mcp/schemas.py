"""Pydantic schemas for tool input validation."""

import re

from pydantic import BaseModel, Field, field_validator, model_validator


class SearchMessagesInput(BaseModel):
    """Input schema for search_messages tool."""

    query: str = Field(..., min_length=1, description='Search query string')
    limit: int = Field(20, ge=1, le=100, description='Maximum number of results (1-100)')


class GetChatMessagesInput(BaseModel):
    """Input schema for get_chat_messages tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    limit: int = Field(50, ge=1, le=200, description='Maximum number of messages (1-200)')
    before_message_id: str | None = Field(None, pattern=r'^\d+$', description='Get messages before this ID')


class SendMessageInput(BaseModel):
    """Input schema for send_message tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    text: str = Field(..., min_length=1, description='Message text')
    reply_to_message_id: str | None = Field(None, pattern=r'^\d+$', description='Reply to post number')


class SearchChatsInput(BaseModel):
    """Input schema for search_chats tool."""

    query: str = Field(..., min_length=1, description='Search query string')
    limit: int = Field(20, ge=1, le=100, description='Maximum number of results (1-100)')


class BuildConversationThreadInput(BaseModel):
    """Input schema for build_conversation_thread tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    root_message_id: str = Field(..., pattern=r'^\d+$', description='Root message post number')
    limit: int = Field(100, ge=1, le=500, description='Maximum messages to load (1-500)')


class UploadFileToChatInput(BaseModel):
    """Input schema for upload_file_to_chat tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    file_path: str | None = Field(None, description='Absolute path to file')
    file_content: str | None = Field(None, description='Base64-encoded file content')
    filename: str | None = Field(None, min_length=1, description='Filename (required with file_content)')
    reply_to_message_id: str | None = Field(None, pattern=r'^\d+$', description='Reply to post number')

    @model_validator(mode='after')
    def validate_file_source(self) -> UploadFileToChatInput:
        """Validate that only one file source is provided."""
        if self.file_path and self.file_content:
            raise ValueError('Cannot specify both file_path and file_content')
        if not self.file_path and not self.file_content:
            raise ValueError('Must specify either file_path or file_content')
        if self.file_content and not self.filename:
            raise ValueError('filename is required when using file_content')
        return self


class GetMessageFromUrlInput(BaseModel):
    """Input schema for get_message_from_url tool."""

    url: str = Field(..., description='Pararam.io URL')

    @field_validator('url')
    @classmethod
    def validate_pararam_url(cls, v: str) -> str:
        """Validate that URL is a pararam.io URL with required patterns."""
        if 'pararam.io' not in v:
            raise ValueError('URL must be a pararam.io URL')

        if not re.search(r'/threads/\d+', v):
            raise ValueError('URL must contain /threads/[NUMBER] pattern')

        if not re.search(r'#post_no-\d+', v):
            raise ValueError('URL must contain #post_no-[NUMBER] pattern')

        return v


class GetPostAttachmentsInput(BaseModel):
    """Input schema for get_post_attachments tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    post_no: str = Field(..., pattern=r'^\d+$', description='Post number (numeric string)')


class DownloadPostAttachmentInput(BaseModel):
    """Input schema for download_post_attachment tool."""

    chat_id: str = Field(..., pattern=r'^\d+$', description='Chat ID (numeric string)')
    post_no: str = Field(..., pattern=r'^\d+$', description='Post number (numeric string)')
    file_guid: str = Field(..., min_length=1, description='File GUID from get_post_attachments')
    output_path: str | None = Field(None, min_length=1, description='Path to save file. If None, returns base64')
