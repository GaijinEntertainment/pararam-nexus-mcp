# Pararam Nexus MCP

A Model Context Protocol (MCP) server for interacting with [pararam.io](https://pararam.io) - a modern communication and collaboration platform.

## About pararam.io

Pararam.io is a communication platform that provides:

- **Messaging**: Create groups and private chats
- **Team Organization**: Organize people into teams
- **Communication**: Group and private calls (audio and video)
- **Cross-platform**: Available on mobile (iOS, Android, Huawei) and web

This MCP server uses the `pararamio-aio` library to provide asynchronous access to pararam.io features through the Model Context Protocol.

## Features

- Asynchronous API client for pararam.io
- Two-factor authentication support (TOTP)
- Session persistence with cookie storage
- Comprehensive chat and message management
- File attachment handling (upload and download)
- URL-based message retrieval
- Conversation thread building

## Available Tools

### Message Operations
- **search_messages**: Search for messages across all chats with advanced search syntax (Boolean operators, wildcards, filters)
- **get_chat_messages**: Get recent messages from a specific chat
- **send_message**: Send a message to a chat with optional reply and quote text
- **get_message_from_url**: Extract and retrieve a message from pararam.io URL

### Chat Operations
- **search_chats**: Search for chats by name or description
- **build_conversation_thread**: Build a conversation tree from a root message

### File Operations
- **upload_file_to_chat**: Upload files to a chat (from path or base64 content)
- **get_post_attachments**: List all attachments in a post
- **download_post_attachment**: Download attachments (to disk or as ImageContent)
  - 1MB size limit for downloads
  - Supported formats for direct display: images (JPEG, PNG, GIF, WEBP), documents (PDF, DOCX, DOC, TXT, RTF, ODT, HTML, EPUB), spreadsheets (XLSX, XLS, CSV), data (JSON, XML)
  - Returns ImageContent for supported types (displays natively in Claude Desktop/Code)
  - For unsupported types, requires output_path to save to disk
  - Saves to disk when output path is provided

### User Operations
- **search_users**: Search for users by name or unique name
- **get_user_info**: Get detailed information about a specific user
- **get_user_team_status**: Get user's status in teams (member, admin, guest)

## Tool Details

### send_message

Send a message to a chat with optional reply and quote functionality.

**Parameters:**
- `chat_id` (required): ID of the chat to send message to
- `text` (required): Message text to send
- `reply_to_message_id` (optional): Post number to reply to
- `quote_text` (optional): Text to quote from the replied message (only used with `reply_to_message_id`)

**Examples:**
```python
# Simple message
send_message(chat_id="123", text="Hello!")

# Reply to a message
send_message(
    chat_id="123",
    text="I agree!",
    reply_to_message_id="456"
)

# Reply with quoted text
send_message(
    chat_id="123",
    text="That's a great idea!",
    reply_to_message_id="456",
    quote_text="We should implement this feature next week"
)
```

## Installation

### Quick Install with uvx (Recommended)

Install directly from PyPI:

```bash
uvx pararam-nexus-mcp
```

Or install from GitHub:

```bash
uvx --from git+https://github.com/ivolnistov/pararam-nexus-mcp pararam-nexus-mcp
```

Or clone to a specific directory (e.g., `~/.mcp/`):

```bash
git clone https://github.com/ivolnistov/pararam-nexus-mcp.git ~/.mcp/pararam-nexus-mcp
cd ~/.mcp/pararam-nexus-mcp
uv sync
```

### Docker Installation

Pull from [Docker Hub](https://hub.docker.com/r/ivolnistov/pararam-nexus-mcp):

```bash
docker pull ivolnistov/pararam-nexus-mcp:latest
```

Or from GitHub Container Registry:

```bash
docker pull ghcr.io/ivolnistov/pararam-nexus-mcp:latest
```

### Development Installation

For local development:

```bash
git clone https://github.com/ivolnistov/pararam-nexus-mcp.git
cd pararam-nexus-mcp
uv sync --dev
```

## Configuration

Create a `.env` file with your pararam.io credentials:

```env
PARARAM_LOGIN=your_login
PARARAM_PASSWORD=your_password
PARARAM_2FA_KEY=your_2fa_key  # Optional
```

## MCP Client Configuration

### Claude Code (CLI)

Add the server using the Claude Code CLI:

```bash
# Using uvx (recommended)
claude mcp add pararam-nexus \
  --env PARARAM_LOGIN=myuser@example.com \
  --env PARARAM_PASSWORD=mySecurePassword123 \
  --env PARARAM_2FA_KEY=JBSWY3DPEHPK3PXP \
  -- uvx pararam-nexus-mcp

# Using Docker
claude mcp add pararam-nexus \
  --env PARARAM_LOGIN=myuser@example.com \
  --env PARARAM_PASSWORD=mySecurePassword123 \
  --env PARARAM_2FA_KEY=JBSWY3DPEHPK3PXP \
  -- docker run -i --rm ivolnistov/pararam-nexus-mcp:latest
```

### Claude Desktop

#### Option 1: Using uvx (Recommended)

1. Open Claude Desktop preferences
2. Navigate to the MCP section
3. Click Edit to open `claude_desktop_config.json`
4. Add the server configuration:

```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "uvx",
      "args": ["pararam-nexus-mcp"],
      "env": {
        "PARARAM_LOGIN": "myuser@example.com",
        "PARARAM_PASSWORD": "mySecurePassword123",
        "PARARAM_2FA_KEY": "JBSWY3DPEHPK3PXP"
      }
    }
  }
}
```

#### Option 2: Using Docker

First, create a volume for session persistence:
```bash
docker volume create pararam-mcp-data
```

Then add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "pararam-mcp-data:/app/.cookies",
        "-e",
        "PARARAM_LOGIN=myuser@example.com",
        "-e",
        "PARARAM_PASSWORD=mySecurePassword123",
        "-e",
        "PARARAM_2FA_KEY=JBSWY3DPEHPK3PXP",
        "ivolnistov/pararam-nexus-mcp:latest"
      ]
    }
  }
}
```

### Cursor IDE

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "uvx",
      "args": ["pararam-nexus-mcp"],
      "env": {
        "PARARAM_LOGIN": "myuser@example.com",
        "PARARAM_PASSWORD": "mySecurePassword123",
        "PARARAM_2FA_KEY": "JBSWY3DPEHPK3PXP"
      }
    }
  }
}
```

