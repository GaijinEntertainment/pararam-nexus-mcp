"""Authentication helpers for 2FA."""

import logging

logger = logging.getLogger(__name__)


def get_2fa_key(stored_key: str | None) -> str | None:
    """
    Get 2FA key from config.

    Args:
        stored_key: Stored 2FA key from config (.env file)

    Returns:
        2FA key or None if not available
    """
    if stored_key:
        logger.debug('Using 2FA key from config')
        return stored_key

    logger.warning('No 2FA key configured in PARARAM_2FA_KEY environment variable')
    return None
