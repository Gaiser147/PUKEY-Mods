"""Inspect an external package before adding its selected mods to the library."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QComboBox)

from .sources import SourceChoices


class ImportDialog(QDialog):
    def __init__(self, store, on_added, parent=None):
        super().__init__(parent)
        self.store, self.on_added = store, on_added
        self.snapshot = None
        self.update_source_id = None
        self.busy = False
        self.setWindowTitle('Add mods')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(680, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Paste a GitHub repository, release or HTTPS ZIP link, or select a local ZIP.'))
        row = QHBoxLayout()
        self.origin = QLineEdit()
        self.origin.setAccessibleName('Mod source')
        self.origin.setPlaceholderText('https://github.com/author/mod')
        row.addWidget(self.origin, 1)
        self.browse = QPushButton('Browse ZIP…')
        self.browse.clicked.connect(self.choose_zip)
        row.addWidget(self.browse)
        self.inspect = QPushButton('Inspect source')
        self.inspect.clicked.connect(self.analyze)
        self.origin.returnPressed.connect(self.analyze)
        row.addWidget(self.inspect)
        layout.addLayout(row)
        self.message = QLabel('Nothing is installed until you choose Install mod in its library tab.')
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.message)
        self.choices = QComboBox()
        self.choices.setAccessibleName('Release or ZIP asset')
        self.choices.hide()
        layout.addWidget(self.choices)
        self.use_choice = QPushButton('Inspect selected release / ZIP')
        self.use_choice.hide()
        self.use_choice.clicked.connect(lambda: self.analyze(self.choices.currentData()))
        layout.addWidget(self.use_choice)
        self.mods = QListWidget()
        self.mods.setAccessibleName('Mods to add')
        self.mods.itemChanged.connect(self.update_add)
        layout.addWidget(self.mods, 1)
        footer = QHBoxLayout()
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.close)
        footer.addWidget(self.close_button)
        footer.addStretch()
        self.add_button = QPushButton('Add selected mods')
        self.add_button.setObjectName('primary')
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self.add_selected)
        footer.addWidget(self.add_button)
        layout.addLayout(footer)
        self.origin.textChanged.connect(self.invalidate)

    def invalidate(self):
        self.snapshot = None
        self.mods.clear()
        self.choices.hide()
        self.use_choice.hide()
        self.update_add()

    def choose_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose a mod ZIP', '', 'Mod archives (*.zip)')
        if path: self.origin.setText(path)

    def update_add(self):
        self.add_button.setEnabled(not self.busy and self.snapshot is not None and
                                   any(self.mods.item(i).checkState() == Qt.CheckState.Checked for i in range(self.mods.count())))

    def start(self, operation, accepted):
        if self.busy: return
        from .gui import Job
        self.busy = True
        for control in (self.origin, self.browse, self.inspect, self.close_button, self.use_choice, self.choices):
            control.setEnabled(False)
        self.update_add()
        self.worker = Job(operation, self)
        worker = self.worker
        worker.progress.connect(self.message.setText)
        worker.result.connect(accepted)
        worker.error.connect(self.message.setText)
        def finished():
            self.busy = False
            for control in (self.origin, self.browse, self.inspect, self.close_button, self.use_choice, self.choices):
                control.setEnabled(True)
            self.update_add()
            worker.deleteLater()
        worker.finished.connect(finished)
        worker.start()

    def analyze(self, origin=None):
        if self.busy: return
        origin = origin if isinstance(origin, str) else self.origin.text().strip()
        if not origin:
            self.message.setText('Enter a source link or select a ZIP first.')
            return
        self.invalidate()
        self.choices.hide()
        self.use_choice.hide()
        self.message.setText('Inspecting package…')
        def inspect(progress):
            try:
                return {'snapshot': self.store.resolve(origin, progress)}
            except SourceChoices as choice:
                return {'choices': choice.choices, 'message': choice.message}
        def accepted(result):
            if 'choices' in result:
                self.message.setText(result['message'])
                self.choices.clear()
                for item in result['choices']: self.choices.addItem(item['label'], item['url'])
                self.choices.show()
                self.use_choice.show()
                return
            self.snapshot = result['snapshot']
            self.analyzed_origin = origin
            for mod in self.snapshot.mods:
                kinds = ', '.join(sorted({point['type'] for point in mod.get('entrypoints', [])})) or 'lua'
                summary = mod['name'] + ' · ' + mod['version'] + ' · ' + kinds
                summary += '\n' + mod.get('description', '')
                summary += '\n' + str(len(mod['files'])) + ' program files'
                if mod.get('author'): summary += ' · by ' + mod['author']
                if mod.get('requires'): summary += '\nAuthor requirements: ' + '; '.join(mod['requires'])
                item = QListWidgetItem(summary)
                item.setData(Qt.ItemDataRole.UserRole, mod['id'])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.mods.addItem(item)
            self.message.setText('Source: ' + origin + '\nSelect the mods to add. Their code runs later inside the game.')
        self.start(inspect, accepted)

    def add_selected(self):
        if self.snapshot is None or self.busy: return
        selected = [self.mods.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.mods.count())
                    if self.mods.item(i).checkState() == Qt.CheckState.Checked]
        snapshot, origin = self.snapshot, self.analyzed_origin
        existing = next((r for r in self.store.records if r['id'] == self.update_source_id or
                         (not self.update_source_id and r['origin'].rstrip('/') == origin.rstrip('/'))), None)
        if existing: selected = list(dict.fromkeys(existing['selected_ids'] + selected))
        def add(progress):
            if existing:
                current = self.store.update(existing['id'], snapshot)
                # Retain existing tabs; also allow selecting newly offered mods.
                self.store.add(current, origin, selected, existing['id'])
                source_id = existing['id']
            else:
                source_id = self.store.add(snapshot, origin, selected)
            return source_id, self.store.load(source_id), selected
        def accepted(result):
            self.on_added(*result)
            self.message.setText('Added to your library. Choose Install mod in each new tab.')
        self.start(add, accepted)

    def reject(self):
        if not self.busy: super().reject()

    def closeEvent(self, event):
        if self.busy:
            self.message.setText('Wait for the source operation to finish before closing.')
            event.ignore()
        else:
            event.accept()
