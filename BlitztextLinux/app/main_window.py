"""Hauptfenster fuer BlitztextLinux (Glass-Redesign).

Grafischer Fallback zum globalen Hotkey: Start/Stopp per Maus-Klick,
Workflow-Auswahl, Verwerfen, Diktat, Verlauf, Vorlesen und Einstellungen.

Das Design folgt dem Blitztext Design System (Glass-Idiom): runder Amber-
Record-„Shutter" als Hero, Status-Punkt + Timer, weiche Pill-Buttons fuer
Verwerfen/Diktat und runde Icon-Buttons fuer Vorlesen/Einstellungen.

Das Fenster ist rein praesentational — die gesamte Aufnahme-/State-Logik
bleibt im Controller (`BlitztextApp`). Beim Schliessen wird es nur versteckt,
die App laeuft im Tray weiter.
"""
from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QRectF
from PyQt6.QtGui import QBrush, QCloseEvent, QColor, QPainter, QPen, QRadialGradient
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
from app import theme

# Reihenfolge der Workflows in der Auswahl
_WORKFLOW_ORDER = [
    WorkflowType.TRANSCRIPTION,
    WorkflowType.LOCAL,
    WorkflowType.TEXT_IMPROVER,
    WorkflowType.DAMPF_ABLASSEN,
    WorkflowType.EMOJI_TEXT,
]


