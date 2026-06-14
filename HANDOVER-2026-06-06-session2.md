# Handover 2026-06-06 (Session 2) – BlitztextLinux

Fortsetzung von [HANDOVER-2026-06-06.md](HANDOVER-2026-06-06.md) (evdev-Hotkey-Stabilisierung).
Diese Session: Hotkey-Hang-Bugfix, neue Komfort-Features, grafisches Hauptfenster und CI.

## Projekt

- Pfad: `/home/timintech/projects/blitztext-app/BlitztextLinux` (Unterordner; Repo-Root ist `blitztext-app`, daneben `BlitztextMac`)
- Branch: `feature/linux-port`
- Remotes: `origin` = `TimInTech/blitztext-app` (unser Fork, hierhin pushen), `upstream` = `cmagnussen/blitztext-app`
- Produktivsystem: Kubuntu / KDE Plasma / Wayland
- Laufzeit: `.venv`, PyQt6 + evdev

## Stand der Verifikation

```bash
.venv/bin/python -m pytest tests/                       # 110 passed, 9 skipped (GUI-gated)
WHISPER_GUI_TESTS=1 QT_QPA_PLATFORM=offscreen \
  .venv/bin/python -m pytest tests/                      # 119 passed (inkl. GUI offscreen)
```

GitHub Actions (TimInTech) läuft grün auf Python 3.11 + 3.12.

## Was in dieser Session passiert ist

### 1. Bugfix: Hotkey haengt nach erstem Zyklus (Icon bleibt orange, zweiter Toggle tot)

- **Root Cause:** blockierender Paste-Subprocess ohne Timeout in `app/paste_service.py`.
  - `wl-copy` forkt einen Clipboard-Daemon, der die geerbte `stderr=PIPE` offen hält →
    `subprocess.run()` wartet auf EOF → blockiert → Worker kehrt nie zurück →
    State bleibt `TRANSCRIBING`/`LLM_REWRITING` → Concurrency-Guard blockiert neue Toggles.
- **Fix:**
  - `wl-copy` mit `stdout/stderr=subprocess.DEVNULL` (statt `PIPE`) + `timeout=5s`.
  - `ydotool key` mit `timeout=5s`; Timeout ist nicht-fatal (Clipboard ist gesetzt).
- Commits: `7d04fc2` (Timeouts), `13db89a` (wl-copy DEVNULL).
- Tests: `tests/test_state_machine.py` (Paste-Timeouts, value=1/2/0-Handling, State-Reset).

### 2. Neue Features (portiert aus `~/projects/whisper-dictation`, angepasst an Tray-only)

Commit `17200ce`. Neue Module:

| Datei | Inhalt |
|---|---|
| `app/history_panel.py` | `HistoryPanel(QWidget)` Verlauf-/Diktat-Fenster + GUI-freie Helfer `save_dictation_note`, `merge_dictation_text`, `save_merged_dictation` (Notizen nur innerhalb `~`, `0o600`) |
| `app/tts_window.py` | `TtsWindow(QDialog)` Vorlesen via Piper (optional); `is_piper_available`, `list_voices` |
| `app/notify.py` | `notify()`/`is_available()` – `notify-send`-Wrapper, schlägt nie hart fehl |

- **Diktat-Modus** (Tray-Toggle): sammelt Transkripte als Diktat-Einträge, speichert je `.md`,
  „Zusammenführen" kombiniert in eine `.md` + Clipboard.
- **Verlauf**: letzte Transkripte, Kopieren/Löschen je Eintrag.
- **Vorlesen (TTS)**: Piper, Stimmen/Tempo, Pause/Fortsetzen.
- **Notifications** bei Diktat-Speicherung/Fehler.
- Config-Felder (`app/config.py`): `notes_folder`, `history_size`, `tts_voice`, `tts_speed` (inkl. Validierung); Settings-Dialog Tab „Allgemein" um Notizordner + Verlaufsgröße erweitert.

### 3. Grafisches Hauptfenster (Fallback zum Hotkey)

Commit `0422da8`. Neue Datei `app/main_window.py`:

