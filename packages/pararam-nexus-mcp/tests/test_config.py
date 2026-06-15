"""Tests for cookie-storage configuration."""

import os
from pathlib import Path

import platformdirs

from pararam_nexus_mcp.config import Config, _default_cookie_file


def test_default_cookie_file_is_in_user_data_dir() -> None:
    """The default cookie path lives under the per-user data directory, not the CWD."""
    default = _default_cookie_file()
    expected_dir = Path(platformdirs.user_data_dir('pararam-nexus-mcp', appauthor=False))
    assert default == expected_dir / 'cookies.json'
    assert default.is_absolute()


def test_prepare_cookie_storage_creates_private_directory(tmp_path: Path) -> None:
    """prepare_cookie_storage creates the parent directory and returns the resolved path."""
    target = tmp_path / 'nested' / 'cookies.json'
    config = Config(pararam_login='user', pararam_password='secret', pararam_cookie_file=target)

    resolved = config.prepare_cookie_storage()

    assert resolved == target
    assert target.parent.is_dir()
    if os.name == 'posix':
        assert (target.parent.stat().st_mode & 0o777) == 0o700


def test_prepare_cookie_storage_tightens_existing_file_permissions(tmp_path: Path) -> None:
    """An existing cookie file is tightened to owner-only read/write."""
    target = tmp_path / 'cookies.json'
    target.write_text('{"cookies": []}', encoding='utf-8')
    target.chmod(0o644)
    config = Config(pararam_login='user', pararam_password='secret', pararam_cookie_file=target)

    config.prepare_cookie_storage()

    if os.name == 'posix':
        assert (target.stat().st_mode & 0o777) == 0o600