class RecordButton(QPushButton):
    """Runder Aufnahme-„Shutter" im Glass-Idiom.

    Zeichnet einen Mikrofon-/Stop-/Spinner-Glyph auf einer amberfarbenen
    bzw. roten Kreisflaeche. Der Text (`Start`/`Stopp`) bleibt gesetzt, wird
    aber nicht gemalt — so bleibt `text()` fuer Tests/Logik nutzbar.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._mode = "IDLE"  # IDLE | RECORDING | PROCESSING
        self._phase = 0.0
        self.setFixedSize(104, 104)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

        self._anim = QTimer(self)
        self._anim.setInterval(60)
        self._anim.timeout.connect(self._tick)

    def set_mode(self, mode: str) -> None:
        if mode not in ("IDLE", "RECORDING", "PROCESSING"):
            mode = "IDLE"
        self._mode = mode
        if mode in ("RECORDING", "PROCESSING"):
            if not self._anim.isActive():
                self._anim.start()
        else:
            self._anim.stop()
            self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.08) % 1.0
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = min(self.width(), self.height())
        margin = 8
        d = size - 2 * margin
        rect = QRectF(margin, margin, d, d)
        cx, cy = self.width() / 2, self.height() / 2

        if self._mode == "RECORDING":
            base, hi = QColor("#cc2b2b"), QColor("#ef4b4b")
        elif self._mode == "PROCESSING":
            base, hi = QColor("#262a31"), QColor("#3a4049")
        else:
            base, hi = QColor(theme.BLITZ_500), QColor("#f4c542")

        grad = QRadialGradient(cx, margin + d * 0.3, d)
        grad.setColorAt(0.0, hi)
        grad.setColorAt(1.0, base)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(rect)

        # Pulsierender Ring waehrend der Aufnahme (die eine bewusste Animation)
        if self._mode == "RECORDING":
            spread = margin * self._phase
            ring = QRectF(margin - spread, margin - spread,
                          d + 2 * spread, d + 2 * spread)
            alpha = int(150 * (1.0 - self._phase))
            p.setPen(QPen(QColor(229, 72, 72, alpha), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ring)

        p.translate(cx, cy)
        if self._mode == "RECORDING":
            self._draw_stop(p)
        elif self._mode == "PROCESSING":
            self._draw_spinner(p)
        else:
            self._draw_mic(p, QColor("#3a2a04"))
        p.end()

    def _draw_mic(self, p: QPainter, color: QColor) -> None:
        p.setPen(QPen(color, 3.2, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QBrush(color))
        p.drawRoundedRect(QRectF(-7, -17, 14, 22), 7, 7)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(-12, -9, 24, 22).toRect(), 200 * 16, 140 * 16)
        p.drawLine(0, 10, 0, 17)
        p.drawLine(-7, 17, 7, 17)

    def _draw_stop(self, p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(QRectF(-13, -13, 26, 26), 8, 8)

    def _draw_spinner(self, p: QPainter) -> None:
        p.setPen(QPen(QColor(255, 255, 255, 60), 4, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-18, -18, 36, 36))
        p.setPen(QPen(QColor("#ffffff"), 4, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        start = int(-self._phase * 360 * 16)
        p.drawArc(QRectF(-18, -18, 36, 36).toRect(), start, 90 * 16)


class MainWindow(QWidget):
    """Klickbare Oberflaeche fuer Aufnahme-Steuerung und Komfort-Funktionen."""

    def __init__(self, controller, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._state = "IDLE"
        self._rec_start: Optional[float] = None

        self.setWindowTitle("Blitztext")
        self.setFixedWidth(340)
        self.resize(340, 392)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_timer_label)

        self._setup_ui()
        self.update_state("IDLE", None, None)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(16)

        # Workflow-Auswahl (Karten-Pill)
        self._workflow_combo = QComboBox()
        self._workflow_combo.setMinimumHeight(44)
        for wf in _WORKFLOW_ORDER:
            meta = WORKFLOW_META.get(wf, {})
            label = str(meta.get("display_name", wf.value)).strip()
            self._workflow_combo.addItem(label, userData=wf)
        layout.addWidget(self._workflow_combo)

        # Hero: runder Record-Shutter
        self._btn_toggle = RecordButton()
        self._btn_toggle.clicked.connect(self._on_toggle_clicked)
        hero_row = QHBoxLayout()
        hero_row.addStretch()
        hero_row.addWidget(self._btn_toggle)
        hero_row.addStretch()
        layout.addLayout(hero_row)

        # Status: Punkt + Text + Timer
        status_row = QHBoxLayout()
        status_row.setSpacing(7)
        status_row.addStretch()
        self._rec_indicator = QLabel("●")
        self._rec_indicator.setStyleSheet(f"color: {theme.STATE_IDLE}; font-size: 13px;")
        status_row.addWidget(self._rec_indicator)
        self._status_label = QLabel("Bereit")
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        self._timer_label = QLabel("00:00")
        self._timer_label.setStyleSheet(
            "font-size: 16px; font-family: monospace; font-weight: 600; "
            f"color: {theme.APP_TEXT_DIM};"
        )
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._timer_label)

        # Sekundaerzeile: Verwerfen + Diktat (Pills)
        sec_row = QHBoxLayout()
        sec_row.setSpacing(10)
        self._btn_discard = QPushButton("↺  Verwerfen")
        self._btn_discard.setMinimumHeight(42)
        self._btn_discard.setStyleSheet("border-radius: 21px; font-weight: 600;")
        self._btn_discard.setEnabled(False)
        self._btn_discard.clicked.connect(self._on_discard_clicked)
        sec_row.addWidget(self._btn_discard)

        self._btn_dictation = QPushButton("🎤  Diktat")
        self._btn_dictation.setMinimumHeight(42)
        self._btn_dictation.setStyleSheet("border-radius: 21px; font-weight: 600;")
        self._btn_dictation.setCheckable(True)
        self._btn_dictation.clicked.connect(self._on_dictation_clicked)
        sec_row.addWidget(self._btn_dictation)
        layout.addLayout(sec_row)

        # Unterzeile: Verlauf (mit Zaehler), Vorlesen, Einstellungen
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        self._btn_history = QPushButton("📋  Verlauf (0)")
        self._btn_history.setMinimumHeight(40)
        self._btn_history.setStyleSheet("border-radius: 13px;")
        self._btn_history.clicked.connect(self._controller.show_history_panel)
        bottom_row.addWidget(self._btn_history, 1)

        self._btn_tts = QPushButton("🔊")
        self._btn_tts.setFixedSize(40, 40)
        self._btn_tts.setStyleSheet("border-radius: 20px; font-size: 15px;")
        self._btn_tts.setToolTip("Vorlesen")
        self._btn_tts.clicked.connect(self._controller.show_tts_window)
        bottom_row.addWidget(self._btn_tts)

        self._btn_settings = QPushButton("⚙")
        self._btn_settings.setFixedSize(40, 40)
        self._btn_settings.setStyleSheet("border-radius: 20px; font-size: 15px;")
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

        # Text bleibt fuer Tests/Logik gesetzt; der Shutter malt den Glyph.
        self._btn_toggle.setText("Stopp" if recording else "Start")
        self._btn_toggle.setEnabled(state in ("IDLE", "RECORDING"))
        self._btn_toggle.set_mode(
            "RECORDING" if recording else ("PROCESSING" if busy else "IDLE")
        )
        self._btn_discard.setEnabled(recording)
        self._workflow_combo.setEnabled(state == "IDLE")

        if error:
            self._set_status("Fehler", theme.STATE_ERROR)
        elif recording:
            wf_name = workflow.value if workflow else ""
            self._set_status(f"Aufnahme läuft… ({wf_name})", theme.STATE_RECORDING)
        elif state == "TRANSCRIBING":
            self._set_status("Transkribiere…", theme.STATE_PROCESSING)
        elif state == "LLM_REWRITING":
            self._set_status("Verarbeite mit KI…", theme.STATE_PROCESSING)
        else:
            self._set_status("Bereit", theme.STATE_IDLE)

        if recording:
            if self._rec_start is None:
                self._rec_start = time.monotonic()
                self._update_timer_label()
                self._timer.start()
            self._timer_label.setStyleSheet(
                "font-size: 16px; font-family: monospace; font-weight: 600; "
                f"color: {theme.APP_TEXT};"
            )
        else:
            self._timer.stop()
            self._rec_start = None
            self._timer_label.setText("00:00")
            self._timer_label.setStyleSheet(
                "font-size: 16px; font-family: monospace; font-weight: 600; "
                f"color: {theme.APP_TEXT_DIM};"
            )
        _ = busy

    def _set_status(self, text: str, color: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {color};")
        self._rec_indicator.setStyleSheet(f"color: {color}; font-size: 13px;")

    def set_history_count(self, count: int) -> None:
        self._btn_history.setText(f"📋  Verlauf ({count})")

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
