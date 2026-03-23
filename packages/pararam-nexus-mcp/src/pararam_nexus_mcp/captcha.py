"""CAPTCHA handling for Pararam.io authentication."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CaptchaHandler:
    """Handle CAPTCHA challenges during authentication."""

    def __init__(self) -> None:
        """Initialize CAPTCHA handler."""
        self._captcha_callback: Any = None

    async def handle_captcha(self, captcha_data: dict[str, Any]) -> str:
        """
        Handle CAPTCHA challenge.

        This method should be called when pararam.io requests CAPTCHA verification.
        In a real implementation, this could:
        1. Save the CAPTCHA image to a file
        2. Use an MCP resource to show it to the user
        3. Wait for user input
        4. Return the CAPTCHA solution

        Args:
            captcha_data: CAPTCHA challenge data from pararam.io

        Returns:
            CAPTCHA solution provided by user

        Raises:
            RuntimeError: If CAPTCHA cannot be solved
        """
        logger.warning('CAPTCHA challenge received')

        captcha_type = captcha_data.get('type', 'unknown')
        captcha_id = captcha_data.get('id', 'unknown')

        logger.info(f'CAPTCHA type: {captcha_type}, ID: {captcha_id}')

        # For now, we'll raise an error and ask the user to handle it manually
        # In a future implementation, this could integrate with MCP resources
        # to show the CAPTCHA to the user and get their response

        error_msg = (
            'CAPTCHA challenge detected. '
            'Please authenticate manually through the web interface first, '
            'then the session cookies will be saved for future use.'
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def set_callback(self, callback: Any) -> None:
        """
        Set a custom CAPTCHA callback function.

        Args:
            callback: Function that takes captcha_data and returns the solution
        """
        self._captcha_callback = callback

    async def solve(self, captcha_data: dict[str, Any]) -> str:
        """
        Solve CAPTCHA using registered callback or default handler.

        Args:
            captcha_data: CAPTCHA challenge data

        Returns:
            CAPTCHA solution
        """
        if self._captcha_callback is not None:
            result = await self._captcha_callback(captcha_data)
            return str(result)
        return await self.handle_captcha(captcha_data)


# Global CAPTCHA handler instance
captcha_handler = CaptchaHandler()
