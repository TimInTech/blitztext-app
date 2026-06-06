"""Tests für portierte Features: Config-Felder, Diktat-Notizen, Merge,
Notifications und TTS-Verfuegbarkeit (alle GUI-frei)."""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Config
from app.history_panel import (
    save_dictation_note,
    merge_dictation_text,
    save_merged_dictation,
    _within_home,
)
from app import notify as notify_service
from app import tts_window


# ---------------------------------------------------------------------------
# Config: neue Felder
# ---------------------------------------------------------------------------

class TestConfigFeatureFields:
    def test_defaults(self, tmp_path):
        cfg = Config.load(tmp_path / "config.json")
        assert cfg.history_size == 50
        assert cfg.tts_speed == 1.0
        assert cfg.tts_voice == ""
        assert cfg.notes_folder.endswith("Blitztext-Notizen")

    def test_history_size_clamped(self, tmp_path):
        cfg = Config.load(tmp_path / "config.json")
        cfg.history_size = 5
        assert cfg.history_size == 10
        cfg.history_size = 500
        assert cfg.history_size == 100

    def test_tts_speed_clamped(self, tmp_path):
        cfg = Config.load(tmp_path / "config.json")
        cfg.tts_speed = 0.1
        assert cfg.tts_speed == 0.5
        cfg.tts_speed = 9.0
        assert cfg.tts_speed == 2.0

    def test_roundtrip_save_load(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config.load(path)
        cfg.tts_voice = "de_DE-thorsten-medium.onnx"
        cfg.notes_folder = str(Path.home() / "Notizen")
        cfg.history_size = 25
        cfg.save()
        cfg2 = Config.load(path)
        assert cfg2.tts_voice == "de_DE-thorsten-medium.onnx"
        assert cfg2.history_size == 25
        assert cfg2.notes_folder.endswith("Notizen")

    def test_sanitize_bad_values(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"history_size": "abc", "tts_speed": "x", "notes_folder": 5}')
        cfg = Config.load(path)
        assert cfg.history_size == 50
        assert cfg.tts_speed == 1.0
        assert cfg.notes_folder == ""


# ---------------------------------------------------------------------------
# Diktat-Notizen + Merge
# ---------------------------------------------------------------------------

@pytest.fixture
def home_folder():
    d = tempfile.mkdtemp(dir=str(Path.home()), prefix=".blitztext-test-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestDictationNotes:
    def test_within_home_accepts_subdir(self, home_folder):
        assert _within_home(home_folder) is not None

    def test_within_home_rejects_outside(self):
        assert _within_home("/tmp/blitztext-evil") is None

    def test_within_home_empty(self):
        assert _within_home("") is None

    def test_save_dictation_note_creates_file(self, home_folder):
        path = save_dictation_note(home_folder, "Hallo Welt")
        assert path is not None
        assert os.path.isfile(path)
        assert "Hallo Welt" in Path(path).read_text(encoding="utf-8")
        assert (os.stat(path).st_mode & 0o777) == 0o600

    def test_save_dictation_note_empty_text(self, home_folder):
        assert save_dictation_note(home_folder, "   ") is None

    def test_save_dictation_note_outside_home_rejected(self):
        assert save_dictation_note("/tmp/evil-notes", "x") is None

    def test_merge_dictation_text(self):
        assert merge_dictation_text(["a", "b", "c"]) == "a\n\nb\n\nc"

    def test_merge_skips_empty(self):
        assert merge_dictation_text(["a", "  ", "", "b"]) == "a\n\nb"

    def test_save_merged_dictation(self, home_folder):
        path = save_merged_dictation(home_folder, "Satz 1\n\nSatz 2")
        assert path is not None and os.path.isfile(path)
        content = Path(path).read_text(encoding="utf-8")
        assert "Satz 1" in content and "Satz 2" in content


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class TestNotify:
    def test_notify_no_raise_when_missing(self):
        with patch("app.notify.shutil.which", return_value=None):
            notify_service.notify("Titel", "Text")  # darf nicht werfen

    def test_is_available(self):
        with patch("app.notify.shutil.which", return_value="/usr/bin/notify-send"):
            assert notify_service.is_available() is True
        with patch("app.notify.shutil.which", return_value=None):
            assert notify_service.is_available() is False

    def test_notify_passes_timeout(self):
        with patch("app.notify.shutil.which", return_value="/usr/bin/notify-send"), \
             patch("app.notify.subprocess.run") as run_mock:
            notify_service.notify("T", "B")
            assert run_mock.call_args.kwargs.get("timeout") is not None


# ---------------------------------------------------------------------------
# TTS-Verfuegbarkeit
# ---------------------------------------------------------------------------

class TestTtsAvailability:
    def test_is_piper_available_false_when_missing(self):
        with patch("app.tts_window._find_piper", return_value=None):
            assert tts_window.is_piper_available() is False

    def test_list_voices_empty_when_no_dir(self):
        with patch.object(tts_window, "VOICES_DIR", Path("/nonexistent/piper-voices")):
            assert tts_window.list_voices() == []
