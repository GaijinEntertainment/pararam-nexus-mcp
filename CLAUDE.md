# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --dev

# Lint and format
uv run ruff check --fix packages/
uv run ruff format packages/

# Type checking
uv run mypy packages/pararam-nexus-mcp/src/pararam_nexus_mcp

# Run all tests
uv run pytest

# Run a single test
uv run pytest packages/pararam-nexus-mcp/tests/test_foo.py::test_bar -v

# Run the MCP server locally
uv run pararam-nexus-mcp

# Run the channel server locally
uv run pararam-nexus-channel

# Build packages
uv build --package pararam-nexus-mcp
uv build --package pararam-nexus-channel

# Interactive MCP inspector (loads .env automatically)
./inspector.sh

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Architecture

UV workspace monorepo with two independent PyPI packages. Python 3.14+, fully async.

### Package: pararam-nexus-mcp (`packages/pararam-nexus-mcp/`)

FastMCP server providing tools for pararam.io (messaging/collaboration platform).

**Entry point:** `server.py` creates FastMCP instance, registers tools from three modules, runs server on stdio transport.

**Client:** `client.py` — singleton `PararamClient` wrapping `AsyncPararamio`. In **full** mode it uses cookie-based session persistence + optional TOTP 2FA; in **limited** mode it passes `user_token=` through to `AsyncPararamio` and the cookie manager is never created.

**Config:** `config.py` — Pydantic BaseSettings loading from `.env`. Either set `PARARAM_LOGIN`/`PARARAM_PASSWORD` (+ optional `PARARAM_2FA_KEY`/`PARARAM_COOKIE_FILE`) for full mode, **or** set `PARARAM_USER_TOKEN` for limited mode. The two sets are mutually exclusive; `Config.validate_credentials()` enforces XOR.

**Modes:**
- `full` (default) — every registered tool is available.
- `limited` (set when `PARARAM_USER_TOKEN` is present) — the server prunes its tool list to the allow-list defined as `LIMITED_MODE_TOOLS` in `server.py`. User tools (`users.py`) aren't registered at all in limited mode.

**Tools** (in `tools/`):
- `posts.py` — message search, send, thread building, file upload/download, plus limited-mode tools `get_reply_thread`, `get_replies_to_post`, `edit_post`, `delete_post` (12 tools)
- `chats.py` — chat search/get + create variants (`create_private_chat`, `create_group_chat`, `create_thread_chat`) (5 tools)
- `users.py` — user search, info, team status (3 tools, full mode only)

Each tool module exports a `register_*_tools(mcp)` function. Tools use `@mcp.tool()` decorator, return `ToolResponse[T]` (generic wrapper with success/message/error/payload).

### Package: pararam-nexus-channel (`packages/pararam-nexus-channel/`)

Standalone Claude Code channel server for pararam.io bot webhooks. Receives messages via bot webhook and pushes them as MCP channel notifications.

**Entry point:** `server.py` — low-level MCP server with webhook listener, env-based config.

**Config:** Environment variables only (`PARARAM_BOT_SECRET`, `PARARAM_CHANNEL_HOST`, `PARARAM_CHANNEL_PORT`, `PARARAM_WHITELISTED_USERS`, `PARARAM_IGNORED_USER_IDS`).

## Code Style

- Ruff with strict rules, 120 char line length, single quotes
- MyPy strict mode
- Catch specific exceptions only — never bare `except Exception:` without a comment explaining why
- All imports at module top level, never inside functions
- All tool functions must have full docstrings with Args/Returns
- English only in code and documentation
