# Blitztext Linux

Dieses Verzeichnis enthält den eigenständigen Linux-Port von **Blitztext**, entwickelt für Kubuntu/Ubuntu unter KDE Plasma mit Wayland. 

> [!IMPORTANT]
> **Hinweis zur Codebasis**: Die macOS-Version (`BlitztextMac/`) bleibt von diesem Port vollkommen unberührt. `BlitztextLinux` ist eine eigenständige Python 3/PyQt6-Implementierung, die die gleichen Kern-Workflows wie das macOS-Original unter Linux bereitstellt.

---

## Voraussetzungen

### Systempakete (apt)
Für den Betrieb werden folgende Linux-Systempakete benötigt:
```bash
sudo apt install pulseaudio-utils wl-clipboard ydotool ffmpeg python3-venv python3-evdev socat
```
*   **pulseaudio-utils**: Stellt `parec` für die Audioaufnahme via PulseAudio/PipeWire bereit.
*   **wl-clipboard**: Stellt `wl-copy` zum Schreiben von Text in die Wayland-Zwischenablage bereit.
*   **ydotool**: Simuliert die Tastenkombination `Ctrl+V` für das automatische Einfügen (Auto-Paste).
*   **ffmpeg**: Wird für Audio-Konvertierungen benötigt.
*   **python3-evdev**: Linux-Eingabegeräte-Zugriff für den systemweiten Hotkey-Daemon.
*   **socat**: Hilfswerkzeug zur optionalen Socket-Kommunikation.

### Python-Pakete (pip / virtuelles Environment)
Innerhalb des virtuellen Environments (`.venv`) werden benötigt:
*   `PyQt6` (GUI und Anwendungs-Lifecycle)
*   `evdev` (systemweite Hotkeys via Linux `/dev/input/`)
*   `openai` (API-Client für LLM-Workflows)
*   `pytest` (nur zur Testausführung)

### Whisper-Engines (pipx)
Die Transkription läuft standardmäßig lokal auf Ihrem Rechner. In der Praxis ist der einfachste Weg auf Ubuntu/Kubuntu das Installationsskript unten; es richtet `pipx` mit Python 3.11 ein und umgeht damit den Versionskonflikt, der auf neueren Ubuntu-Setups auftreten kann.

*   **Pflicht**: `openai-whisper`
    ```bash
    pipx install --python "$(command -v python3.11)" openai-whisper
    ```
*   **Optional**: `faster-whisper` (für beschleunigte Ausführung)
    ```bash
    pipx inject openai-whisper faster-whisper
    ```
*   **Empfohlen auf Ubuntu/Kubuntu**:
    ```bash
    bash scripts/install.sh
    ```

---

## Verzeichnisüberblick von BlitztextLinux/

```text
BlitztextLinux/
├── app/
│   ├── __init__.py
│   ├── audio_recorder.py   # PulseAudio/PipeWire-Aufnahme via parec-Subprozess
│   ├── blitztext_linux.py  # PyQt6-Hauptanwendung (System-Tray & Einstellungen)
│   ├── config.py           # Konfigurations-Manager (Laden, Validieren, Speichern)
│   ├── hotkey_service.py   # evdev-basierter globaler Hotkey-Daemon (QThread)
│   ├── llm_service.py      # Schnittstelle zur OpenAI API für Rewriting-Workflows
│   ├── paste_service.py    # Wayland-Clipboard-Integration (wl-copy, ydotool)
│   ├── transcribe.py       # Whisper-Transkription (openai-whisper/faster-whisper)
│   └── workflows.py        # Definitionen und Metadaten der 5 Workflows
├── tests/
│   ├── __init__.py
│   ├── test_config.py      # Tests für Defaults, Speichern und Berechtigungen
│   ├── test_hotkey_modes.py# Tests für Hold- und Toggle-Modus sowie Debouncing
│   ├── test_llm_service.py # Tests für OpenAI-Prompts und Mock-Aufrufe
│   └── test_workflows.py   # Tests für Metadaten und Tasten-Zuordnung
├── README.md               # Dieses Dokument
└── linux_port_report.md    # Status-Bericht und Test-Zusammenfassung
```

---

## Die 5 Workflows und Hotkeys

Blitztext Linux registriert globale Hotkeys über die Linux-Input-Subsysteme (`evdev`). Folgende Workflows stehen bereit:

