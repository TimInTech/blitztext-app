# Blitztext

**Sprache zu Text per Hotkey** — aufnehmen, transkribieren, optional per LLM umschreiben und direkt in die aktive Anwendung einfügen.

Dieses Repository enthält zwei eigenständige Implementierungen:

- 🐧 **[Blitztext Linux](BlitztextLinux/README.md)** — Python 3 / PyQt6, für Kubuntu/Ubuntu unter KDE Plasma mit Wayland. **Im Fokus dieses Forks.**
- 🍎 **[Blitztext macOS](BlitztextMac/README.md)** — das ursprüngliche Swift/SwiftUI-Menubar-Projekt von [cmagnussen](https://github.com/cmagnussen/blitztext-app), unverändert übernommen.

> [!NOTE]
> Dies ist ein Lern- und Experimentier-Projekt: eigenen OpenAI API-Key mitbringen, kein gehostetes Backend, keine Gewährleistung. Die macOS-Version bleibt von der Linux-Portierung vollkommen unberührt.

---

## Screenshots (Linux)

<table>
  <tr>
    <td align="center">
      <img src="docs/screenshots/linux/main-window-compact-glass.png" alt="Hauptfenster im Breeze-Dark/Glass-Design: Workflow-Auswahl, runder Aufnahme-Button, Status und Schnellzugriffe" width="256"><br>
      <sub><b>Hauptfenster</b> — bereit (Glass-Dark-Design)</sub>
    </td>
    <td align="center">
      <img src="docs/screenshots/linux/main-window-compact-recording.png" alt="Hauptfenster während der Aufnahme: roter Aufnahme-Button, Statuspunkt und laufender Timer" width="256"><br>
      <sub><b>Hauptfenster</b> — Aufnahme läuft</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="docs/screenshots/linux/settings-whisper.png" alt="Einstellungen: Spracherkennung mit Whisper-Modell, Backend, Hotkey-Modus" width="360"><br>
      <sub><b>Einstellungen → Spracherkennung</b></sub>
    </td>
    <td align="center">
      <img src="docs/screenshots/linux/settings-ki-workflows.png" alt="Einstellungen: KI-Workflows mit OpenAI API-Key, Tonfall und Emoji-Dichte" width="360"><br>
      <sub><b>Einstellungen → KI-Workflows</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="docs/screenshots/linux/settings-allgemein.png" alt="Einstellungen: Allgemein mit Auto-Paste, Diktat-Notizordner und Verlaufsgröße" width="360"><br>
      <sub><b>Einstellungen → Allgemein</b></sub>
    </td>
    <td align="center">
      <img src="docs/screenshots/linux/history.png" alt="Verlaufs-Fenster mit Transkripten und Diktat-Einträgen" width="360"><br>
      <sub><b>Verlauf</b> — Transkripte & Diktat-Einträge</sub>
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <img src="docs/screenshots/linux/tts.png" alt="Vorlesen-Fenster mit Stimmen- und Tempo-Auswahl (Piper TTS)" width="360"><br>
      <sub><b>Vorlesen</b> — Text-to-Speech via Piper</sub>
    </td>
  </tr>
</table>

---

## Die 5 Workflows

| Workflow | Hotkey | LLM | Beschreibung |
| :--- | :--- | :---: | :--- |
| 🎙 **Blitztext** | `Meta+H` | – | Sprache aufnehmen, transkribieren, direkt einfügen. |
| 🔒 **Blitztext Lokal** | `Meta+Shift+H` | – | Rein lokale Transkription, ohne Internet. |
| ✨ **Blitztext+** | `Meta+Shift+T` | ✓ | Transkript per GPT-4o-mini sauber umformulieren. |
| 🔥 **Blitztext $%&!** | `Meta+Shift+D` | ✓ | Emotionale Sprache in eine sachliche Nachricht wandeln. |
| 😊 **Blitztext :)** | `Meta+Shift+E` | ✓ | Passende Emojis ergänzen (Dichte einstellbar). |

Dazu Komfort-Funktionen: **Diktat-Modus** (Markdown-Notizen), **Verlauf** (Kopieren/Löschen/Zusammenführen), **Vorlesen** (Piper TTS) und Desktop-**Benachrichtigungen**.

---

## Status auf einen Blick — Tray-Symbol

Das Mikrofon-Symbol im System-Tray signalisiert über seine Farbe den aktuellen Zustand:

<p align="center">
  <img src="docs/screenshots/linux/tray-states.png" alt="Tray-Symbol in den Farben grün (Bereit), rot (Aufnahme), orange (Verarbeitung) und grau (Fehler)" width="640">
</p>

| Farbe | Zustand | Bedeutung |
| :---: | :--- | :--- |
| 🟢 **Grün** | Bereit (IDLE) | Wartet auf Hotkey oder Klick. |
| 🔴 **Rot** | Aufnahme | Mikrofon nimmt gerade auf. |
| 🟠 **Orange** | Verarbeitung | Transkription bzw. LLM-Umschreibung läuft. |
| ⚪ **Grau** | Fehler | Letzter Vorgang ist fehlgeschlagen. |

---

## Schnellstart (Linux)

```bash
# Systempakete
sudo apt install pulseaudio-utils wl-clipboard ydotool ffmpeg python3-venv python3-evdev socat

# Lokale Whisper-Engine
pipx install openai-whisper

# Projekt aufsetzen
cd BlitztextLinux
python3 -m venv .venv
.venv/bin/pip install PyQt6 evdev openai pytest

# evdev-Rechte (danach ab- und wieder anmelden)
sudo usermod -aG input $USER

# Starten
./run.sh
```

Die **vollständige Anleitung** — Voraussetzungen, ydotool-Setup, Konfiguration, systemd-Autostart, Tests, Sicherheits- und Datenschutz-Hinweise — steht in **[BlitztextLinux/README.md](BlitztextLinux/README.md)**.

---

## macOS-Version

Der ursprüngliche macOS-Menubar-Client liegt unverändert unter **[BlitztextMac/](BlitztextMac/README.md)** und stammt aus dem Upstream-Projekt von [cmagnussen/blitztext-app](https://github.com/cmagnussen/blitztext-app). Build und Nutzung sind dort dokumentiert.

---

## Lizenz

Code unter der MIT-Lizenz — siehe [LICENSE](LICENSE). Projektnamen, Logos und App-Icons sind davon nicht automatisch als Marken-/Brand-Assets erfasst — siehe [TRADEMARKS.md](TRADEMARKS.md).

Begleitende Website (blitztext.de) betrieben von Blackboat Internet GmbH:
[Impressum](https://www.blackboat.com/impressum) · [Datenschutz](https://www.blackboat.com/datenschutz)
