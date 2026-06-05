"""Tests für BlitztextConfig — Lesen, Schreiben, Defaults, API-Key-Handling."""
import json
import os
import pytest
from pathlib import Path
from app.config import BlitztextConfig


@pytest.fixture
def config_dir(tmp_path):
    return tmp_path / ".config" / "blitztext-linux"


@pytest.fixture
def config(config_dir):
    return BlitztextConfig(config_dir=config_dir)


class TestDefaults:
    def test_default_model(self, config):
        assert config.model == "base"

    def test_default_language(self, config):
        assert config.language == "de"

    def test_default_backend(self, config):
        assert config.backend == "openai-whisper"

    def test_default_hotkey_mode(self, config):
        assert config.hotkey_mode in ("toggle", "hold")

    def test_default_api_key_empty(self, config):
        assert config.openai_api_key == ""

    def test_default_autopaste(self, config):
        assert config.autopaste is True


class TestPersistence:
    def test_save_creates_file(self, config, config_dir):
        config.save()
        assert (config_dir / "config.json").exists()

    def test_save_load_roundtrip(self, config, config_dir):
        config.model = "small"
        config.language = "en"
        config.save()
        loaded = BlitztextConfig(config_dir=config_dir)
        assert loaded.model == "small"
        assert loaded.language == "en"

    def test_config_file_permissions(self, config, config_dir):
        config.save()
        cfg_file = config_dir / "config.json"
        mode = oct(cfg_file.stat().st_mode)[-3:]
        assert mode == "600", f"Expected 600, got {mode}"

    def test_partial_config_fills_defaults(self, config_dir):
        config_dir.mkdir(parents=True, exist_ok=True)
        partial = {"model": "tiny"}
        (config_dir / "config.json").write_text(json.dumps(partial))
        loaded = BlitztextConfig(config_dir=config_dir)
        assert loaded.model == "tiny"
        assert loaded.language == "de"  # default


class TestWorkflowConfig:
    def test_text_improver_tone_default(self, config):
        assert config.workflows["text_improver_tone"] == "neutral"

    def test_emoji_density_default(self, config):
        assert config.workflows["emoji_density"] == "mittel"

    def test_custom_dampf_prompt_default_empty(self, config):
        assert config.workflows["dampf_system_prompt"] == ""


class TestAPIKeyHandling:
    def test_has_api_key_false_when_empty(self, config):
        config.openai_api_key = ""
        assert config.has_api_key() is False

    def test_has_api_key_true_when_set(self, config):
        config.openai_api_key = "sk-abc123"
        assert config.has_api_key() is True

    def test_api_key_not_logged(self, config, capsys, config_dir):
        """API-Key darf nie in stdout/stderr landen."""
        config.openai_api_key = "sk-secret-do-not-log"
        config.save()
        loaded = BlitztextConfig(config_dir=config_dir)
        captured = capsys.readouterr()
        assert "sk-secret-do-not-log" not in captured.out
        assert "sk-secret-do-not-log" not in captured.err
