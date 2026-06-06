"""PasteService for BlitztextLinux.

Kopiert/extrahiert aus whisper-dictation scripts/dictate_toggle.py v0.2.19.

Zwei Schritte:
  1. wl-copy  -- Text in Wayland-Clipboard schreiben
  2. ydotool  -- Ctrl+V simulieren (nur wenn autopaste=True)

Fuer LLM-Workflows (text_improver, dampf_ablassen, emoji_text) wird
der rewritten Text eingefuegt, nicht das rohe Transkript.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import Optional

logger = logging.getLogger("blitztext.paste_service")

# Verzoegerung zwischen wl-copy und ydotool key (identisch zu whisper-dictation)
_PASTE_DELAY = 0.15
# ydotool key-delay in ms (identisch zu whisper-dictation)
_KEY_DELAY_MS = 80
# Subprocess-Timeouts: verhindern, dass ein haengendes wl-copy/ydotool den
# Transkriptions-Worker dauerhaft blockiert (sonst bleibt der App-State auf
# TRANSCRIBING/LLM_REWRITING haengen und kein neuer Hotkey-Toggle ist moeglich).
_WL_COPY_TIMEOUT = 5.0
_YDOTOOL_TIMEOUT = 5.0


class PasteServiceError(Exception):
    """Raised when clipboard write or key injection fails hard."""


class PasteService:
    """Schreibt Text ins Wayland-Clipboard und fuehrt optional Auto-Paste durch.

    Beispiel:
        svc = PasteService(autopaste=True)
        svc.paste("Hallo Welt")
    """

    def __init__(self, autopaste: bool = True) -> None:
        """
        Args:
            autopaste: True = nach wl-copy automatisch Ctrl+V via ydotool senden.
        """
        self.autopaste = autopaste

    def paste(self, text: str) -> None:
        """Text ins Clipboard schreiben und optional einfuegen.

        Args:
            text: Der einzufuegende Text.

        Raises:
            PasteServiceError: Wenn wl-copy nicht gefunden oder hart fehlschlaegt.
        """
        if not text or not text.strip():
            logger.debug("paste() mit leerem Text aufgerufen, uebersprungen.")
            return

        self._wl_copy(text)

        if self.autopaste:
            self._ydotool_paste()

    def clipboard_only(self, text: str) -> None:
        """Nur wl-copy, kein ydotool -- fuer Faelle wo Auto-Paste unterwuenscht."""
        if not text or not text.strip():
            return
        self._wl_copy(text)

    # ------------------------------------------------------------------
    # Interne Methoden
    # ------------------------------------------------------------------

    def _wl_copy(self, text: str) -> None:
        if shutil.which("wl-copy") is None:
            raise PasteServiceError(
                "wl-copy nicht gefunden. Bitte installieren: sudo apt install wl-clipboard"
            )
        try:
            subprocess.run(
                ["wl-copy"],
                input=text.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=_WL_COPY_TIMEOUT,
            )
            logger.debug("wl-copy: %d Zeichen ins Clipboard geschrieben.", len(text))
        except subprocess.TimeoutExpired as exc:
            raise PasteServiceError(
                f"wl-copy reagierte nicht innerhalb von {_WL_COPY_TIMEOUT:.0f}s"
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace").strip() if exc.stderr else ""
            raise PasteServiceError(f"wl-copy fehlgeschlagen: {stderr}") from exc

    def _ydotool_paste(self) -> None:
        if shutil.which("ydotool") is None:
            logger.warning(
                "ydotool nicht gefunden -- Auto-Paste uebersprungen. "
                "Installieren: sudo apt install ydotool"
            )
            return
        # Kurze Pause damit Clipboard-Inhalt sicher verfuegbar ist
        time.sleep(_PASTE_DELAY)
        try:
            result = subprocess.run(
                ["ydotool", "key", "--key-delay", str(_KEY_DELAY_MS), "ctrl+v"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=_YDOTOOL_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            # Nicht fatal -- Clipboard-Inhalt ist bereits gesetzt. Wichtig: nicht
            # blockieren, damit der Worker zurueckkehrt und der State auf IDLE faellt.
            logger.warning(
                "ydotool Ctrl+V Timeout nach %.0fs -- Auto-Paste uebersprungen "
                "(Text liegt bereits im Clipboard).",
                _YDOTOOL_TIMEOUT,
            )
            return
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip() if result.stderr else ""
            # Nicht fatal -- Clipboard-Inhalt ist bereits gesetzt
            logger.warning("ydotool Ctrl+V fehlgeschlagen (rc=%d): %s", result.returncode, stderr)


def check_dependencies() -> list[str]:
    """Gibt eine Liste fehlender System-Abhaengigkeiten zurueck.

    Verwendet von install.sh-Verifikation und Einstellungs-Dialog.
    """
    missing = []
    if shutil.which("wl-copy") is None:
        missing.append("wl-clipboard (wl-copy fehlt)")
    if shutil.which("ydotool") is None:
        missing.append("ydotool")
    return missing
