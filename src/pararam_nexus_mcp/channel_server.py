#!/usr/bin/env python3
"""Standalone Claude Code channel server for pararam.io bot webhooks.

This is a separate MCP server that only handles channel notifications.
It's loaded via --dangerously-load-development-channels, not as a regular MCP server.
"""

import asyncio
import logging
import os
import sys

import httpx
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCNotification
from pararamio_bot import WebhookMessage, WebhookServer
from pararamio_bot.signature import extract_api_key

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger('pararam-channel')

BOT_SECRET = os.environ.get('PARARAM_BOT_SECRET', '')
BOT_API_KEY = extract_api_key(BOT_SECRET) if BOT_SECRET else ''
CHANNEL_HOST = os.environ.get('PARARAM_CHANNEL_HOST', '127.0.0.1')
CHANNEL_PORT = int(os.environ.get('PARARAM_CHANNEL_PORT', '8443'))
WHITELISTED = os.environ.get('PARARAM_WHITELISTED_USERS', '')
WHITELISTED_SET = {u.strip() for u in WHITELISTED.split(',') if u.strip()} if WHITELISTED else set()
IGNORED_USER_IDS = {int(x) for x in os.environ.get('PARARAM_IGNORED_USER_IDS', '').split(',') if x.strip()}
PARARAM_API_BASE = os.environ.get('PARARAM_API_BASE', 'https://api.pararam.io')

# Track post_nos sent by us to avoid echo
_sent_post_nos: set[tuple[int, int]] = set()  # (chat_id, post_no)

# Create MCP server with channel + tools capabilities
mcp = Server(
    name='pararam-channel',
    version='0.1.0',
    instructions=(
        'Messages from pararam.io arrive as <channel source="pararam-channel" ...>. '
        'Each message includes user_unique_name, chat_id, and post_no in attributes. '
        'To reply, use the pararam_channel_reply tool with chat_id and text. '
        'You can also reply to a specific message by providing reply_no.'
    ),
)


# --- Reply tool ---

@mcp.list_tools()  # type: ignore[misc]
async def list_tools() -> list[dict[str, object]]:
    """List available tools."""
    return [
        {
            'name': 'pararam_channel_reply',
            'description': 'Reply to a message in pararam.io chat via the bot',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'chat_id': {'type': 'integer', 'description': 'Chat ID to reply in'},
                    'text': {'type': 'string', 'description': 'Message text to send'},
                    'reply_no': {
                        'type': 'integer',
                        'description': 'Post number to reply to (optional)',
                    },
                },
                'required': ['chat_id', 'text'],
            },
        }
    ]


@mcp.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, object]) -> list[dict[str, str]]:
    """Handle tool calls."""
    if name != 'pararam_channel_reply':
        raise ValueError(f'Unknown tool: {name}')

    chat_id = int(arguments['chat_id'])  # type: ignore[arg-type]
    text = str(arguments['text'])
    reply_no = arguments.get('reply_no')

    data: dict[str, object] = {'key': BOT_API_KEY, 'chat_id': chat_id, 'text': text}
    if reply_no is not None:
        data['reply_no'] = int(reply_no)  # type: ignore[arg-type]

    async with httpx.AsyncClient() as client:
        resp = await client.post(f'{PARARAM_API_BASE}/bot/message', json=data)
        resp.raise_for_status()

    result = resp.json()
    post_no = result.get('post_no')
    if post_no is not None:
        _sent_post_nos.add((chat_id, int(post_no)))
    logger.info('Replied in chat %d: post_no=%s', chat_id, post_no)
    return [{'type': 'text', 'text': f'Sent message to chat {chat_id}, post_no={post_no}'}]


# --- Main ---

async def main() -> None:
    """Run the channel server."""
    if not BOT_SECRET:
        logger.error('PARARAM_BOT_SECRET is required')
        sys.exit(1)

    logger.info('Starting pararam-channel server')
    logger.info(
        'Webhook: %s:%d, whitelisted: %s, ignored_ids: %s',
        CHANNEL_HOST, CHANNEL_PORT, WHITELISTED_SET or '(all)', IGNORED_USER_IDS or '(none)',
    )

    async with stdio_server() as (read_stream, write_stream):
        init_options = mcp.create_initialization_options(
            notification_options=NotificationOptions(),
            experimental_capabilities={'claude/channel': {}},
        )

        # Start MCP session in background
        session_task = asyncio.create_task(
            mcp.run(read_stream, write_stream, init_options)
        )

        # Wait a moment for session to initialize
        await asyncio.sleep(0.5)

        async def on_message(message: WebhookMessage) -> str | None:
            """Handle incoming webhook message."""
            # Skip messages from ignored users (e.g. the bot itself)
            if message.user_id in IGNORED_USER_IDS:
                logger.debug('Ignored message from user_id=%d', message.user_id)
                return None

            # Skip echo — messages we sent ourselves via reply tool or send_message
            key = (message.chat_id, message.post_no)
            if key in _sent_post_nos:
                _sent_post_nos.discard(key)
                logger.debug('Skipped echo: chat=%d post=%d', message.chat_id, message.post_no)
                return None

            # Filter by whitelisted users
            if WHITELISTED_SET and message.user_unique_name not in WHITELISTED_SET:
                logger.info('Filtered: %s', message.user_unique_name)
                return f'@{message.user_unique_name} not authorized'

            content_parts = [f'Message from @{message.user_unique_name} in chat #{message.chat_id}:']
            if message.reply_no is not None and message.reply_text:
                content_parts.append(f'(replying to #{message.reply_no}: "{message.reply_text}")')
            content_parts.append(message.text)
            if message.file_name:
                content_parts.append(f'[Attachment: {message.file_name}]')
            content = '\n'.join(content_parts)

            meta: dict[str, str] = {
                'user_unique_name': message.user_unique_name,
                'chat_id': str(message.chat_id),
                'post_no': str(message.post_no),
                'user_id': str(message.user_id),
            }
            if message.reply_no is not None:
                meta['reply_no'] = str(message.reply_no)

            notification = JSONRPCNotification(
                jsonrpc='2.0',
                method='notifications/claude/channel',
                params={'content': content, 'meta': meta},
            )
            session_msg = SessionMessage(message=JSONRPCMessage(notification))
            await write_stream.send(session_msg)
            logger.info('Sent channel notification: %s', content[:80])
            return None

        # Start webhook server
        webhook = WebhookServer(
            bot_secret=BOT_SECRET,
            host=CHANNEL_HOST,
            port=CHANNEL_PORT,
        )
        webhook.on_message(on_message)
        await webhook.start()
        logger.info('Webhook server started on %s:%d', CHANNEL_HOST, CHANNEL_PORT)

        # Wait for MCP session to end
        await session_task


if __name__ == '__main__':
    asyncio.run(main())