| Menüpunkt | Hotkey | LLM-Bedarf | Beschreibung |
| :--- | :--- | :--- | :--- |
| **🎙 Blitztext** | `Meta+H` | Nein | Zeichnet Sprache auf, transkribiert sie lokal oder online und fügt sie direkt ein. |
| **🔒 Blitztext Lokal** | `Meta+Shift+H` | Nein | Erzwingt eine rein lokale Transkription ohne Internet-Verbindung. |
| **✨ Blitztext+** | `Meta+Shift+T` | Ja | Transkribiert die Aufnahme und formuliert sie mittels GPT-4o-mini um. |
| **🔥 Blitztext $%&!** | `Meta+Shift+D` | Ja | Wandelt emotionale oder frustrierte Sprache in eine sachliche Nachricht um. |
| **😊 Blitztext :)** | `Meta+Shift+E` | Ja | Ergänzt den transkribierten Text mit passenden Emojis (Dichte einstellbar). |

> [!NOTE]
> Die drei **LLM-Workflows** (`Blitztext+`, `Blitztext $%&!`, `Blitztext :)`) benötigen zwingend einen gültigen **OpenAI API-Key**. Ohne diesen Key sind diese Funktionen im Menü und über die Hotkeys deaktiviert bzw. führen zu einer Fehlermeldung.

---

## Tray-Symbol: Statusfarben

Das Mikrofon-Symbol im System-Tray zeigt über seine Farbe den aktuellen Zustand der State-Machine an:

<p align="center">
  <img src="../docs/screenshots/linux/tray-states.png" alt="Tray-Symbol in grün (Bereit), rot (Aufnahme), orange (Verarbeitung) und grau (Fehler)" width="640">
</p>

| Farbe | Zustand | Bedeutung |
| :---: | :--- | :--- |
| 🟢 **Grün** (`#2e7d32`) | `IDLE` | Bereit — wartet auf Hotkey oder Klick. |
| 🔴 **Rot** (`#c62828`) | `RECORDING` | Aufnahme läuft. |
| 🟠 **Orange** (`#ef6c00`) | `TRANSCRIBING` / `LLM_REWRITING` | Transkription bzw. LLM-Umschreibung läuft. |
| ⚪ **Grau** (`#757575`) | `ERROR` | Letzter Vorgang ist fehlgeschlagen. |

> [!NOTE]
> Steht im Desktop-Environment kein Tray-Bereich zur Verfügung, fällt das Icon auf das System-Theme `audio-input-microphone` zurück; die Farbkodierung greift dann ggf. nicht.

---

## Hauptfenster (grafischer Fallback)

Falls der globale Hotkey nicht greift (z. B. KDE-Shortcut-Konflikt) oder keine Tastatur zur Hand ist, bietet Blitztext ein **klickbares Hauptfenster**:

- **Start/Stopp-Button** — startet bzw. stoppt die Aufnahme per Maus (funktioniert unabhängig vom Hotkey-Modus `toggle`/`hold`).
- **Workflow-Auswahl** — alle fünf Workflows per Dropdown wählbar.
- **Verwerfen** — laufende Aufnahme abbrechen, ohne zu transkribieren.
- Schnellzugriff auf **Diktat**, **Verlauf**, **Vorlesen** und **Einstellungen**.

Das Fenster öffnet sich beim Start sowie über den Tray-Eintrag **🪟 Fenster anzeigen** oder einen Klick auf das Tray-Icon. Schließen versteckt das Fenster nur — die App läuft im Tray weiter.

---

## Diktat, Verlauf und Vorlesen

Zusätzlich zu den Workflows bietet das Tray-Menü (und das Hauptfenster) drei Komfort-Funktionen:

| Menüpunkt | Beschreibung |
| :--- | :--- |
| **🎤 Diktat-Modus** | Umschalter. Ist er aktiv, werden alle Transkripte als Diktat-Einträge gesammelt und (sofern ein gültiger Notizordner gesetzt ist) einzeln als Markdown-Datei gespeichert. Im Verlauf erscheint dann eine Schaltfläche **Zusammenführen**, die alle Diktat-Einträge chronologisch in eine Textdatei kombiniert und in die Zwischenablage kopiert. |
| **📋 Verlauf…** | Öffnet ein Fenster mit den letzten Transkripten (Anzahl konfigurierbar). Pro Eintrag: in Zwischenablage kopieren oder löschen. |
| **🔊 Vorlesen…** | Liest beliebigen Text per **Piper TTS** vor (Stimmen- und Tempo-Auswahl, Pause/Fortsetzen). |

> [!NOTE]
> **Diktat-Notizen** werden ausschließlich in einen Ordner **innerhalb des Home-Verzeichnisses** geschrieben (Schutz gegen Pfad-Ausbruch), mit Berechtigungen `0o600`. Ordner und maximale Verlaufsgröße sind unter **Einstellungen → Allgemein** konfigurierbar.