Or using Docker (with session persistence):

First, create a volume:
```bash
docker volume create pararam-mcp-data
```

Then add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "pararam-mcp-data:/app/.cookies",
        "-e",
        "PARARAM_LOGIN=myuser@example.com",
        "-e",
        "PARARAM_PASSWORD=mySecurePassword123",
        "-e",
        "PARARAM_2FA_KEY=JBSWY3DPEHPK3PXP",
        "ivolnistov/pararam-nexus-mcp:latest"
      ]
    }
  }
}
```

### Other MCP-Compatible Clients

For any MCP-compatible client that supports stdio transport:

**Using uvx:**
```bash
uvx pararam-nexus-mcp
```

**Using Docker (with session persistence):**
```bash
# Create volume for cookies
docker volume create pararam-mcp-data

# Run with volume mounted
docker run -i --rm \
  -v pararam-mcp-data:/app/.cookies \
  -e PARARAM_LOGIN=myuser@example.com \
  -e PARARAM_PASSWORD=mySecurePassword123 \
  -e PARARAM_2FA_KEY=JBSWY3DPEHPK3PXP \
  ivolnistov/pararam-nexus-mcp:latest
```

**Environment variables:**
- `PARARAM_LOGIN` (required): Your pararam.io login
- `PARARAM_PASSWORD` (required): Your pararam.io password
- `PARARAM_2FA_KEY` (optional): Your 2FA secret key for TOTP authentication

## Usage

### If installed with uvx:

```bash
uvx --from git+https://github.com/ivolnistov/pararam-nexus-mcp pararam-nexus-mcp
```

### If cloned locally:

```bash
cd ~/.mcp/pararam-nexus-mcp
uv run pararam-nexus-mcp
```

### For development:

```bash
uv run pararam-nexus-mcp
```

## Development

Install pre-commit hooks:

```bash
uv run pre-commit install
```

Run linting and formatting:

```bash
uv run ruff check --fix src/
uv run ruff format src/
```

Run type checking:

```bash
uv run mypy src/pararam_nexus_mcp
```

Run tests:

```bash
uv run pytest
```

## Dependencies

- **FastMCP**: Model Context Protocol server framework
- **pararamio-aio**: Async Python client for pararam.io API
- **httpx**: Modern HTTP client
- **Pydantic**: Data validation using Python type annotations

## License

MIT
