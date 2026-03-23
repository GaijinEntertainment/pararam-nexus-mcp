"""Tests for server module."""

from pararam_nexus_mcp import __version__


def test_version() -> None:
    """Test that version is set."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
