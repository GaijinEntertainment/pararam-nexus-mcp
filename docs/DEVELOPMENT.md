# Development Guide

Guide for developers who want to contribute to or extend Pararam Nexus MCP.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Adding New Tools](#adding-new-tools)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Debugging](#debugging)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js (for MCP Inspector)

### Initial Setup

1. **Clone and install dependencies:**

```bash
git clone <repository-url>
cd pararam-nexus-mcp
uv sync --dev
```

2. **Set up pre-commit hooks:**

```bash
uv run pre-commit install
```

This will automatically run linters and formatters on every commit.

3. **Configure environment:**

Create `.env` file with your credentials:

```env
PARARAM_LOGIN=your_email@example.com
PARARAM_PASSWORD=your_password
PARARAM_2FA_KEY=your_2fa_key  # Optional
MCP_DEBUG=true  # Enable debug mode for development
```

### MCP Inspector

MCP Inspector is a development tool for testing and debugging MCP servers interactively.

**Start the inspector:**

```bash
./inspector.sh
```

This will:
1. Load environment variables from `.env`
2. Start the MCP server
3. Open MCP Inspector in your browser
4. Allow you to test tools interactively

**Manual start:**

```bash
npx @modelcontextprotocol/inspector uv run pararam-nexus-mcp
```

## Project Structure

```
pararam-nexus-mcp/
├── src/
│   └── pararam_nexus_mcp/
│       ├── __init__.py           # Package initialization
│       ├── server.py             # Main server entry point
│       ├── client.py             # Pararam.io client wrapper
│       ├── config.py             # Configuration management
│       └── tools/                # Tool implementations
│           ├── __init__.py
│           ├── messages.py       # Message and file tools
│           └── users.py          # User tools
├── tests/                        # Test files
├── docs/                         # Documentation
├── pyproject.toml               # Project configuration
├── uv.lock                      # Dependency lock file
├── inspector.sh                 # MCP Inspector launcher
└── README.md                    # Project readme

```

### Key Files

**`src/pararam_nexus_mcp/server.py`**
- Main entry point
- Initializes FastMCP server
- Registers all tools
- Handles server lifecycle

**`src/pararam_nexus_mcp/client.py`**
- Wraps `pararamio-aio` client
- Handles authentication
- Manages cookie storage
- Provides singleton access

**`src/pararam_nexus_mcp/config.py`**
- Loads environment variables
- Validates configuration
- Provides centralized config access

**`src/pararam_nexus_mcp/tools/messages.py`**
- Message operations (search, get, send)
- File operations (upload, download)
- Chat operations (search, threads)

**`src/pararam_nexus_mcp/tools/users.py`**
- User operations (search, info, team status)

## Adding New Tools

### 1. Create Tool Function

Tools are created using the `@mcp.tool()` decorator:

```python
from fastmcp import FastMCP

def register_my_tools(mcp: FastMCP[None]) -> None:
    """Register my tools with the MCP server."""

    @mcp.tool()
    async def my_new_tool(
        param1: str,
        param2: int = 10,
    ) -> str:
        """
        Brief description of what the tool does.

        Args:
            param1: Description of param1
            param2: Description of param2 (default: 10)

        Returns:
            JSON string with result data
        """
        try:
            client = await get_client()

            # Your implementation here
            result = await client.client.some_operation(param1, param2)

            return json.dumps({
                'success': True,
                'data': result,
            }, indent=2)

        except PararamioAuthenticationError as e:
            logger.error('Authentication failed: %s', e)
            return f'Authentication error: {e!s}'
        except PararamioHTTPRequestError as e:
            logger.error('HTTP request failed: %s', e)
            return f'Request error: {e!s}'
        except (PararamioValidationError, PararamioRequestError) as e:
            logger.error('API error: %s', e)
            return f'API error: {e!s}'
        except httpx.HTTPError as e:
            logger.error('Network error: %s', e)
            return f'Network error: {e!s}'
```

### 2. Best Practices

**Type Annotations:**
- Always use type hints for parameters and return types
- Use `str | None` for optional parameters
- Return `str` for JSON responses, `Image` for images

**Error Handling:**
- Catch specific exceptions from `pararamio_aio._core`
- Never use bare `except Exception:` without a comment explaining why
- Always log errors before returning
- Return user-friendly error messages

**Documentation:**
- Write clear docstrings with Args and Returns sections
- Document default values
- Explain the format of returned data

**Return Format:**
- Return JSON strings using `json.dumps(data, indent=2)`
- Use consistent structure: `{'success': bool, 'data': ...}` or direct data
- For images, return `Image` objects
- For errors, return plain text strings starting with error type

### 3. Register Tool

Add your tool registration to `server.py`:

```python
from pararam_nexus_mcp.tools.my_tools import register_my_tools

# In main():
register_message_tools(mcp)
register_user_tools(mcp)
register_my_tools(mcp)  # Add this
```

Update the log message to include your new tools:

```python
logger.info(
    'Registered tools: ..., my_new_tool'
)
```

### 4. Document Tool

Add your tool to `docs/TOOLS.md` following the existing format.

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/pararam_nexus_mcp --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py

# Run specific test
uv run pytest tests/test_client.py::test_get_client
```

### Writing Tests

Create test files in the `tests/` directory:

```python
import pytest
from pararam_nexus_mcp.client import get_client

@pytest.mark.asyncio
async def test_my_tool():
    """Test my new tool."""
    client = await get_client()

    # Test implementation
    result = await my_function()

    assert result is not None
    assert 'expected_key' in result
```

### Test Coverage

View coverage report:

```bash
uv run pytest --cov=src/pararam_nexus_mcp --cov-report=html
open htmlcov/index.html
```

Aim for >80% coverage for new code.

## Code Quality

### Linting and Formatting

The project uses `ruff` for linting and formatting:

```bash
# Check code style
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/
```

### Type Checking

The project uses `mypy` for static type checking:

```bash
# Check types
uv run mypy src/pararam_nexus_mcp

# Check specific file
uv run mypy src/pararam_nexus_mcp/tools/messages.py
```

**Type checking rules:**
- All function parameters must have type annotations
- All function return types must be annotated
- Use `str | None` for optional types
- Avoid using `Any` unless necessary

### Code Style Rules

**From `.claude/CLAUDE.md` (enforced by pre-commit):**

1. **Never use Russian** in code, comments, or documentation
2. **Exception handling**: Never use bare `except Exception:` without a comment
3. **Imports**: Always place imports at the top of the file
4. **Commit messages**: Don't add "co-authored with Claude" to commits

**Additional rules:**
- Line length: 120 characters maximum
- Use f-strings for string formatting
- Prefer `async`/`await` over callbacks
- Use descriptive variable names
- Add docstrings to all public functions

### Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

```bash
# Install hooks
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files

# Skip hooks for a single commit (not recommended)
git commit --no-verify
```

Hooks include:
- Ruff linting
- Ruff formatting
- Mypy type checking
- Trailing whitespace removal
- YAML validation

## Debugging

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Via environment
MCP_DEBUG=true uv run pararam-nexus-mcp

# Or in .env
echo "MCP_DEBUG=true" >> .env
```

In debug mode you'll see:
- Full HTTP requests and responses
- Authentication flow details
- Complete error tracebacks
- Detailed API interactions

### Logging

Use Python's logging module:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug('Detailed debug info')
logger.info('General information')
logger.warning('Warning message')
logger.error('Error occurred: %s', error)
```

### MCP Inspector

Use MCP Inspector for interactive debugging:

```bash
./inspector.sh
```

This allows you to:
- Test tools interactively
- Inspect tool parameters and responses
- Debug tool behavior in real-time
- View server logs

### Common Issues

**Import errors:**
- Always use `uv run` to execute commands
- Verify dependencies: `uv sync`

**Authentication issues:**
- Check credentials in `.env`
- Delete `~/.pararam_cookies.json` to reset session
- Enable debug mode to see auth details

**Type errors:**
- Run `uv run mypy src/pararam_nexus_mcp`
- Add missing type annotations
- Check for `None` handling

## Contributing

### Git Workflow

1. **Fork the repository**

2. **Create a feature branch:**

```bash
git checkout -b feature/my-new-feature
```

3. **Make your changes:**
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation

4. **Run quality checks:**

```bash
# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/

# Type checking
uv run mypy src/pararam_nexus_mcp

# Tests
uv run pytest
```

5. **Commit your changes:**

```bash
git add .
git commit -m "Add feature: description"
```

Pre-commit hooks will run automatically.

6. **Push to your fork:**

```bash
git push origin feature/my-new-feature
```

7. **Create a Pull Request**

### Commit Message Guidelines

Follow conventional commits format:

```
feat: add new search tool
fix: correct authentication flow
docs: update installation guide
test: add tests for user tools
refactor: improve error handling
chore: update dependencies
```

### Pull Request Guidelines

**PR Description should include:**
- What changes were made
- Why the changes were necessary
- How to test the changes
- Any breaking changes

**Before submitting:**
- All tests pass
- Code coverage doesn't decrease
- Documentation is updated
- Commit messages are clear

### Review Process

1. Automated checks must pass (linting, tests, type checking)
2. Code review by maintainer
3. Address review feedback
4. Merge when approved

## Additional Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- pararamio-aio API
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
