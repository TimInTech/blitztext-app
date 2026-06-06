# BlitztextLinux Handover

Aktuelle Uebergabe fuer den naechsten Chat:

- [HANDOVER-2026-06-06.md](HANDOVER-2026-06-06.md)

Kurzkontext:

- Projektpfad: `/home/timintech/projects/blitztext-app/BlitztextLinux`
- Branch: `feature/linux-port`
- Fokus der letzten Arbeit: evdev-Hotkey-Zuverlaessigkeit fuer `KEY_LEFTALT`, Debug-Logging, Tray-State-Feedback und Shutdown-Crash beim Beenden waehrend `TRANSCRIBING`.
- Letzte Verifikation: `.venv/bin/python -m pytest tests/ -v` mit `91 passed, 4 skipped` (GUI-Tests via `WHISPER_GUI_TESTS=1 QT_QPA_PLATFORM=offscreen`).

## Changelog v0.2.20

- fix: Left-Alt Hotkey haengt nach erstem Zyklus — Root Cause war ein
  blockierender Paste-Subprocess ohne Timeout (`paste_service.py`). Ein haengendes
  `ydotool`/`wl-copy` liess den Transkriptions-Worker nie zurueckkehren, sodass der
  App-State dauerhaft auf `TRANSCRIBING`/`LLM_REWRITING` (orange) stand und kein
  neuer Hotkey-Toggle moeglich war. `wl-copy` und `ydotool` haben jetzt
  `timeout=5s`; ein ydotool-Timeout ist nicht-fatal (Clipboard ist bereits
  gesetzt), ein wl-copy-Timeout wird als `PasteServiceError` -> Worker-`error` ->
  State `IDLE` behandelt. Damit kehrt der State nach jedem Zyklus zuverlaessig auf
  IDLE zurueck.
- bestaetigt/abgesichert: `KEY_LEFTALT` Einzel-Key-Erkennung, `value=1` (key-down)
  loest aus, `value=2` (auto-repeat) und `value=0` (key-up) werden ignoriert;
  Debounce 0.6s. Neue Regressionstests in `tests/test_state_machine.py`.

## Nicht anfassen

- Hotkey-Erkennung: Left-Alt (`KEY_LEFTALT`) Einzel-Key-Erkennung, `value=1` only,
  `value=2`/`value=0` ignoriert (`app/hotkey_service.py`).
- evdev-Debounce-Timing: 0.6s (`DEBOUNCE_SECONDS`).
- State-Guard: neue Toggles werden waehrend `TRANSCRIBING`/`LLM_REWRITING`
  bewusst blockiert (Concurrency-Schutz) — der Fix sorgt nur dafuer, dass der
  State nicht haengenbleibt, der Guard bleibt erhalten.
- Tray-Farb-Konvention: IDLE=gruen, RECORDING=rot, TRANSCRIBING/LLM=orange,
  ERROR=grau.