> [!IMPORTANT]
> **Vorlesen** benötigt die optionale Abhängigkeit **Piper TTS** sowie Stimm-Modelle:
> ```bash
> .venv/bin/pip install piper-tts
> # Stimmen (.onnx + .onnx.json) nach ~/.local/share/piper-voices/ legen
> ```
> Fehlt Piper oder eine Stimme, zeigt das Vorlese-Fenster einen Installationshinweis; alle übrigen Funktionen bleiben nutzbar. Optionale Desktop-Benachrichtigungen nutzen `notify-send` (Paket `libnotify-bin`).

---

## Konfiguration

### Konfigurationspfad
Die Konfiguration wird im Standard-XDG-Verzeichnis abgelegt unter:
`~/.config/blitztext-linux/config.json`

> [!IMPORTANT]
> Um den OpenAI API-Key zu schützen, wird die Datei automatisch mit restriktiven Dateiberechtigungen (**0o600 / `chmod 600`**) gespeichert, sodass nur der aktuelle Benutzer Lese- und Schreibrechte besitzt.

### Beispiel-Konfiguration
Folgende Struktur zeigt die Standardkonfiguration mit allen Default-Werten:

```json
{
  "model": "base",
  "language": "de",
  "backend": "openai-whisper",
  "hotkey_mode": "toggle",
  "openai_api_key": "",
  "autopaste": true,
  "audio_device": "@DEFAULT_SOURCE@",
  "workflows": {
    "text_improver_tone": "neutral",
    "emoji_density": "mittel",
    "dampf_system_prompt": ""
  }
}
```

