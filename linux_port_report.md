# Blitztext Linux Port Status-Report

Dieses Dokument beschreibt den aktuellen Entwicklungsstand des Linux-Ports im Branch `feature/linux-port`.

---

## 1. Implementierte Module (`app/`)

*   **`blitztext_linux.py`**:
    *   Hauptkomponente und Einstiegspunkt der Anwendung (`QApplication`).
    *   System-Tray-Icon (Mikrofon-Symbol) mit vollständigem Kontextmenü für alle 5 Workflows, Einstellungen und Beenden.
    *   Einstellungsdialog (`SettingsDialog`) zur Konfiguration aller Parameter inklusive Tab-Struktur für Workflows.
    *   Asynchrone Hintergrund-Ausführung der Aufnahme-, Transkriptions- und LLM-Prozesse mittels `QThreadPool` und `QRunnable`, um ein Einfrieren der Benutzeroberfläche zu verhindern.
    *   State-Machine zur Visualisierung des aktuellen Zustands im Tooltip des System-Trays (`IDLE`, `RECORDING`, `TRANSCRIBING`, `LLM_REWRITING`).
*   **`config.py`**:
    *   Verwaltet Laden, Speichern und Validierung von `~/.config/blitztext-linux/config.json`.
    *   Implementiert automatische Rechtevergabe (**0o600 / Lese- und Schreibrechte nur für den aktuellen Benutzer**) zum Schutz des gespeicherten OpenAI API-Keys.
    *   Führt Deep-Merge mit vordefinierten Default-Werten aus.
*   **`audio_recorder.py`**:
    *   Steuert die Audioaufnahme über das System-Utility `parec` (unterstützt PulseAudio und PipeWire).
    *   Implementiert "Stale-PID-Schutz" zur Erkennung und automatischen Bereinigung verwaister `parec`-Hintergrundprozesse vor dem Start einer neuen Aufnahme.
    *   Benötigt ein gültiges `$XDG_RUNTIME_DIR` (Pflicht aus Sicherheitsgründen, kein unsicherer `/tmp`-Fallback).
*   **`transcribe.py`**:
    *   Verantwortlich für die lokale Transkription aufgezeichneter WAV-Dateien.
    *   Unterstützt sowohl das offizielle `openai-whisper` (Standard) als auch das performantere `faster-whisper` Backend.
    *   Kompatibel mit allen gängigen Whisper-Modellgrößen (`tiny` bis `large-v3-turbo`).
*   **`hotkey_service.py`**:
    *   Globaler systemweiter Hotkey-Daemon via `evdev`, der in einem separaten `QThread` (`HotkeyWorker`) läuft.
    *   Unterstützt **Toggle-Modus** (Hotkey drücken = Start/Stopp) und **Hold-Modus** (gedrückt halten = aufnehmen, loslassen = stoppen).
    *   Implementiert Entprellung (Debouncing, `0.6` Sekunden) gegen doppelte Trigger-Events.
    *   Automatisches Reconnect-Verhalten bei Verbindungsabbruch von Tastatur-Eingabegeräten.
*   **`paste_service.py`**:
    *   Überträgt den fertigen Text (Original oder umformuliert) via `wl-copy` in das Wayland-System-Clipboard.
    *   Simuliert ein anschließendes `Ctrl+V` mittels `ydotool` (sofern `autopaste` in den Einstellungen aktiviert ist).
*   **`llm_service.py`**:
    *   Anbindung an das OpenAI SDK unter Verwendung des schnellen und kostengünstigen Modells `gpt-4o-mini`.
    *   Implementiert die 3 Text-Rewriting-Workflows (`Blitztext+`, `Blitztext $%&!`, `Blitztext :)`) mit den entsprechenden System-Prompts.
*   **`workflows.py`**:
    *   Zentrale Definition der Workflows, deren Hotkeys, Anzeige-Icons und Abhängigkeiten (z. B. `needs_llm`).

---

## 2. Teststatus

Alle **54 Tests** im Verzeichnis `tests/` laufen vollständig grün durch. 

### Übersicht der Testdateien
*   **`test_config.py`** (16 Tests):
    *   Verifiziert Default-Werte.
    *   Prüft Lese-/Schreib-Roundtrip, das automatische Ergänzen fehlender Konfigurationsabschnitte und die korrekten Datei-Berechtigungen (600).
    *   Stellt sicher, dass sensible API-Keys niemals über Standard-Logs oder Konsolenausgaben ausgegeben werden.
*   **`test_hotkey_modes.py`** (15 Tests):
    *   Prüft die korrekte Signalverarbeitung für Hold- und Toggle-Abläufe.
    *   Testet das Debounce-Verhalten und den Schutz vor Autorepeat-Tastaturevents.
*   **`test_llm_service.py`** (13 Tests):
    *   Verifiziert das Zusammenbauen der OpenAI-Prompts für alle Umschreibungs-Workflows.
    *   Testet das Fehlerhandling bei API-Verbindungsfehlern oder leeren Rückgaben anhand eines Mock-OpenAI-Clients.
*   **`test_workflows.py`** (10 Tests):
    *   Stellt sicher, dass alle 5 Workflows mit korrekten Namen, Icons und Metadaten (Umschreibung erforderlich vs. lokal) registriert sind.

---

## 3. Bekannte Restpunkte / Einschränkungen

*   **Autostart**: Im Gegensatz zur macOS-Version, die ein integriertes Kontrollkästchen besitzt, wird Autostart unter Linux derzeit nicht direkt aus der App heraus konfiguriert. Benutzer müssen manuell einen `.desktop`-Eintrag unter `~/.config/autostart/` anlegen oder einen Systemd-User-Service konfigurieren.
*   **Wayland-Fokus**: Das Auto-Paste (`ydotool`) und das Clipboard (`wl-clipboard`) setzen eine aktive Wayland-Session voraus. Reine X11-Desktops werden derzeit nicht offiziell unterstützt (hier müssten `xclip` und `xdotool` als Fallbacks implementiert werden).
*   **evdev-Berechtigungen**: Da `evdev` direkten Zugriff auf `/dev/input/` benötigt, muss der ausführende Benutzer zwingend in der Systemgruppe `input` sein. Dies erfordert nach der Installation eine einmalige Benutzer-Interaktion (Ab- und Anmeldung).
