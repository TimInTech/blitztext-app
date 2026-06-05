#!/usr/bin/env python3
"""BlitztextLinux main application.

Combines system tray operations, settings UI, and hotkey actions using evdev,
Parec, Whisper, and OpenAI.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, QThreadPool, QRunnable, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QComboBox, QLineEdit, QCheckBox, QPlainTextEdit,
    QPushButton, QDialogButtonBox, QLabel, QMessageBox, QMenu, QSystemTrayIcon, QStyle
)

# Make project importable when running directly
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app.config import Config
from app.llm_service import LLMService, WorkflowType, LLM_WORKFLOWS, LLMServiceError
from app.hotkey_service import HotkeyWorker
from app.audio_recorder import AudioRecorder, AudioRecorderError
from app.transcribe import transcribe, TranscribeError
from app.paste_service import PasteService, PasteServiceError

# Set up module logger
logger = logging.getLogger("blitztext.main")


def _configure_qt_platform() -> None:
    """Prefer native Wayland when a Wayland session is available."""
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if _wayland_display_available(os.environ.get("WAYLAND_DISPLAY")):
        os.environ["QT_QPA_PLATFORM"] = "wayland"


def _wayland_display_available(display_name: Optional[str]) -> bool:
    """Return True when WAYLAND_DISPLAY points to an existing socket path."""
    if not display_name:
        return False

    if os.path.isabs(display_name):
        return os.path.exists(display_name)

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        return False

    return os.path.exists(os.path.join(runtime_dir, display_name))


def _infer_wayland_display() -> Optional[str]:
    """Infer a Wayland socket name from XDG_RUNTIME_DIR when env import lagged."""
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir or not os.path.isdir(runtime_dir):
        return None

    candidates = []
    try:
        for name in os.listdir(runtime_dir):
            if name.startswith("wayland-") and os.path.exists(os.path.join(runtime_dir, name)):
                candidates.append(name)
    except OSError:
        return None

    return sorted(candidates)[0] if candidates else None


def _require_display_environment() -> None:
    """Exit before QApplication when no GUI session variables are present."""
    if _wayland_display_available(os.environ.get("WAYLAND_DISPLAY")):
        return

    if os.environ.get("DISPLAY"):
        if os.environ.get("WAYLAND_DISPLAY"):
            print(
                "Warning: WAYLAND_DISPLAY is not usable; falling back to DISPLAY.",
                file=sys.stderr,
                flush=True,
            )
            os.environ.pop("WAYLAND_DISPLAY", None)
        return

    inferred_wayland = _infer_wayland_display()
    if inferred_wayland:
        os.environ["WAYLAND_DISPLAY"] = inferred_wayland
        return

    print("ERROR: No usable display environment set. Exiting.", file=sys.stderr, flush=True)
    sys.exit(1)


def create_help_label(text: str) -> QLabel:
    """Create a styled small help label for config fields."""
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 10px;")
    label.setWordWrap(True)
    return label


class SettingsDialog(QDialog):
    """Settings dialog for configuring BlitztextLinux."""

    def __init__(self, config: Config, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Blitztext Einstellungen")
        self.resize(550, 480)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Whisper & Audio
        tab_whisper = QWidget()
        form_whisper = QFormLayout(tab_whisper)
        form_whisper.setSpacing(10)

        self.combo_model = QComboBox()
        self.combo_model.addItems(["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "large-v3-turbo"])
        self.combo_model.setCurrentText(self.config.model)

        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["openai-whisper", "faster-whisper"])
        self.combo_backend.setCurrentText(self.config.backend)

        self.edit_language = QLineEdit()
        self.edit_language.setText(self.config.language)
        self.edit_language.setPlaceholderText("de, en, auto...")

        self.edit_audio_device = QLineEdit()
        self.edit_audio_device.setText(self.config.audio_device)
        self.edit_audio_device.setPlaceholderText("@DEFAULT_SOURCE@")

        self.combo_hotkey_mode = QComboBox()
        self.combo_hotkey_mode.addItems(["toggle", "hold"])
        self.combo_hotkey_mode.setCurrentText(self.config.hotkey_mode)

        form_whisper.addRow("Whisper-Modell:", self.combo_model)
        form_whisper.addRow("", create_help_label("Wählen Sie die Modellgröße. Größere Modelle sind genauer, benötigen aber mehr Ressourcen."))

        form_whisper.addRow("Transkription-Backend:", self.combo_backend)
        form_whisper.addRow("", create_help_label("faster-whisper ist deutlich schneller und ressourcenschonender."))

        form_whisper.addRow("Sprache:", self.edit_language)
        form_whisper.addRow("", create_help_label("Zweistelliger Ländercode (z. B. 'de', 'en') oder 'auto' für automatische Erkennung."))

        form_whisper.addRow("Audio-Eingabegerät:", self.edit_audio_device)
        form_whisper.addRow("", create_help_label("'@DEFAULT_SOURCE@' nutzt das Standardmikrofon von PulseAudio/PipeWire."))

        form_whisper.addRow("Hotkey-Modus:", self.combo_hotkey_mode)
        form_whisper.addRow("", create_help_label("toggle: Einmal drücken zum Starten, erneut drücken zum Stoppen.\nhold: Gedrückt halten zum Aufnehmen, Loslassen zum Stoppen."))

        self.tabs.addTab(tab_whisper, "Spracherkennung")

        # Tab 2: LLM (KI)
        tab_llm = QWidget()
        form_llm = QFormLayout(tab_llm)
        form_llm.setSpacing(10)

        self.edit_api_key = QLineEdit()
        self.edit_api_key.setText(self.config.openai_api_key)
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_api_key.setPlaceholderText("sk-...")

        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(self.edit_api_key)
        self.btn_show_key = QPushButton("Anzeigen")
        self.btn_show_key.setCheckable(True)
        self.btn_show_key.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self.btn_show_key)

        self.combo_tone = QComboBox()
        self.combo_tone.addItems(["formal", "neutral", "locker"])
        self.combo_tone.setCurrentText(self.config.text_improver_tone)

        self.combo_emoji = QComboBox()
        self.combo_emoji.addItems(["wenig", "mittel", "viel"])
        self.combo_emoji.setCurrentText(self.config.emoji_density)

        self.edit_dampf_prompt = QPlainTextEdit()
        self.edit_dampf_prompt.setPlainText(self.config.dampf_system_prompt)
        self.edit_dampf_prompt.setPlaceholderText("Standard-Systemprompt verwenden...")

        form_llm.addRow("OpenAI API-Key:", api_key_layout)
        form_llm.addRow("", create_help_label("Erforderlich für alle KI/LLM-Features (Blitztext+, Dampf ablassen, Emojis)."))

        form_llm.addRow("Text-Verbesserer Tonfall:", self.combo_tone)
        form_llm.addRow("Emoji-Dichte:", self.combo_emoji)

        form_llm.addRow("Dampf-Umschreiber Prompt:", self.edit_dampf_prompt)
        form_llm.addRow("", create_help_label("Eigener System-Prompt, um wütende Aussagen in eine professionelle Form umzuschreiben."))

        self.tabs.addTab(tab_llm, "KI-Workflows")

        # Tab 3: Allgemein
        tab_general = QWidget()
        form_general = QFormLayout(tab_general)
        form_general.setSpacing(10)

        self.check_autopaste = QCheckBox("Text automatisch einfügen (Auto-Paste)")
        self.check_autopaste.setChecked(self.config.autopaste)
        form_general.addRow(self.check_autopaste)
        form_general.addRow("", create_help_label("Simuliert Strg+V nach Abschluss der Aufnahme. Benötigt das Tool 'ydotool'."))

        self.tabs.addTab(tab_general, "Allgemein")

        layout.addWidget(self.tabs)

        # Dialog Button Box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _toggle_api_key_visibility(self) -> None:
        if self.btn_show_key.isChecked():
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_key.setText("Verbergen")
        else:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_key.setText("Anzeigen")

    def save_settings(self) -> None:
        try:
            self.config.model = self.combo_model.currentText()
            self.config.backend = self.combo_backend.currentText()
            self.config.language = self.edit_language.text().strip()
            self.config.audio_device = self.edit_audio_device.text().strip()
            self.config.hotkey_mode = self.combo_hotkey_mode.currentText()

            self.config.openai_api_key = self.edit_api_key.text().strip()
            self.config.text_improver_tone = self.combo_tone.currentText()
            self.config.emoji_density = self.combo_emoji.currentText()
            self.config.dampf_system_prompt = self.edit_dampf_prompt.toPlainText().strip()

            self.config.autopaste = self.check_autopaste.isChecked()

            self.config.save()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", f"Konfiguration konnte nicht gespeichert werden: {e}")


class _WorkerSignals(QObject):
    """Signals for background transcription/rewrite tasks."""
    status_changed = pyqtSignal(str)  # "transcribing" | "rewriting"
    result = pyqtSignal(str)
    error = pyqtSignal(str)


class _TranscribeWorker(QRunnable):
    """Task worker running Whisper transcription and LLM rewrite asynchronously."""

    def __init__(
        self,
        wav_file: Path,
        model: str,
        language: str,
        backend: str,
        workflow: WorkflowType,
        llm_service: LLMService,
        autopaste: bool,
        paste_service: PasteService,
    ) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self.wav_file = wav_file
        self.model = model
        self.language = language
        self.backend = backend
        self.workflow = workflow
        self.llm_service = llm_service
        self.autopaste = autopaste
        self.paste_service = paste_service

    def run(self) -> None:
        try:
            self.signals.status_changed.emit("transcribing")
            transcript = transcribe(
                wav_file=self.wav_file,
                model=self.model,
                language=self.language,
                backend=self.backend,
            )

            if not transcript or not transcript.strip():
                raise TranscribeError("Keine Sprache im Audio erkannt.")

            # LLM rewrite if it is an LLM workflow
            if self.workflow in LLM_WORKFLOWS:
                self.signals.status_changed.emit("rewriting")
                if not self.llm_service.is_available():
                    raise LLMServiceError(
                        "OpenAI API-Key nicht konfiguriert. Bitte in den Einstellungen eintragen."
                    )
                result_text = self.llm_service.rewrite(self.workflow, transcript)
            else:
                result_text = transcript

            # Paste
            if self.autopaste:
                self.paste_service.paste(result_text)
            else:
                self.paste_service.clipboard_only(result_text)

            self.signals.result.emit(result_text)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            # Clean up WAV file
            try:
                if self.wav_file.is_file():
                    self.wav_file.unlink()
            except OSError as exc:
                logger.warning("Failed to delete temp WAV file %s: %s", self.wav_file, exc)


class BlitztextApp(QObject):
    """Main Blitztext Linux application coordinator."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.config = Config.load()

        self.llm_service = LLMService(
            api_key=self.config.openai_api_key,
            tone=self.config.text_improver_tone,
            emoji_density=self.config.emoji_density,
            dampf_system_prompt=self.config.dampf_system_prompt
        )
        self.audio_recorder = AudioRecorder()
        self.paste_service = PasteService(autopaste=self.config.autopaste)

        # State machine state: "IDLE", "RECORDING", "TRANSCRIBING", "LLM_REWRITING"
        self.state = "IDLE"
        self.current_workflow: Optional[WorkflowType] = None

        # Tray setup
        self.setup_tray()

        # Start hotkey worker
        self.hotkey_worker: Optional[HotkeyWorker] = None
        self.hotkey_thread: Optional[QThread] = None
        self.start_hotkey_worker()

    def setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)

        # Load standard icon fallback
        icon = QIcon.fromTheme("audio-input-microphone")
        if icon.isNull():
            icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Blitztext")

        # Create menu
        self.menu = QMenu()

        # Actions for workflows matching handover specs
        self.action_transcription = QAction("🎙  Blitztext\tMeta+H", self)
        self.action_transcription.triggered.connect(lambda: self._trigger_menu_workflow(WorkflowType.TRANSCRIPTION))
        self.menu.addAction(self.action_transcription)

        self.action_local = QAction("🔒  Blitztext Lokal\tMeta+Shift+H", self)
        self.action_local.triggered.connect(lambda: self._trigger_menu_workflow(WorkflowType.LOCAL))
        self.menu.addAction(self.action_local)

        self.action_improver = QAction("✨  Blitztext+\tMeta+T", self)
        self.action_improver.triggered.connect(lambda: self._trigger_menu_workflow(WorkflowType.TEXT_IMPROVER))
        self.menu.addAction(self.action_improver)

        self.action_dampf = QAction("🔥  Blitztext $%&!\tMeta+D", self)
        self.action_dampf.triggered.connect(lambda: self._trigger_menu_workflow(WorkflowType.DAMPF_ABLASSEN))
        self.menu.addAction(self.action_dampf)

        self.action_emoji = QAction("😊  Blitztext :)\tMeta+E", self)
        self.action_emoji.triggered.connect(lambda: self._trigger_menu_workflow(WorkflowType.EMOJI_TEXT))
        self.menu.addAction(self.action_emoji)

        self.menu.addSeparator()

        # Settings action
        self.action_settings = QAction("⚙   Einstellungen...", self)
        self.action_settings.triggered.connect(self.show_settings_dialog)
        self.menu.addAction(self.action_settings)

        # Quit action
        self.action_quit = QAction("✕   Beenden", self)
        self.action_quit.triggered.connect(self.quit_app)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)

        # Enable/disable items dynamically
        self.update_menu_availability()

        self.tray_icon.show()

    def update_menu_availability(self) -> None:
        available = self.llm_service.is_available()
        self.action_improver.setEnabled(available)
        self.action_dampf.setEnabled(available)
        self.action_emoji.setEnabled(available)

    def start_hotkey_worker(self) -> None:
        self.stop_hotkey_worker()

        self.hotkey_thread = QThread()
        self.hotkey_worker = HotkeyWorker(hotkey_mode=self.config.hotkey_mode)
        self.hotkey_worker.moveToThread(self.hotkey_thread)

        self.hotkey_thread.started.connect(self.hotkey_worker.run)
        self.hotkey_worker.workflow_triggered.connect(self._on_workflow_triggered)
        self.hotkey_worker.recording_stop.connect(self._on_recording_stop)
        self.hotkey_worker.error.connect(self._on_hotkey_error)

        self.hotkey_thread.start()

    def stop_hotkey_worker(self) -> None:
        if self.hotkey_worker:
            self.hotkey_worker.stop()
            self.hotkey_worker = None
        if self.hotkey_thread:
            self.hotkey_thread.quit()
            self.hotkey_thread.wait(2000)
            self.hotkey_thread = None

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update LLM Service parameters from saved configuration
            self.llm_service = LLMService(
                api_key=self.config.openai_api_key,
                tone=self.config.text_improver_tone,
                emoji_density=self.config.emoji_density,
                dampf_system_prompt=self.config.dampf_system_prompt
            )
            self.update_menu_availability()

            # Restart hotkey listener if mode changed
            if self.hotkey_worker and self.hotkey_worker._mode != self.config.hotkey_mode:
                logger.info("Hotkey mode changed to %s. Restarting hotkey worker.", self.config.hotkey_mode)
                self.start_hotkey_worker()

    def _trigger_menu_workflow(self, workflow: WorkflowType) -> None:
        self._on_workflow_triggered(workflow)

    @pyqtSlot(object)
    def _on_workflow_triggered(self, workflow: WorkflowType) -> None:
        logger.info("Workflow triggered: %s (current state: %s)", workflow, self.state)

        if self.state == "IDLE":
            try:
                self.audio_recorder.start(device=self.config.audio_device)
                self.state = "RECORDING"
                self.current_workflow = workflow
                self.update_tray_state()
            except AudioRecorderError as e:
                logger.error("Failed to start recording: %s", e)
                self.show_tray_error("Aufnahme-Fehler", f"Aufnahme konnte nicht gestartet werden: {e}")
                self.state = "IDLE"
                self.current_workflow = None
                self.update_tray_state()

        elif self.state == "RECORDING":
            if self.config.hotkey_mode == "toggle":
                if workflow == self.current_workflow:
                    self._stop_recording_and_process()
                else:
                    logger.info("Ignored hotkey trigger for different workflow %s during recording %s", workflow, self.current_workflow)
            else:
                logger.info("Ignored hotkey trigger %s during recording %s in hold mode", workflow, self.current_workflow)

        else:
            logger.info("Ignored hotkey trigger %s while busy", workflow)

    @pyqtSlot()
    def _on_recording_stop(self) -> None:
        logger.info("Recording stop signal received (current state: %s)", self.state)
        if self.state == "RECORDING":
            if self.config.hotkey_mode == "hold":
                self._stop_recording_and_process()
            else:
                logger.info("Ignored recording stop signal because hotkey mode is toggle")

    def _stop_recording_and_process(self) -> None:
        try:
            wav_path = self.audio_recorder.stop()
            if not wav_path:
                logger.warning("No audio was recorded")
                self.show_tray_warning("Blitztext", "Keine Audioaufnahme erfasst.")
                self.state = "IDLE"
                self.current_workflow = None
                self.update_tray_state()
                return

            self.state = "TRANSCRIBING"
            self.update_tray_state()

            # Ensure PasteService has the latest autopaste configuration
            self.paste_service.autopaste = self.config.autopaste

            # Create the transcribe worker
            worker = _TranscribeWorker(
                wav_file=wav_path,
                model=self.config.model,
                language=self.config.language,
                backend=self.config.backend,
                workflow=self.current_workflow,
                llm_service=self.llm_service,
                autopaste=self.config.autopaste,
                paste_service=self.paste_service
            )

            worker.signals.status_changed.connect(self._on_worker_status_changed)
            worker.signals.result.connect(self._on_worker_result)
            worker.signals.error.connect(self._on_worker_error)

            QThreadPool.globalInstance().start(worker)

        except AudioRecorderError as e:
            logger.error("Failed to stop recording: %s", e)
            self.show_tray_error("Aufnahme-Fehler", f"Aufnahme konnte nicht sauber gestoppt werden: {e}")
            self.state = "IDLE"
            self.current_workflow = None
            self.update_tray_state()

    @pyqtSlot(str)
    def _on_worker_status_changed(self, status: str) -> None:
        if status == "transcribing":
            self.state = "TRANSCRIBING"
        elif status == "rewriting":
            self.state = "LLM_REWRITING"
        self.update_tray_state()

    @pyqtSlot(str)
    def _on_worker_result(self, result_text: str) -> None:
        logger.info("Transcription/Rewrite success. Result length: %d chars", len(result_text))
        self.state = "IDLE"
        self.current_workflow = None
        self.update_tray_state()

    @pyqtSlot(str)
    def _on_worker_error(self, err_msg: str) -> None:
        logger.error("Worker error: %s", err_msg)
        self.show_tray_error("Blitztext Fehler", err_msg)
        self.state = "IDLE"
        self.current_workflow = None
        self.update_tray_state()

    def update_tray_state(self) -> None:
        if self.state == "IDLE":
            self.tray_icon.setToolTip("Blitztext")
        elif self.state == "RECORDING":
            wf_name = self.current_workflow.value if self.current_workflow else ""
            self.tray_icon.setToolTip(f"Aufnahme läuft… ({wf_name})")
        elif self.state == "TRANSCRIBING":
            self.tray_icon.setToolTip("Transkribiere…")
        elif self.state == "LLM_REWRITING":
            self.tray_icon.setToolTip("Verarbeite mit KI…")

    @pyqtSlot(str)
    def _on_hotkey_error(self, err_msg: str) -> None:
        logger.error("Hotkey worker error: %s", err_msg)
        self.show_tray_error("Hotkey Fehler", err_msg)

    def show_tray_error(self, title: str, message: str) -> None:
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Critical, 10000)

    def show_tray_warning(self, title: str, message: str) -> None:
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def quit_app(self) -> None:
        logger.info("Quitting application...")
        self.audio_recorder.discard()
        self.stop_hotkey_worker()
        self.tray_icon.hide()
        self.app.quit()


def main() -> int:
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    _require_display_environment()
    _configure_qt_platform()

    try:
        app = QApplication(sys.argv)
    except Exception as exc:
        logging.critical(
            "QApplication init failed (WAYLAND_DISPLAY=%s, DISPLAY=%s): %s",
            os.environ.get("WAYLAND_DISPLAY", "<unset>"),
            os.environ.get("DISPLAY", "<unset>"),
            exc,
        )
        return 1

    app.setApplicationName("Blitztext")
    app.setQuitOnLastWindowClosed(False)

    blitztext = BlitztextApp(app)

    exit_code = app.exec()

    blitztext.stop_hotkey_worker()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