*   **model**: Whisper-Modellgröße (`tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, `large-v3-turbo`). Standard: `base`.
*   **language**: Sprache für die Transkription (z. B. `de`, `en`) oder `auto` für automatische Erkennung.
*   **backend**: Das Transkriptions-Backend (`openai-whisper` oder `faster-whisper`).
*   **hotkey_mode**: Steuert das Verhalten der Aufnahme.
    *   `toggle`: Einmal drücken startet die Aufnahme, erneutes Drücken beendet sie. (Standard)
    *   `hold`: Aufnahme läuft, solange der Hotkey gedrückt gehalten wird; Loslassen stoppt sie.
*   **openai_api_key**: Ihr persönlicher OpenAI API-Key für die LLM-Workflows.
*   **autopaste**: Falls `true`, wird das Ergebnis direkt per `ydotool` (Ctrl+V) an der Cursor-Position eingefügt.
*   **audio_device**: Der Name der PulseAudio/PipeWire-Quelle (Default: `@DEFAULT_SOURCE@`).
*   **workflows.text_improver_tone**: Tonalität für `Blitztext+` (`neutral`, `formal`, `locker`).
*   **workflows.emoji_density**: Emoji-Menge für `Blitztext :)` (`wenig`, `mittel`, `viel`).
*   **workflows.dampf_system_prompt**: Benutzerdefinierter System-Prompt für `Blitztext $%&!`. Falls leer, greift der eingebaute Standard.

---

## Installation und Start

### Schnellstart (empfohlen)

```bash
cd BlitztextLinux
bash scripts/install.sh
```

Wichtig: Die Befehle unten gehen vom Verzeichnis `BlitztextLinux/` aus.

Das Skript ist der bevorzugte Weg für Ubuntu/Kubuntu. Es:
- prüft Ubuntu/Debian und die nötige Python-Version
- installiert fehlende Systempakete inkl. `pipx`
- richtet die virtuelle Umgebung `.venv` ein
- installiert `openai-whisper` mit einem kompatiblen Python 3.11–3.13
- verwendet den vorhandenen `ydotool.service`
- richtet den systemd-User-Service von Blitztext ein

### Danach

1. Falls der Benutzer neu zur Gruppe `input` hinzugefügt wurde: **ab- und wieder anmelden** oder neu starten.
2. Anwendung starten:
   ```bash
   cd BlitztextLinux
   ./run.sh
   ```
   Das Skript findet die `.venv` automatisch und startet die App mit dem passenden Python.
3. Wenn der Test läuft, Autostart aktivieren:
   ```bash
   systemctl --user start blitztext-linux
   ```

Erscheint das Mikrofon-Symbol im Tray und reagieren die Hotkeys korrekt, ist die Installation erfolgreich.

### Manuell nur für Diagnose

Wenn Sie gezielt debuggen oder die Schritte einzeln ausführen möchten:

1. **evdev-Rechte**
   ```bash
   sudo usermod -aG input $USER
   ```
2. **Virtuelle Umgebung**
   ```bash
   cd BlitztextLinux
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r <(echo "PyQt6" && echo "evdev" && echo "openai" && echo "pytest")
   ```
3. **ydotool prüfen**
   ```bash
   systemctl --user start ydotool.service
   ```
4. **Anwendung starten**
   ```bash
   python app/blitztext_linux.py
   ```

---

## Test-Ausführung

Um die komplette Suite aus 57 Unit- und Integrationstests auszuführen, stellen Sie sicher, dass Sie sich im Verzeichnis `BlitztextLinux` befinden und das Environment aktiv ist:

```bash
pytest
```

---

## Autostart einrichten

Blitztext Linux kann als systemd-User-Service eingerichtet werden, damit es nach dem Login automatisch im System-Tray erscheint.

### 1. Installations-Skript ausführen

Das Skript prüft alle Abhängigkeiten, richtet die virtuelle Umgebung ein und installiert den systemd-Service — es startet die Anwendung aber **nicht** automatisch:

```bash
cd BlitztextLinux
bash scripts/install.sh
```

### 2. Re-Login durchführen

Falls der Benutzer noch nicht Mitglied der Gruppe `input` war, informiert das Skript über einen nötigen Re-Login. **Melden Sie sich ab und wieder an** (oder starten Sie das System neu), damit evdev-Hotkeys funktionieren.

### 3. Manuellen Test durchführen

Starten Sie die Anwendung einmalig manuell, um sicherzugehen, dass alles funktioniert:

```bash
cd BlitztextLinux
./run.sh
```

Erscheint das Mikrofon-Symbol im Tray und reagieren die Hotkeys korrekt, ist die Installation erfolgreich.

### 4. Autostart aktivieren

Wenn der manuelle Test erfolgreich war, starten Sie den Service:

```bash
systemctl --user start blitztext-linux
```

Ab sofort startet Blitztext Linux automatisch mit jeder grafischen Sitzung.

### Diagnose

Bei Problemen liefert das Verify-Skript eine Übersicht aller Abhängigkeiten:

```bash
bash scripts/verify.sh
```

### Autostart deaktivieren

```bash
systemctl --user stop blitztext-linux
systemctl --user disable blitztext-linux
```

---

## Bekannte Grenzen

*   **Linux only**: Läuft ausschließlich auf Linux-Systemen.
*   **Wayland Fokus**: Die Automatisierung (Auto-Paste) und das Clipboard sind auf Wayland ausgelegt (`wl-clipboard` und `ydotool`).
*   **Kein nativer X11-Support**: Unter klassischen X11-Sessions fehlen native Fallbacks für `xclip` or `xdotool`.
*   **System-Tray Abhängigkeit**: Erfordert einen System-Tray-Bereich im Desktop-Environment (getestet und optimiert auf Kubuntu 24.04 unter KDE Plasma).

---

## Datenschutz-Hinweis

*   **Lokale Workflows** (`Blitztext` ohne API-Key / `Blitztext Lokal`): Verbleiben komplett offline. Die Sprachaufzeichnungen werden lokal auf Ihrem Gerät transkribiert und nicht an externe Server übertragen.
*   **LLM-Workflows** (`Blitztext+`, `Blitztext $%&!`, `Blitztext :)`): Senden das lokal erstellte Transkript zur Verarbeitung an die OpenAI API. Hierbei gelten die Datenschutzbestimmungen von OpenAI (analog zur macOS-Version).

---

## Sicherheitshinweis: evdev und input-Gruppe

BlitztextLinux liest globale Tastenkürzel direkt über `/dev/input/event*` via `evdev`. Dazu wird der Benutzer der Gruppe `input` hinzugefügt (`sudo usermod -aG input $USER`).

**Sicherheitsabwägung:** Alle Prozesse des Benutzers (eigene Skripte, Browser-Plugins, andere Apps) können damit systemweit Tastatureingaben mitlesen. Dies ist ein bekanntes Trade-off unter Wayland, da kein standardisiertes Portal für globale Hotkeys existiert. Nutze BlitztextLinux nur auf Systemen, denen du vollständig vertraust, und installiere keine unbekannten Programme im selben Benutzerkonto.

**Langfristige Alternative:** XDG GlobalShortcuts Portal (D-Bus) — wird noch nicht flächendeckend von allen Compositors unterstützt.

---

## Entwickler-Hinweis (AI-Assisted Development)

Dieses Projekt wurde mit Unterstützung künstlicher Intelligenz (AI-assisted) entworfen. Die Planung, Architektur-Entscheidungen sowie der Entwurf einzelner Komponenten wurden KI-gestützt erarbeitet. Der gesamte Code wurde anschließend manuell gesichtet, auf Funktion und Sicherheit geprüft und die vollständige Test-Suite lokal verifiziert.
