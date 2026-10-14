"""
Unit Tests for Algorise DevEx Unified CLI
Validates consolidated status reporting and proxy routing to sub-engines.
"""

from __future__ import annotations

import io
import sys
import pytest

from devex.cli import show_platform_status


def test_show_platform_status(capsys):
    show_platform_status(root_dir=".")
    captured = capsys.readouterr()
    assert "ALGORISE AUTONOMOUS DEVEX & SRE UNIFIED PLATFORM — STATUS" in captured.out
    assert "AutoTest Sentinel" in captured.out
    assert "ContextPR" in captured.out
    assert "ModernizeAI" in captured.out
    assert "TraceRoot AI" in captured.out
    assert "Platform Engines Operational: 4 / 4" in captured.out
