"""Channel manager — bridges pararam.io bot webhooks to Claude Code channel notifications."""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

from mcp.server.session import ServerSession
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCNotification
from pararamio_bot import WebhookMessage, WebhookServer

from pararam_nexus_mcp.config import config

logger = logging.getLogger(__name__)

CHANNEL_NOTIFICATION_METHOD = 'notifications/claude/channel'


@dataclass
class ChannelStats:
    """Runtime statistics for the channel."""

    events_received: int = 0
    events_forwarded: int = 0
    events_filtered: int = 0


@dataclass
class ChannelManager:
    """Manages webhook server and pushes events as MCP channel notifications.

    Architecture:
        WebhookServer (aiohttp) → asyncio.Queue → consumer task → session._write_stream
    """

    _pre_exec_process: asyncio.subprocess.Process | None = field(default=None, repr=False)
    _webhook_server: WebhookServer | None = field(default=None, repr=False)
    _queue: asyncio.Queue[WebhookMessage] = field(default_factory=asyncio.Queue, repr=False)
    _consumer_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _session: ServerSession | None = field(default=None, repr=False)
    _session_write_stream: Any = field(default=None, repr=False)
    _active: bool = field(default=False)
    _stats: ChannelStats = field(default_factory=ChannelStats)

    @property
    def is_active(self) -> bool:
        """Whether the channel is currently active."""
        return self._active

    @property
    def stats(self) -> ChannelStats:
        """Runtime statistics."""
        return self._stats

    @property
    def whitelisted_users(self) -> list[str]:
        """Currently whitelisted user unique_names."""
        return config.whitelisted_users_list

    async def start(self, session: object) -> None:
        """Start the webhook server and notification consumer.

        Args:
            session: MCP ServerSession instance (used to access _write_stream)
        """
        if self._active:
            logger.warning('Channel already active')
            return

        if not config.pararam_bot_secret:
            raise ValueError('PARARAM_BOT_SECRET is required to activate the channel')

        self._session = session  # type: ignore[assignment]
        self._session_write_stream = getattr(session, '_write_stream', None)
        if self._session_write_stream is None:
            raise RuntimeError('Cannot access session write stream')

        # Run pre-exec command (e.g. rathole tunnel)
        if config.pararam_channel_pre_exec:
            await self._start_pre_exec(config.pararam_channel_pre_exec)

        # Start webhook HTTP server
        self._webhook_server = WebhookServer(
            bot_secret=config.pararam_bot_secret,
            host=config.pararam_channel_host,
            port=config.pararam_channel_port,
        )
        self._webhook_server.on_message(self._on_webhook_message)
        await self._webhook_server.start()

        # Start consumer task
        self._consumer_task = asyncio.create_task(self._consume_events())
        self._active = True

        logger.info(
            'Channel activated on %s:%d, whitelisted users: %s',
            config.pararam_channel_host,
            config.pararam_channel_port,
            config.whitelisted_users_list or '(all)',
        )

    async def stop(self) -> None:
        """Stop the webhook server and consumer task."""
        if not self._active:
            return

        self._active = False

        if self._consumer_task is not None:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
            self._consumer_task = None

        if self._webhook_server is not None:
            await self._webhook_server.stop()
            self._webhook_server = None

        await self._stop_pre_exec()

        self._session = None
        self._session_write_stream = None
        logger.info('Channel deactivated')

    async def _start_pre_exec(self, command: str) -> None:
        """Start the pre-exec subprocess (e.g. rathole tunnel)."""
        logger.info('Starting pre-exec: %s', command)
        self._pre_exec_process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Give the process a moment to start and check it didn't exit immediately
        await asyncio.sleep(0.5)
        if self._pre_exec_process.returncode is not None:
            stderr = b''
            if self._pre_exec_process.stderr:
                stderr = await self._pre_exec_process.stderr.read()
            raise RuntimeError(
                f'Pre-exec command exited with code {self._pre_exec_process.returncode}: '
                f'{stderr.decode().strip()}'
            )
        logger.info('Pre-exec started (pid=%d)', self._pre_exec_process.pid)

    async def _stop_pre_exec(self) -> None:
        """Stop the pre-exec subprocess."""
        if self._pre_exec_process is None:
            return
        if self._pre_exec_process.returncode is not None:
            logger.debug('Pre-exec already exited (code=%d)', self._pre_exec_process.returncode)
            self._pre_exec_process = None
            return

        logger.info('Stopping pre-exec (pid=%d)', self._pre_exec_process.pid)
        self._pre_exec_process.terminate()
        try:
            await asyncio.wait_for(self._pre_exec_process.wait(), timeout=5.0)
        except TimeoutError:
            logger.warning('Pre-exec did not exit in time, killing')
            self._pre_exec_process.kill()
            await self._pre_exec_process.wait()
        self._pre_exec_process = None

    async def _on_webhook_message(self, message: WebhookMessage) -> str | None:
        """Callback from WebhookServer — puts message into queue and returns reply for webhook response."""
        self._stats.events_received += 1

        # Filter by whitelisted users (empty list = allow all)
        if self.whitelisted_users and message.user_unique_name not in self.whitelisted_users:
            self._stats.events_filtered += 1
            logger.debug('Filtered message from non-whitelisted user: %s', message.user_unique_name)
            return f'@{message.user_unique_name} not authorized'

        await self._queue.put(message)
        return None

    async def _consume_events(self) -> None:
        """Consumer task — reads queue and sends MCP channel notifications."""
        while True:
            message = await self._queue.get()
            await self._send_channel_notification(message)
            self._stats.events_forwarded += 1

    async def _send_channel_notification(self, event: WebhookMessage) -> None:
        """Send a notifications/claude/channel to Claude Code via MCP session."""
        content_parts = [f'New message from @{event.user_unique_name} in chat #{event.chat_id}:']
        if event.reply_no is not None:
            content_parts.append(f'(reply to #{event.reply_no})')
        content_parts.append(f'\n{event.text}')
        if event.file_name:
            content_parts.append(f'\n[Attachment: {event.file_name}]')

        content = ' '.join(content_parts)

        meta: dict[str, object] = {
            'source': 'pararam.io',
            'user_id': event.user_id,
            'user_unique_name': event.user_unique_name,
            'chat_id': event.chat_id,
            'post_no': event.post_no,
        }
        if event.reply_no is not None:
            meta['reply_no'] = event.reply_no

        notification = JSONRPCNotification(
            jsonrpc='2.0',
            method=CHANNEL_NOTIFICATION_METHOD,
            params={'content': content, 'meta': meta},
        )
        session_msg = SessionMessage(message=JSONRPCMessage(notification))

        try:
            # Send as channel notification
            await self._session_write_stream.send(session_msg)
            # Also send as MCP log message (visible in Claude Code)
            if self._session is not None:
                await self._session.send_log_message(level='info', data=content, logger='pararam-channel')
        except Exception as e:  # COMMENT: Top-level handler — write stream errors should not crash the consumer
            logger.error('Failed to send channel notification: %s', e)


# Global singleton
channel_manager = ChannelManager()
