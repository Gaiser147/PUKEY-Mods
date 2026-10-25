"""Modeless native log viewer with independent, bounded read-only jobs."""
from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout)

from .logs import LogSource, ReadResult, TailReader, discover_log_sources

MAX_RENDER_LINES = 10000
MAX_LINE_CHARS = 16384
MAX_RENDER_CHARS = 2 * 1024 * 1024
# Jobs have no widget parent. Keep them alive until the operating system read
# returns, even when their window or the parent manager has already closed.
_ACTIVE_JOBS = set()


class _ReadJob(QThread):
    result = Signal(int, str, object)

    def __init__(self, generation, kind, operation):
        super().__init__()
        self.generation = generation
        self.kind = kind
        self.operation = operation

    def run(self):
        try:
            result = self.operation()
        except Exception as error:
            result = ReadResult(error=str(error) or type(error).__name__)
        self.result.emit(self.generation, self.kind, result)


def _release_job(job):
    _ACTIVE_JOBS.discard(job)
    job.deleteLater()


class LogsWindow(QDialog):
    def __init__(self, game_root: Path | None, parent=None):
        super().__init__(parent)
        self.game_root = Path(game_root) if game_root is not None else None
        self.setWindowTitle('PUKEY Mod Manager - Logs')
        self.setModal(False)
        self.resize(1000, 680)
        self.setMinimumSize(640, 420)
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())
            self.setFont(parent.font())
        else:
            from .theme import stylesheet
            self.setStyleSheet(stylesheet())
        self._job = None
        self._reader = None
        self._generation = 0
        self._closing = False
        self._discovered = False
        self._needs_poll = False
        self._pending = None
        self._sources = []
        self._lines = deque()
        self._line_chars = 0
        self._partial = ''
        self._partial_truncated = False
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        controls = QHBoxLayout()
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(['UE4SS', 'Game'])
        self.kind_combo.setAccessibleName('Log type')
        self.kind_combo.currentTextChanged.connect(self._populate_sources)
        controls.addWidget(self.kind_combo)
        self.source_combo = QComboBox()
        self.source_combo.setAccessibleName('Log source')
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        controls.addWidget(self.source_combo, 1)
        self.browse_button = QPushButton('Browse log...')
        self.browse_button.clicked.connect(self.browse_log)
        controls.addWidget(self.browse_button)
        self.live_button = QPushButton('Live')
        self.live_button.setCheckable(True)
        self.live_button.setChecked(True)
        self.live_button.setToolTip('Pause or resume reading the selected log')
        self.live_button.toggled.connect(self._live_changed)
        controls.addWidget(self.live_button)
        layout.addLayout(controls)
        self.path_label = QLabel('Choose a log source or browse for a log file.')
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText('Filter visible lines (plain text)')
        self.filter_edit.setAccessibleName('Filter log lines')
        self.filter_edit.textChanged.connect(self._render)
        layout.addWidget(self.filter_edit)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.setMaximumBlockCount(MAX_RENDER_LINES)
        self.text.setAccessibleName('Log contents')
        layout.addWidget(self.text, 1)
        footer = QHBoxLayout()
        self.status = QLabel('Waiting for log sources...')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.autoscroll = QCheckBox('Auto-scroll')
        self.autoscroll.setChecked(True)
        footer.addWidget(self.autoscroll)
        self.copy_button = QPushButton('Copy visible')
        self.copy_button.clicked.connect(self.copy_visible)
        footer.addWidget(self.copy_button)
        self.folder_button = QPushButton('Open folder')
        self.folder_button.clicked.connect(self.open_folder)
        footer.addWidget(self.folder_button)
        layout.addLayout(footer)

    def showEvent(self, event):
        super().showEvent(event)
        reopening = self._closing
        self._closing = False
        if reopening and self._discovered:
            # A finished read while hidden may have advanced its cursor. Reload
            # the bounded tail instead of silently losing those log lines.
            self._source_changed()
        if self.live_button.isChecked():
            self._timer.start()
            self._tick()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closing = True
        self._timer.stop()
        super().closeEvent(event)

    def _live_changed(self, live):
        self.live_button.setText('Live' if live else 'Paused')
        if live and self.isVisible():
            if self._pending is not None:
                self._apply_result(self._pending)
                self._pending = None
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()
            if not live:
                self.status.setText('Paused - log reading is stopped')

    def _start(self, kind, operation):
        job = _ReadJob(self._generation, kind, operation)
        self._job = job
        _ACTIVE_JOBS.add(job)
        job.result.connect(self._receive)
        job.finished.connect(self._finished)
        job.finished.connect(lambda: _release_job(job))
        job.start()

    def _tick(self):
        if self._closing or not self.isVisible() or not self.live_button.isChecked() or self._job is not None:
            return
        if not self._discovered:
            self._start('discover', lambda: discover_log_sources(self.game_root))
        elif self._reader is not None:
            self._start('read', self._reader.poll)

    def _receive(self, generation, kind, result):
        if self._closing or generation != self._generation:
            return
        if kind == 'discover':
            self._discovered = True
            if isinstance(result, ReadResult):
                self.status.setText('Could not discover logs: ' + result.error)
                return
            self._sources = result
            self._populate_sources()
        elif not self.live_button.isChecked():
            self._pending = result
        else:
            self._apply_result(result)

    def _finished(self):
        self._job = None
        if self._needs_poll and not self._closing:
            self._needs_poll = False
            QTimer.singleShot(0, self._tick)

    def _populate_sources(self):
        if not hasattr(self, 'source_combo'):
            return
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for source in self._sources:
            if source.kind == self.kind_combo.currentText():
                self.source_combo.addItem(source.label, source.path)
        self.source_combo.blockSignals(False)
        self._source_changed()

    def _source_changed(self):
        self._generation += 1
        path = self.source_combo.currentData()
        self._reader = TailReader(path) if path is not None else None
        self._pending = None
        self._clear_content()
        self._render()
        self.path_label.setText(str(path) if path is not None else 'No source found. Browse for a log file.')
        self.status.setText('Waiting for log file...' if path else 'No log source found. Browse for a log file.')
        self._needs_poll = self._job is not None
        self._tick()

    def _clear_content(self):
        self._lines.clear()
        self._line_chars = 0
        self._partial = ''
        self._partial_truncated = False

    def _append(self, text):
        marker = ' [line truncated]'
        for piece in text.splitlines(keepends=True):
            complete = piece.endswith(('\n', '\r'))
            content = piece.rstrip('\r\n') if complete else piece
            if not self._partial_truncated:
                self._partial += content
                if len(self._partial) > MAX_LINE_CHARS:
                    self._partial = self._partial[:MAX_LINE_CHARS - len(marker)] + marker
                    self._partial_truncated = True
            if complete:
                self._lines.append(self._partial)
                self._line_chars += len(self._partial)
                self._partial = ''
                self._partial_truncated = False
            while self._lines and (len(self._lines) >= MAX_RENDER_LINES or
                                   self._line_chars + len(self._partial) > MAX_RENDER_CHARS):
                self._line_chars -= len(self._lines.popleft())

    def _apply_result(self, result):
        if result.reset:
            self._clear_content()
        if result.text:
            self._append(result.text)
        if result.reset or result.text:
            self._render()
        if result.error:
            self.status.setText('Could not read log: ' + result.error)
        elif result.missing:
            self.status.setText('Waiting for log file to be created...')
        elif not self._lines and not self._partial:
            self.status.setText('Log is empty. Waiting for new lines...')
        else:
            self.status.setText('Live - showing the latest bounded log lines' if self.live_button.isChecked() else 'Paused')

    def _render(self):
        scrollbar = self.text.verticalScrollBar()
        previous = scrollbar.value()
        at_bottom = previous >= scrollbar.maximum() - 2
        query = self.filter_edit.text().casefold()
        lines = list(self._lines)
        if self._partial:
            lines.append(self._partial)
        visible = [line for line in lines if query in line.casefold()]
        self.text.setPlainText('\n'.join(visible))
        if self.autoscroll.isChecked() and at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(previous)

    def copy_visible(self):
        QApplication.clipboard().setText(self.text.toPlainText())

    def browse_log(self):
        start = self.source_combo.currentData() or self.game_root or Path.home()
        filename, _ = QFileDialog.getOpenFileName(self, 'Browse log', str(start), 'Log files (*.log *.txt);;All files (*)')
        if filename:
            path = Path(filename)
            self._sources.append(LogSource(self.kind_combo.currentText(), 'Browsed: ' + path.name, path))
            self._populate_sources()
            self.source_combo.setCurrentIndex(self.source_combo.count() - 1)

    def open_folder(self):
        path = self.source_combo.currentData()
        folder = Path(path).parent if path else self.game_root
        if folder is None:
            return
        while not folder.is_dir() and folder.parent != folder:
            folder = folder.parent
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.absolute())))
