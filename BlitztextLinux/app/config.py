"""Config for BlitztextLinux.

Pfad: ~/.config/blitztext-linux/config.json
Berechtigungen: 0o600 (API-Key liegt im File).

Schema-Validierung bei load() -- unbekannte Keys werden ignoriert,
fehlende Keys werden mit Defaults aufgefuellt. Kein Absturz bei
beschaedigter Config -- Fallback auf Defaults.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("blitztext.config")

CONFIG_DIR = Path.home() / ".config" / "blitztext-linux"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "model": "base",
    "language": "de",
    "backend": "openai-whisper",
    "hotkey_mode": "toggle",
    "openai_api_key": "",
    "autopaste": True,
    "audio_device": "@DEFAULT_SOURCE@",
    "workflows": {
        "text_improver_tone": "neutral",
        "emoji_density": "mittel",
        "dampf_system_prompt": "",
    },
}

VALID_MODELS = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo"}
VALID_BACKENDS = {"openai-whisper", "faster-whisper"}
VALID_HOTKEY_MODES = {"toggle", "hold"}
VALID_TONES = {"formal", "neutral", "locker"}
VALID_EMOJI_DENSITIES = {"wenig", "mittel", "viel"}


class ConfigError(Exception):
    """Raised only for unrecoverable config errors (e.g. permission denied on write)."""


class Config:
    """Laedt, validiert und speichert die BlitztextLinux-Konfiguration.

    Beispiel:
        cfg = Config.load()
        cfg.openai_api_key = "sk-..."
        cfg.save()
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config":
        """Laedt Config aus Datei. Fehlende Keys werden mit Defaults ergaenzt.
        Bei beschaedigter JSON-Datei: Warnung + Defaults.
        """
        if not path.is_file():
            logger.debug("Config-Datei nicht gefunden, verwende Defaults: %s", path)
            return cls(_deep_merge(DEFAULTS, {}))

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Config-Root ist kein JSON-Objekt")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Config beschaedigt (%s), verwende Defaults: %s", exc, path)
            return cls(_deep_merge(DEFAULTS, {}))

        merged = _deep_merge(DEFAULTS, data)
        cfg = cls(merged)
        cfg._validate_and_sanitize()
        return cfg

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Speichert Config als JSON. Setzt Berechtigungen auf 0o600.

        Raises:
            ConfigError: Bei Schreibfehler.
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(path)
            path.chmod(0o600)
        except OSError as exc:
            raise ConfigError(f"Config konnte nicht gespeichert werden: {exc}") from exc

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model(self) -> str:
        return self._data["model"]

    @model.setter
    def model(self, value: str) -> None:
        if value not in VALID_MODELS:
            raise ValueError(f"Ungueltiges Modell: {value!r}. Gueltig: {sorted(VALID_MODELS)}")
        self._data["model"] = value

    @property
    def language(self) -> str:
        return self._data["language"]

    @language.setter
    def language(self, value: str) -> None:
        self._data["language"] = value

    @property
    def backend(self) -> str:
        return self._data["backend"]

    @backend.setter
    def backend(self, value: str) -> None:
        if value not in VALID_BACKENDS:
            raise ValueError(f"Ungueltiger Backend: {value!r}. Gueltig: {sorted(VALID_BACKENDS)}")
        self._data["backend"] = value

    @property
    def hotkey_mode(self) -> str:
        return self._data["hotkey_mode"]

    @hotkey_mode.setter
    def hotkey_mode(self, value: str) -> None:
        if value not in VALID_HOTKEY_MODES:
            raise ValueError(f"Ungueltiger Hotkey-Modus: {value!r}")
        self._data["hotkey_mode"] = value

    @property
    def openai_api_key(self) -> str:
        return self._data["openai_api_key"]

    @openai_api_key.setter
    def openai_api_key(self, value: str) -> None:
        self._data["openai_api_key"] = value

    @property
    def autopaste(self) -> bool:
        return bool(self._data["autopaste"])

    @autopaste.setter
    def autopaste(self, value: bool) -> None:
        self._data["autopaste"] = bool(value)

    @property
    def audio_device(self) -> str:
        return self._data["audio_device"]

    @audio_device.setter
    def audio_device(self, value: str) -> None:
        self._data["audio_device"] = value

    # Workflow-Sub-Keys
    @property
    def text_improver_tone(self) -> str:
        return self._data["workflows"]["text_improver_tone"]

    @text_improver_tone.setter
    def text_improver_tone(self, value: str) -> None:
        if value not in VALID_TONES:
            raise ValueError(f"Ungueltiger Ton: {value!r}. Gueltig: {sorted(VALID_TONES)}")
        self._data["workflows"]["text_improver_tone"] = value

    @property
    def emoji_density(self) -> str:
        return self._data["workflows"]["emoji_density"]

    @emoji_density.setter
    def emoji_density(self, value: str) -> None:
        if value not in VALID_EMOJI_DENSITIES:
            raise ValueError(f"Ungueltige Emoji-Dichte: {value!r}")
        self._data["workflows"]["emoji_density"] = value

    @property
    def dampf_system_prompt(self) -> str:
        return self._data["workflows"]["dampf_system_prompt"]

    @dampf_system_prompt.setter
    def dampf_system_prompt(self, value: str) -> None:
        self._data["workflows"]["dampf_system_prompt"] = value

    def as_dict(self) -> dict[str, Any]:
        """Gibt eine tiefe Kopie der Config-Daten zurueck."""
        import copy
        return copy.deepcopy(self._data)

    # ------------------------------------------------------------------
    # Interne Validierung
    # ------------------------------------------------------------------

    def _validate_and_sanitize(self) -> None:
        """Korrigiert ungueltige Werte auf Defaults, ohne Exception."""
        if self._data.get("model") not in VALID_MODELS:
            logger.warning("Ungueltiges model %r, setze 'base'", self._data.get("model"))
            self._data["model"] = "base"
        if self._data.get("backend") not in VALID_BACKENDS:
            logger.warning("Ungueltiger backend %r, setze 'openai-whisper'", self._data.get("backend"))
            self._data["backend"] = "openai-whisper"
        if self._data.get("hotkey_mode") not in VALID_HOTKEY_MODES:
            logger.warning("Ungueltiger hotkey_mode %r, setze 'toggle'", self._data.get("hotkey_mode"))
            self._data["hotkey_mode"] = "toggle"
        wf = self._data.get("workflows", {})
        if wf.get("text_improver_tone") not in VALID_TONES:
            wf["text_improver_tone"] = "neutral"
        if wf.get("emoji_density") not in VALID_EMOJI_DENSITIES:
            wf["emoji_density"] = "mittel"


# ------------------------------------------------------------------
# Hilfsfunktion
# ------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Merged override in base (rekursiv). base wird nicht veraendert."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result
