# BlitztextLinux – Claude Context

Diese Datei gibt Claude Kontext über das Projekt.

## Projektübersicht

BlitztextLinux ist ein Linux-nativer Sprach-Diktierdienst (Python, PyQt5/PySide6, Whisper).
Er läuft als System-Tray-App mit globalem Hotkey, transkribiert Sprache lokal und tippt den
Text direkt in das fokussierte Fenster.

## Architektur

- `app/` – Python-Paket (Tray, Hotkey, State-Machine, Paste, History, TTS, Notify, Settings)
- `scripts/` – Hilfsskripte (Setup, Packaging)
- `systemd/` – User-Service-Unit
- `tests/` – pytest-Suite (GUI-gated via `WHISPER_GUI_TESTS=1 QT_QPA_PLATFORM=offscreen`)
- `docs/` – Screenshots und Dokumentation

## Wichtige Konventionen

### Nicht anfassen
- Hotkey-Erkennung: `KEY_LEFTALT`, `value=1` only, `value=2`/`value=0` ignoriert (`app/hotkey_service.py`)
- evdev-Debounce-Timing: `0.6s` (`DEBOUNCE_SECONDS`)
- State-Guard: Toggles während `TRANSCRIBING`/`LLM_REWRITING` werden bewusst blockiert
- Tray-Farb-Konvention: IDLE=grün, RECORDING=rot, TRANSCRIBING/LLM=orange, ERROR=grau

### Tests ausführen
```bash
.venv/bin/python -m pytest tests/
# Mit GUI-Tests:
WHISPER_GUI_TESTS=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/
```

### Branch-Strategie
- `main` – stabiler Stand, direkt nutzbar
- Feature-Branches für größere Änderungen

## Letzte bekannte Teststände

- `110 passed, 9 skipped` (ohne GUI-Tests)
- `119 passed` (mit `WHISPER_GUI_TESTS=1 QT_QPA_PLATFORM=offscreen`)
- CI auf `TimInTech/blitztext-app` grün (Python 3.11 + 3.12)

## Offene Punkte

- PR #1 (upstream `cmagnussen/blitztext-app`) ist ein automatischer GitHub-Vorschlag
  (fremder Windows-Tauri-Port) – nicht mergen
- Eigener Linux-PR zum upstream folgt später
