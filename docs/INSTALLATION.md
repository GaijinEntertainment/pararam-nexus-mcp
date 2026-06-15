# Installation Guide

Complete guide for installing and configuring Pararam Nexus MCP.

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- A pararam.io account with API access

## Installation Steps

### 1. Install UV Package Manager

If you don't have `uv` installed:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Choose Authentication Mode

The server starts in one of two modes depending on which environment variables
you provide.

#### Full mode: login + password (+ optional 2FA)

Full mode registers all tools and persists cookies between runs:

```bash
PARARAM_LOGIN=your_email@example.com \
PARARAM_PASSWORD=your_password \
PARARAM_2FA_KEY=your_2fa_key \
uvx pararam-nexus-mcp
```

#### Limited mode: `X-UserToken` service token

Limited mode uses `PARARAM_USER_TOKEN` instead of login/password. It registers
only chat, message, post, replies, edit, and delete tools. User lookups, global
search, and file operations are excluded.

```bash
PARARAM_USER_TOKEN=your_service_token \
uvx pararam-nexus-mcp
```

`PARARAM_USER_TOKEN` is mutually exclusive with `PARARAM_LOGIN` and
`PARARAM_PASSWORD`.

To get a user token:

1. Open the Pararam **Info Chat** bot documentation.
2. In **User Tokens**, run **Create new token** (`bot://cmd_create_user_token?title=Create+new+token&conf=True`).
3. InfoBot will reply with `New user token - ...`.
4. Copy that value into `PARARAM_USER_TOKEN` and store it as a secret.

You can also run **Get user tokens** (`bot://cmd_get_user_tokens?title=Get+user+tokens&conf=True`)
to view the tokens created under your account.

Tools available in limited mode:

- **Chats**: `get_chat`, `create_private_chat`, `create_group_chat`,
  `create_thread_chat`
- **Posts**: `get_chat_messages`, `get_message_from_url`,
  `get_reply_thread`, `get_replies_to_post`, `send_message`,
  `edit_post`, `delete_post`

### 3. Verify Package Startup

Run the server once to verify `uvx` can install and start the published package:

```bash
PARARAM_LOGIN=your_email@example.com \
PARARAM_PASSWORD=your_password \
PARARAM_2FA_KEY=your_2fa_key \
uvx pararam-nexus-mcp
```

Press Ctrl-C to stop the server.

Use environment variables for credentials. Full mode:

```env
# Required in full mode: your pararam.io credentials
PARARAM_LOGIN=your_email@example.com
PARARAM_PASSWORD=your_password

# Optional: Two-factor authentication key
PARARAM_2FA_KEY=your_2fa_secret_key
```

Limited mode:

```env
# Required in limited mode; do not set login/password with it
PARARAM_USER_TOKEN=your_service_token
```

Common options:

```env
# Optional: Debug mode (set to true for detailed logging)
MCP_DEBUG=false
```

#### Getting Your 2FA Key

If you have two-factor authentication enabled on pararam.io:

1. Go to your account settings
2. Navigate to Security settings
3. Find your TOTP secret key
4. Copy the secret key (not the QR code) to `PARARAM_2FA_KEY`

**Note:** The 2FA key is the secret used to generate the 6-digit codes, not the codes themselves.

## Configuring Claude Desktop

To use Pararam Nexus MCP with Claude Desktop, you need to add it to your MCP configuration.

### 1. Locate Claude Desktop Config

The configuration file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add MCP Server Configuration

Edit the configuration file and add the Pararam Nexus MCP server:

Full mode:

```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "uvx",
      "args": ["pararam-nexus-mcp"],
      "env": {
        "PARARAM_LOGIN": "your_email@example.com",
        "PARARAM_PASSWORD": "your_password",
        "PARARAM_2FA_KEY": "your_2fa_key"
      }
    }
  }
}
```

Limited mode:

```json
{
  "mcpServers": {
    "pararam-nexus": {
      "command": "uvx",
      "args": ["pararam-nexus-mcp"],
      "env": {
        "PARARAM_USER_TOKEN": "your_service_token"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

### 4. Verify Integration

In Claude Desktop, you should now be able to use Pararam Nexus MCP tools. Try asking:

> "Search for messages containing 'bug' in pararam"

Claude should be able to access the MCP tools and execute the search.

## Configuration Options

### Environment Variables

All configuration is done through environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PARARAM_LOGIN` | Full mode | - | Your pararam.io email/username |
| `PARARAM_PASSWORD` | Full mode | - | Your pararam.io password |
| `PARARAM_2FA_KEY` | No | - | TOTP secret key for 2FA in full mode |
| `PARARAM_USER_TOKEN` | Limited mode | - | Service token sent as `X-UserToken` |
| `MCP_DEBUG` | No | `false` | Enable debug logging |
| `DEBUG` | No | `false` | Alternative debug flag |

