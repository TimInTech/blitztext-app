"""Hauptfenster fuer BlitztextLinux.

Grafischer Fallback zum globalen Hotkey: Start/Stopp per Maus-Klick,
Workflow-Auswahl, Verwerfen, Diktat, Verlauf, Vorlesen und Einstellungen.

Das Fenster ist rein praesentational — die gesamte Aufnahme-/State-Logik
bleibt im Controller (`BlitztextApp`). Beim Schliessen wird es nur versteckt,
die App laeuft im Tray weiter.
"""
from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.llm_service import WorkflowType, LLM_WORKFLOWS
from app.workflows import WORKFLOW_META

# Reihenfolge der Workflows in der Auswahl
_WORKFLOW_ORDER = [
    WorkflowType.TRANSCRIPTION,
    WorkflowType.LOCAL,
    WorkflowType.TEXT_IMPROVER,
    WorkflowType.DAMPF_ABLASSEN,
    WorkflowType.EMOJI_TEXT,
]


class MainWindow(QWidget):
    """Klickbare Oberflaeche fuer Aufnahme-Steuerung und Komfort-Funktionen."""

    def __init__(self, controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._state = "IDLE"
        self._rec_start: Optional[float] = None

        self.setWindowTitle("Blitztext")
        self.resize(360, 260)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_timer_label)

        self._setup_ui()
        self.update_state("IDLE", None, None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Status (zentriert)
        status_row = QHBoxLayout()
        status_row.addStretch()
        self._rec_indicator = QLabel("⬤")  # gefuellter Kreis
        self._rec_indicator.setStyleSheet("color: #c62828; font-size: 14px;")
        self._rec_indicator.setFixedWidth(20)
        self._rec_indicator.hide()
        status_row.addWidget(self._rec_indicator)

        self._status_label = QLabel("Bereit")
        self._status_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet("font-size: 13px; font-family: monospace; color: #888;")
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_label.hide()
        layout.addWidget(self._timer_label)

        # Workflow-Auswahl
        wf_row = QHBoxLayout()
        wf_row.addWidget(QLabel("Workflow:"))
        self._workflow_combo = QComboBox()
        for wf in _WORKFLOW_ORDER:
            meta = WORKFLOW_META.get(wf, {})
            label = str(meta.get("display_name", wf.value)).strip()
            self._workflow_combo.addItem(label, userData=wf)
        wf_row.addWidget(self._workflow_combo, 1)
        layout.addLayout(wf_row)

        # Primaerer Start/Stopp-Button
        self._btn_toggle = QPushButton("Start")
        self._btn_toggle.setMinimumHeight(40)
        self._btn_toggle.setStyleSheet("font-size: 15px; font-weight: bold;")
        self._btn_toggle.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._btn_toggle)

        # Sekundaerzeile: Verwerfen + Diktat
        sec_row = QHBoxLayout()
        sec_row.setSpacing(6)
        self._btn_discard = QPushButton("Verwerfen")
        self._btn_discard.setMinimumHeight(28)
        self._btn_discard.setEnabled(False)
        self._btn_discard.clicked.connect(self._on_discard_clicked)
        sec_row.addWidget(self._btn_discard)

        self._btn_dictation = QPushButton("🎤 Diktat")
        self._btn_dictation.setMinimumHeight(28)
        self._btn_dictation.setCheckable(True)
        self._btn_dictation.clicked.connect(self._on_dictation_clicked)
        sec_row.addWidget(self._btn_dictation)
        layout.addLayout(sec_row)

        # Unterzeile: Verlauf, Vorlesen, Einstellungen
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        self._btn_history = QPushButton("📋 Verlauf (0)")
        self._btn_history.setMinimumHeight(26)
        self._btn_history.clicked.connect(self._controller.show_history_panel)
        bottom_row.addWidget(self._btn_history, 1)

        self._btn_tts = QPushButton("🔊")
        self._btn_tts.setFixedWidth(36)
        self._btn_tts.setMinimumHeight(26)
        self._btn_tts.setToolTip("Vorlesen")
        self._btn_tts.clicked.connect(self._controller.show_tts_window)
        bottom_row.addWidget(self._btn_tts)

        self._btn_settings = QPushButton("⚙")
        self._btn_settings.setFixedWidth(36)
        self._btn_settings.setMinimumHeight(26)
        self._btn_settings.setToolTip("Einstellungen")
        self._btn_settings.clicked.connect(self._controller.show_settings_dialog)
        bottom_row.addWidget(self._btn_settings)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Aktionen
    # ------------------------------------------------------------------

    def _selected_workflow(self) -> WorkflowType:
        wf = self._workflow_combo.currentData()
        return wf if isinstance(wf, WorkflowType) else WorkflowType.TRANSCRIPTION

    @pyqtSlot()
    def _on_toggle_clicked(self) -> None:
        self._controller.gui_toggle_recording(self._selected_workflow())

    @pyqtSlot()
    def _on_discard_clicked(self) -> None:
        self._controller.gui_discard()

    @pyqtSlot()
    def _on_dictation_clicked(self) -> None:
        self._controller.set_dictation_mode(self._btn_dictation.isChecked())

    # ------------------------------------------------------------------
    # Vom Controller aufgerufen
    # ------------------------------------------------------------------

    def update_state(self, state: str, workflow: Optional[WorkflowType], error: Optional[str]) -> None:
        self._state = state
        recording = state == "RECORDING"
        busy = state in ("TRANSCRIBING", "LLM_REWRITING")

        self._btn_toggle.setText("Stopp" if recording else "Start")
        self._btn_toggle.setEnabled(state in ("IDLE", "RECORDING"))
        self._btn_discard.setEnabled(recording)
        self._workflow_combo.setEnabled(state == "IDLE")
        self._rec_indicator.setVisible(recording)

        if error:
            self._status_label.setText("Fehler")
            self._status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #c62828;")
        elif recording:
            wf_name = workflow.value if workflow else ""
            self._status_label.setText(f"Aufnahme läuft… ({wf_name})")
            self._status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #c62828;")
        elif state == "TRANSCRIBING":
            self._status_label.setText("Transkribiere…")
            self._status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef6c00;")
        elif state == "LLM_REWRITING":
            self._status_label.setText("Verarbeite mit KI…")
            self._status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef6c00;")
        else:
            self._status_label.setText("Bereit")
            self._status_label.setStyleSheet("font-size: 15px; font-weight: bold;")

        if recording:
            if self._rec_start is None:
                self._rec_start = time.monotonic()
                self._timer_label.show()
                self._update_timer_label()
                self._timer.start()
        else:
            self._timer.stop()
            self._rec_start = None
            self._timer_label.hide()
        # Waehrend busy nichts blockieren — nur Anzeige
        _ = busy

    def set_history_count(self, count: int) -> None:
        self._btn_history.setText(f"📋 Verlauf ({count})")

    def set_dictation_checked(self, checked: bool) -> None:
        self._btn_dictation.blockSignals(True)
        self._btn_dictation.setChecked(checked)
        self._btn_dictation.blockSignals(False)

    def _update_timer_label(self) -> None:
        if self._rec_start is None:
            return
        elapsed = int(time.monotonic() - self._rec_start)
        self._timer_label.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def closeEvent(self, event: QCloseEvent) -> None:
        # Nicht beenden — nur verstecken; App laeuft im Tray weiter.
        event.ignore()
        self.hide()
