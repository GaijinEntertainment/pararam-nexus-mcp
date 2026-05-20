"""Tests for server module."""

from pararam_nexus_mcp import __version__
from pararam_nexus_mcp.formatting import PARARAM_FORMATTING_GUIDE, PARARAM_FORMATTING_REFERENCE


def test_version() -> None:
    """Test that version is set."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_pararam_formatting_guide_mentions_supported_markup() -> None:
    """Test that the MCP guidance documents Pararam-specific formatting."""
    assert 'Markdown headings' in PARARAM_FORMATTING_GUIDE
    assert '**bold**' in PARARAM_FORMATTING_GUIDE
    assert '[#2E7D32](●)' in PARARAM_FORMATTING_GUIDE
    assert '@all' in PARARAM_FORMATTING_GUIDE
    assert 'only when the user explicitly asks' in PARARAM_FORMATTING_GUIDE
    assert 'ask the user for explicit confirmation' in PARARAM_FORMATTING_GUIDE
    assert '[ ](task text)' in PARARAM_FORMATTING_REFERENCE
