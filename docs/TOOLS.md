# Tools Documentation

Complete reference for all available tools in Pararam Nexus MCP.

## Response Format

All tools (except `download_post_attachment` when returning images) return a standardized `ToolResponse` object:

```typescript
{
  "success": boolean,        // Whether the operation was successful
  "message": string,         // Human-readable summary of the result
  "error": string | null,    // Error message if operation failed (null on success)
  "payload": object | null   // The actual response data (null on error)
}
```

## Table of Contents

- [Response Format](#response-format)
- [Message Operations](#message-operations)
- [Chat Operations](#chat-operations)
- [File Operations](#file-operations)
- [User Operations](#user-operations)

## Message Operations

### search_messages

Search for messages across all chats.

**Parameters:**
- `query` (str): Search query string
- `limit` (int, optional): Maximum number of results to return (default: 20)

**Returns:**
`ToolResponse[SearchMessagesPayload]` with payload containing:
- `query`: The search query used
- `total_count`: Total number of matches found
- `returned_count`: Number of results returned
- `messages`: Array of message objects with:
  - `post_no`: Message number
  - `text`: Message content
  - `user_name`: Name of the sender
  - `chat_id`: ID of the chat
  - `chat_name`: Name of the chat

**Success Example:**
```json
{
  "success": true,
  "message": "Found 15 messages matching 'bug report'",
  "error": null,
  "payload": {
    "query": "bug report",
    "total_count": 15,
    "returned_count": 15,
    "messages": [
      {
        "post_no": 123,
        "text": "Found a bug in the login form",
        "user_name": "John Doe",
        "chat_id": "456",
        "chat_name": "Bug Reports"
      }
    ]
  }
}
```

**Error Example:**
```json
{
  "success": false,
  "message": "Authentication failed",
  "error": "Authentication error: Invalid credentials",
  "payload": null
}
```

### get_chat_messages

Get messages from a specific chat.

**Parameters:**
- `chat_id` (str): ID of the chat to get messages from
- `limit` (int, optional): Maximum number of messages to return (default: 50)
- `before_message_id` (str, optional): Get messages before this message ID (for pagination)

**Returns:**
`ToolResponse[GetChatMessagesPayload]` with payload containing:
- `chat_id`: ID of the chat
- `count`: Number of messages returned
- `messages`: Array of message objects with:
  - `post_no`: Message number
  - `text`: Message content
  - `user_name`: Name of the sender
  - `user_id`: ID of the sender (if available)
  - `time_created`: Timestamp when message was created
  - `reply_no`: Post number this message replies to (if any)

**Success Example:**
```json
{
  "success": true,
  "message": "Retrieved 10 messages from chat 456",
  "error": null,
  "payload": {
    "chat_id": "456",
    "count": 10,
    "messages": [
      {
        "post_no": 789,
        "text": "Hello team!",
        "user_name": "Jane Smith",
        "user_id": 123,
        "time_created": "2025-10-15 10:30:00",
        "reply_no": null
      }
    ]
  }
}
```

### send_message

Send a message to a chat.

**Parameters:**
- `chat_id` (str): ID of the chat to send message to
- `text` (str): Message text to send
- `reply_to_message_id` (str, optional): Post number to reply to

**Message Formatting:**
Pararam supports Markdown-like text, but does not support Markdown headings (`#`, `##`, `###`).
Use `**bold**` section titles instead. Use colors as `[#RRGGBB](text)`;
colored bullet example: `[#2E7D32](●)`. Keep tables simple because colors may not render inside
table cells. Use `@all`, `@online`, `@admin`, and `@groups` only when the user explicitly asks
for broad notification, and ask for explicit confirmation before sending such mentions.
See `docs/PARARAM_FORMATTING.md` for the full syntax.

**Returns:**
`ToolResponse[SendMessagePayload]` with payload containing:
- `post_no`: ID of the sent message
- `chat_id`: ID of the chat
- `text`: Message content sent
- `time_created`: Timestamp when message was created

**Success Example:**
```json
{
  "success": true,
  "message": "Message sent successfully to chat 456",
  "error": null,
  "payload": {
    "post_no": 890,
    "chat_id": "456",
    "text": "Message sent successfully",
    "time_created": "2025-10-15 11:00:00"
  }
}
```

### get_message_from_url

Extract and retrieve a message from a pararam.io URL.

**Parameters:**
- `url` (str): Pararam.io URL (e.g., `https://app.pararam.io/#/organizations/1/threads/12345#post_no-6789`)

**Returns:**
JSON string with message details:
- `url`: Original URL
- `chat_id`: Extracted chat ID
- `chat_name`: Name of the chat
- `post`: Message object with:
  - `post_no`: Message number
  - `text`: Message content
  - `user_name`: Name of the sender
  - `user_id`: ID of the sender (if available)
  - `time_created`: Timestamp when message was created
  - `reply_no`: Post number this message replies to (if any)

**Example:**
```json
{
  "url": "https://app.pararam.io/#/organizations/1/threads/12345#post_no-6789",
  "chat_id": "12345",
  "chat_name": "Development",
  "post": {
    "post_no": 6789,
    "text": "Check this out",
    "user_name": "Bob",
    "user_id": 42,
    "time_created": "2025-10-15 09:00:00",
    "reply_no": 6788
  }
}
```

## Chat Operations

### search_chats

Search for chats by name or description.

**Parameters:**
- `query` (str): Search query string
- `limit` (int, optional): Maximum number of results to return (default: 20)

**Returns:**
JSON string with chat list:
- `query`: The search query used
- `count`: Number of chats returned
- `chats`: Array of chat objects with:
  - `id`: Chat ID
  - `title`: Chat name
  - `type`: Chat type (e.g., "group", "private")
  - `members_count`: Number of members
  - `description`: Chat description

**Example:**
```json
{
  "query": "dev",
  "count": 3,
  "chats": [
    {
      "id": 123,
      "title": "Development Team",
      "type": "group",
      "members_count": 15,
      "description": "Main development chat"
    }
  ]
}
```

### build_conversation_thread

Build a conversation thread starting from a root message.

Returns all messages that are replies to the root message or replies to those replies, recursively.

**Parameters:**
- `chat_id` (str): ID of the chat
- `root_message_id` (str): Post number to use as root of the conversation
- `limit` (int, optional): Maximum number of recent messages to load and search (default: 100)

**Returns:**
JSON string with flat list of all posts in the thread:
- `chat_id`: ID of the chat
- `root_message_id`: Root message ID
- `messages_loaded`: Total number of messages loaded from chat
- `total_in_thread`: Number of messages in the thread
- `posts`: Array of message objects sorted by post_no, each containing:
  - `post_no`: Message number
  - `text`: Message content
  - `user_name`: Name of the sender
  - `user_id`: ID of the sender (if available)
  - `time_created`: Timestamp when message was created
  - `reply_no`: Post number this message replies to (use to reconstruct tree)

**Example:**
```json
{
  "chat_id": "456",
  "root_message_id": "100",
  "messages_loaded": 50,
  "total_in_thread": 5,
  "posts": [
    {
      "post_no": 100,
      "text": "What do you think about this?",
      "user_name": "Alice",
      "user_id": 1,
      "time_created": "2025-10-15 10:00:00",
      "reply_no": null
    },
    {
      "post_no": 101,
      "text": "I agree!",
      "user_name": "Bob",
      "user_id": 2,
      "time_created": "2025-10-15 10:05:00",
      "reply_no": 100
    }
  ]
}
```

## File Operations

### upload_file_to_chat

Upload a file to a chat.

**Parameters:**
- `chat_id` (str): ID of the chat to upload file to
- `file_path` (str, optional): Absolute path to the file on local filesystem (mutually exclusive with file_content)
- `file_content` (str, optional): Base64-encoded file content (mutually exclusive with file_path)
- `filename` (str, optional): Filename to use when file_content is provided (required if file_content is set)
- `reply_to_message_id` (str, optional): Post number to reply to

**Returns:**
JSON string with uploaded file details:
- `success`: Boolean indicating success
- `file_id`: Unique identifier for the file
- `filename`: Name of the uploaded file
- `size`: File size in bytes
- `url`: URL to access the file
- `chat_id`: ID of the chat

**Example:**
```json
{
  "success": true,
  "file_id": "abc123-def456",
  "filename": "document.pdf",
  "size": 52428,
  "url": "https://cdn.pararam.io/files/abc123-def456",
  "chat_id": "456"
}
```

### get_post_attachments

Get list of attachments (files, images, documents) from a specific post.

**Parameters:**
- `chat_id` (str): ID of the chat
- `post_no` (str): Post number

**Returns:**
JSON string with list of attachments:
- `chat_id`: ID of the chat
- `post_no`: Post number
- `has_attachments`: Boolean indicating if post has attachments
- `attachments_count`: Number of attachments (if any)
- `attachments`: Array of attachment objects with:
  - `guid`: Unique identifier for the file
  - `name`: Filename
  - `size`: File size in bytes
  - `url`: URL to access the file
  - `mime_type`: MIME type of the file

**Example:**
```json
{
  "chat_id": "456",
  "post_no": "789",
  "has_attachments": true,
  "attachments_count": 2,
  "attachments": [
    {
      "guid": "abc123",
      "name": "screenshot.png",
      "size": 102400,
      "url": "https://cdn.pararam.io/files/abc123",
      "mime_type": "image/png"
    }
  ]
}
```

### download_post_attachment

Download a specific attachment from a post.

**Behavior:**
- If `output_path` is provided: saves file to disk and returns JSON with status
- If `output_path` is None and file type is supported: returns `ImageContent` for direct display in Claude Desktop/Code
- If `output_path` is None and file type is not supported: returns JSON with base64 content

**Supported File Types for Direct Display:**
- **Images**: JPEG, PNG, GIF, WEBP
- **Documents**: PDF, DOCX, DOC, TXT, RTF, ODT, HTML, EPUB
- **Spreadsheets**: XLSX, XLS, CSV
- **Data formats**: JSON, XML

**Parameters:**
- `chat_id` (str): ID of the chat
- `post_no` (str): Post number
- `file_guid` (str): GUID of the file to download (from get_post_attachments)
- `output_path` (str, optional): Absolute path where to save the file. If None, supported files returned as ImageContent, others as base64 JSON

**Size Limit:**
- Maximum file size: 1MB (1,048,576 bytes)
- Files larger than 1MB will return an error

**Returns:**

**For supported file types (when output_path is None):**
Returns an `ImageContent` object that displays natively in Claude Desktop/Code.

**For unsupported file types (when output_path is None):**
JSON string with error message:
```json
{
  "success": false,
  "error": "File cannot be loaded by Claude",
  "chat_id": "456",
  "post_no": "789",
  "file_guid": "abc123",
  "filename": "archive.zip",
  "size": 52428,
  "mime_type": "application/zip",
  "message": "File type \"application/zip\" cannot be loaded by Claude. To download this file, please provide output_path parameter to save it to disk."
}
```

**When saved to disk:**
```json
{
  "success": true,
  "chat_id": "456",
  "post_no": "789",
  "file_guid": "abc123",
  "filename": "document.pdf",
  "size": 52428,
  "downloaded_size": 52428,
  "saved_to": "/path/to/document.pdf"
}
```

**On size limit error:**
```json
{
  "success": false,
  "error": "File size exceeds limit",
  "file_size": 2097152,
  "max_size": 1048576,
  "message": "File size (2097152 bytes) exceeds 1MB limit"
}
```

## User Operations

### search_users

Search for users by name or unique name.

**Parameters:**
- `query` (str): Search query string (name or unique_name)
- `limit` (int, optional): Maximum number of results to return (default: 20)

**Returns:**
JSON string with list of users:
- `query`: The search query used
- `count`: Number of users returned
- `users`: Array of user objects with:
  - `id`: User ID
  - `name`: User's display name
  - `unique_name`: User's unique username
  - `active`: Whether user is active
  - `is_bot`: Whether user is a bot
  - `organizations`: List of organizations user belongs to

**Example:**
```json
{
  "query": "john",
  "count": 2,
  "users": [
    {
      "id": 123,
      "name": "John Doe",
      "unique_name": "johndoe",
      "active": true,
      "is_bot": false,
      "organizations": [1, 2]
    }
  ]
}
```

### get_user_info

Get detailed information about a specific user.

**Parameters:**
- `user_id` (str): User ID

**Returns:**
JSON string with user details:
- `id`: User ID
- `name`: User's display name
- `unique_name`: User's unique username
- `active`: Whether user is active
- `is_bot`: Whether user is a bot
- `time_created`: When user account was created
- `time_updated`: When user account was last updated
- `timezone_offset_minutes`: User's timezone offset in minutes
- `organizations`: List of organizations user belongs to

**Example:**
```json
{
  "id": 123,
  "name": "John Doe",
  "unique_name": "johndoe",
  "active": true,
  "is_bot": false,
  "time_created": "2024-01-15 08:30:00",
  "time_updated": "2025-10-15 12:00:00",
  "timezone_offset_minutes": -420,
  "organizations": [1, 2, 5]
}
```

### get_user_team_status

Get user's status in teams (member, admin, guest, or not in team).

**Parameters:**
- `user_id` (str): User ID to check
- `team_id` (str, optional): Team ID to check status in specific team. If not provided, returns status in all teams

**Returns:**
JSON string with team membership status:
- `user_id`: User ID checked
- `teams_checked`: Number of teams checked
- `team_statuses`: Array of team status objects with:
  - `team_id`: Team ID
  - `team_title`: Team name
  - `team_slug`: Team slug/identifier
  - `is_member`: Whether user is a regular member
  - `is_admin`: Whether user is an admin
  - `is_guest`: Whether user is a guest
  - `in_team`: Whether user has any access to the team

**Example:**
```json
{
  "user_id": "123",
  "teams_checked": 2,
  "team_statuses": [
    {
      "team_id": 1,
      "team_title": "Engineering",
      "team_slug": "engineering",
      "is_member": true,
      "is_admin": false,
      "is_guest": false,
      "in_team": true
    },
    {
      "team_id": 2,
      "team_title": "Design",
      "team_slug": "design",
      "is_member": false,
      "is_admin": false,
      "is_guest": true,
      "in_team": true
    }
  ]
}
```

## Error Handling

All tools use consistent error handling with specific exception types:

- **Authentication errors**: Returned when credentials are invalid or session has expired
- **Request errors**: Returned when HTTP request fails
- **API errors**: Returned when pararam.io API returns an error
- **Network errors**: Returned when network connection fails
- **Validation errors**: Returned when input parameters are invalid

Error responses are returned as plain text strings starting with the error type, e.g.:
```
Authentication error: Invalid credentials
Request error: Chat 999 not found
API error: Invalid post number
Network error: Connection timeout
Invalid input: user_id must be a number
```
