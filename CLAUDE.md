# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --dev

# Lint and format
uv run ruff check --fix src/
uv run ruff format src/

# Type checking
uv run mypy src/pararam_nexus_mcp

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_foo.py::test_bar -v

# Run the MCP server locally
uv run pararam-nexus-mcp

# Interactive MCP inspector (loads .env automatically)
./inspector.sh

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Architecture

FastMCP server providing tools for pararam.io (messaging/collaboration platform). Python 3.13+, fully async.

**Entry point:** `server.py` creates FastMCP instance, registers tools from three modules, runs server on stdio transport.

**Client:** `client.py` — singleton `PararamClient` wrapping `AsyncPararamio` with cookie-based session persistence and TOTP 2FA support.

**Config:** `config.py` — Pydantic BaseSettings loading from `.env`. Required: `PARARAM_LOGIN`, `PARARAM_PASSWORD`. Optional: `PARARAM_2FA_KEY`, `PARARAM_COOKIE_FILE`.

**Tools** (in `tools/`):
- `posts.py` — message search, send, thread building, file upload/download (8 tools)
- `chats.py` — chat search (1 tool)
- `users.py` — user search, info, team status (3 tools)

Each tool module exports a `register_*_tools(mcp)` function. Tools use `@mcp.tool()` decorator, return `ToolResponse[T]` (generic wrapper with success/message/error/payload).

## Code Style

- Ruff with strict rules, 120 char line length, single quotes
- MyPy strict mode
- Catch specific exceptions only — never bare `except Exception:` without a comment explaining why
- All imports at module top level, never inside functions
- All tool functions must have full docstrings with Args/Returns
- English only in code and documentation
