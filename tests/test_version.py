"""Tests für die zentrale App-Versionsquelle.

Prüft, dass ``app.__version__`` definiert und semver-förmig ist und mit dem
obersten Changelog-Header in ``CLAUDE.md`` übereinstimmt (Drift-Guard).

Die optische Versionszeile im „Allgemein"-Tab des Einstellungen-Dialogs wird
nicht automatisiert getestet: ein voller ``SettingsDialog`` unter
``QT_QPA_PLATFORM=offscreen`` bricht beim Qt-Teardown (Python 3.14) mit SIGABRT
ab. Die Anzeige wird daher manuell/visuell verifiziert (siehe Handover).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import __version__

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_version_is_defined_and_semver() -> None:
    assert isinstance(__version__, str)
    assert SEMVER.match(__version__), f"unerwartetes Versionsformat: {__version__!r}"


def test_version_matches_claude_changelog() -> None:
    """__version__ entspricht dem obersten ``## Changelog vX.Y.Z`` in CLAUDE.md."""
    claude_md = Path(__file__).resolve().parents[1] / "CLAUDE.md"
    if not claude_md.exists():
        pytest.skip("CLAUDE.md nicht vorhanden")
    text = claude_md.read_text(encoding="utf-8")
    match = re.search(r"^## Changelog v(\d+\.\d+\.\d+)", text, re.MULTILINE)
    assert match, "kein Changelog-Header in CLAUDE.md gefunden"
    assert match.group(1) == __version__, (
        f"Version-Drift: __version__={__version__} vs. CLAUDE.md v{match.group(1)}"
    )