Set either `PARARAM_LOGIN`/`PARARAM_PASSWORD` or `PARARAM_USER_TOKEN`, not both.

### Cookie Storage

In full mode, the MCP server automatically manages authentication sessions using a cookie file
stored in the per-user data directory:

```
Linux:   ~/.local/share/pararam-nexus-mcp/cookies.json
macOS:   ~/Library/Application Support/pararam-nexus-mcp/cookies.json
Windows: %LOCALAPPDATA%\pararam-nexus-mcp\cookies.json
```

The directory is created with `0700` and the file with `0600` permissions. Override the location
with `PARARAM_COOKIE_FILE` (absolute path). This file is created and maintained automatically — you
don't need to manage it. Limited mode does not use cookie storage.

**Security Note:** This file contains sensitive session data. Keep it secure and don't commit it to version control.

## Development Setup

If you want to contribute or develop the project:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pararam-nexus-mcp
uv sync --dev
```

This will:
- Create a virtual environment
- Install all required dependencies
- Install development dependencies (linters, type checkers, test tools)

### 2. Configure Local Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials.

### 3. Install Pre-commit Hooks

```bash
uv run pre-commit install
```

This will automatically run linters and formatters before each commit.

### 4. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/pararam_nexus_mcp --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 5. Run Linters

```bash
# Check code style
uv run ruff check src/

# Format code
uv run ruff format src/

# Type checking
uv run mypy src/pararam_nexus_mcp
```

### 6. Debug Mode

Enable debug mode for detailed logging:

```bash
# Via environment variable
MCP_DEBUG=true uv run pararam-nexus-mcp

# Or in .env file
echo "MCP_DEBUG=true" >> .env
uv run pararam-nexus-mcp
```

In debug mode, you'll see:
- Detailed HTTP requests and responses
- Authentication flow details
- Full error tracebacks
- API call details

## Troubleshooting

### Authentication Fails

**Problem:** Server fails to authenticate with pararam.io

**Solutions:**
1. Verify your credentials in `.env` are correct
2. If you have 2FA enabled, ensure `PARARAM_2FA_KEY` is set correctly
3. Try deleting `~/.pararam_cookies.json` to force re-authentication
4. Enable debug mode to see detailed authentication logs

### Module Not Found Errors

**Problem:** Import errors when running the server

**Solutions:**
1. For normal usage, run the package with `uvx pararam-nexus-mcp`
2. For local development, ensure dependencies are installed: `uv sync`
3. For local development commands, use `uv run`
4. Check Python version: `python --version` (must be 3.11+)

### Claude Desktop Can't Find MCP Server

**Problem:** MCP tools don't appear in Claude Desktop

**Solutions:**
1. Verify `claude_desktop_config.json` uses `"command": "uvx"` and `"args": ["pararam-nexus-mcp"]`
2. Ensure environment variables are set in the config file
3. Check Claude Desktop logs for errors:
   - macOS: `~/Library/Logs/Claude/mcp*.log`
   - Windows: `%APPDATA%\Claude\logs\mcp*.log`
4. Restart Claude Desktop after config changes

### Connection Errors

**Problem:** Network or connection errors

**Solutions:**
1. Check your internet connection
2. Verify pararam.io is accessible
3. Check if you're behind a proxy (may need proxy configuration)
4. Try with debug mode enabled to see detailed error messages

### Cookie Expiration

**Problem:** Session expires frequently

**Solutions:**
1. The server automatically re-authenticates when sessions expire
2. If problems persist, delete `~/.pararam_cookies.json` and restart
3. Check if pararam.io has rate limiting or session policies

## Uninstallation

To completely remove Pararam Nexus MCP:

### 1. Remove from Claude Desktop

Edit `claude_desktop_config.json` and remove the `pararam-nexus` entry.

### 2. Delete Project Files

```bash
rm -rf /path/to/pararam-nexus-mcp
```

### 3. Delete Cookie Storage

```bash
rm ~/.pararam_cookies.json
```

## Next Steps

- Read the [Tools Documentation](TOOLS.md) to learn about available tools
- Check the [Development Guide](DEVELOPMENT.md) for contribution guidelines
- Review the [API Reference](API.md) for technical details