- `MainWindow(QWidget)`: **Start/Stopp-Button**, Workflow-Auswahl (alle 5), Verwerfen,
  Aufnahme-Timer/Status, plus Diktat/Verlauf/Vorlesen/Einstellungen.
- Start/Stopp funktioniert **unabhängig vom Hotkey-Modus** via
  `BlitztextApp.gui_toggle_recording()` / `gui_discard()` (Startlogik in `_start_recording()` extrahiert).
- Tray-Eintrag „🪟 Fenster anzeigen" + Einfach-/Doppelklick aufs Tray-Icon; Fenster wird beim Start gezeigt.
- **Schließen versteckt nur** (`closeEvent` → `hide()`); App läuft im Tray weiter.
- Diktat-Modus zwischen Tray-Action und Fenster-Button synchronisiert (`set_dictation_mode`);
  Verlaufs-Zähler als Fenster-Badge.

### 4. CI (GitHub Actions)

Commits `bac73cf`, `2a993a7`. Datei `.github/workflows/blitztext-linux-ci.yml` (im Repo-Root):

- Trigger: Push (jeder Branch) + PR, nur bei Änderungen unter `BlitztextLinux/**` oder am Workflow.
- Schritte: Qt-Offscreen-Systemlibs (`libegl1 libgl1 libxkbcommon0 libdbus-1-3`) →
  `BlitztextLinux/requirements-dev.txt` → `compileall app` → volle Test-Suite inkl. GUI offscreen.
- Matrix: Python 3.11 + 3.12.
- `cache-dependency-path: BlitztextLinux/requirements-dev.txt` (sonst scheitert `cache: pip`).
- Neue Datei `BlitztextLinux/requirements-dev.txt` (PyQt6, evdev, openai, pytest).

## NICHT anfassen (Constraints)

- `scripts/dictate_toggle.py` existiert in diesem Repo NICHT (war eine andere Codebasis). Blitztext ist monolithisch.
- Debounce-Timing 0.6s (`hotkey_service.py:DEBOUNCE_SECONDS`).
- Tray-Farb-Konvention: IDLE=grün, RECORDING=rot, TRANSCRIBING/LLM=orange, ERROR=grau.
- State-Guard (neue Toggles während TRANSCRIBING/LLM blockiert) ist **gewollt** (Concurrency-Schutz); nicht aufweichen – nur sicherstellen, dass der State nie hängenbleibt.
- `wl-copy` immer mit `DEVNULL` (nicht `PIPE`) aufrufen, sonst Hang.

## Offene / mögliche nächste Schritte

- **Eigener sauberer PR** für den Linux-Port (bewusst noch nicht erstellt). PR #1 auf `upstream` ist ein automatischer GitHub-Vorschlag (fremder Windows-Tauri-Port von `nobbie2009`) – **nicht anfassen**.
- **Piper-TTS** ist optionale Laufzeit-Abhängigkeit. Für echtes Vorlesen:
  `.venv/bin/pip install piper-tts` + Stimmen (`.onnx`+`.onnx.json`) nach `~/.local/share/piper-voices/`.
- `notify-send` benötigt Paket `libnotify-bin` (auf KDE i.d.R. vorhanden).
- Menü-/Tray-Hotkey-Beschriftungen zeigen teils noch statisch `Meta+H` etc. – könnte dynamisch aus `config.transcription_hotkey` abgeleitet werden (UX-Detail).

## Changelog-Übersicht (siehe CLAUDE.md)

- v0.2.20 – Paste-Subprocess-Timeouts / Hang-Fix
- v0.2.21 – Diktat, Verlauf, Vorlesen (TTS), Notifications
- v0.2.22 – Grafisches Hauptfenster als Start/Stopp-Fallback
- (CI ohne Versionsnummer)

## Schnellstart nächster Chat

```bash
cd /home/timintech/projects/blitztext-app/BlitztextLinux
.venv/bin/python -m pytest tests/                                  # Baseline
BLITZTEXT_DEBUG=1 bash run.sh                                      # App mit Debug-Logs
git log --oneline -8                                              # letzte Arbeit
gh run list --repo TimInTech/blitztext-app --branch feature/linux-port --limit 3
```
