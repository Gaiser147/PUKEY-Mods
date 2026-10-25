"""Native desktop interface. All downloads and mutations run in a worker."""
import json
import os
from decimal import Decimal
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QCloseEvent, QFontDatabase, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QListWidget, QListWidgetItem,
    QScrollArea, QFormLayout, QDoubleSpinBox, QComboBox,
    QCheckBox, QTabWidget, QProgressBar, QMessageBox, QFrame,
)

from . import __version__
from .theme import STYLE
from .widgets import icon, mod_icon, ModDelegate, PreviewCanvas

REPOSITORY = 'https://github.com/Gaiser147/PUKEY-Mods'
PROTON_OPTION = 'WINEDLLOVERRIDES="dwmapi.dll=n,b" %command%'
KEYS = ([f'F{i}' for i in range(1, 13)] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') +
        ['HOME', 'END', 'PAGE_UP', 'PAGE_DOWN', 'INSERT', 'DELETE', 'SPACE',
         'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'])


class Job(QThread):
    progress = Signal(str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.result.emit(self.operation(self.progress.emit))
        except Exception as error:
            self.error.emit(str(error) or type(error).__name__)


def text_label(text='', name=None):
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(True)
    if name:
        label.setObjectName(name)
    return label


class Window(QMainWindow):
    def __init__(self, snapshot=None, preferences_path=None, start_online=True):
        super().__init__()
        # The offscreen platform on Windows does not populate the system font database.
        if not QFontDatabase.families():
            candidates = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/segoeui.ttf',
                          Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
            for candidate in candidates:
                if candidate.is_file():
                    font_id = QFontDatabase.addApplicationFont(str(candidate))
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        QApplication.setFont(QFont(families[0], 10))
                        break
        self.setWindowTitle('PUKEY Mod Manager')
        self.resize(1120, 800)
        self.setMinimumSize(900, 640)
        self.snapshot = snapshot
        self.manager = None
        self.current_mod = None
        self.settings_widgets = {}
        self._busy = False
        self._dirty = False
        self._job = None
        self._settings_error = False
        self._state_error = None
        self._image_bytes = None
        self._image_target = None
        self.preferences_path = preferences_path or Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / 'preferences.json'
        self.cache_dir = self.preferences_path.parent / 'cache'
        self._build()
        self.setStyleSheet(STYLE)
        if self.snapshot:
            self.source_label.setText('Local catalogue')
            self.populate()
        else:
            self.render_details()
        if start_online:
            QTimer.singleShot(0, self.startup)

    def _build(self):
        body = QWidget()
        self.setCentralWidget(body)
        shell = QHBoxLayout(body)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(236)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(12, 26, 12, 18)
        rail.setSpacing(12)
        brand = QHBoxLayout()
        brand.setContentsMargins(12, 0, 8, 0)
        mark = text_label('P', 'brandMark')
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(42, 42)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_text.addWidget(text_label('PUKEY', 'brandName'))
        brand_text.addWidget(text_label('Mod Manager', 'sidebarMuted'))
        brand.addLayout(brand_text, 1)
        rail.addLayout(brand)
        rail.addSpacing(24)
        library = QHBoxLayout()
        library.setContentsMargins(14, 0, 14, 0)
        library.addWidget(text_label('Your library', 'libraryLabel'), 1)
        self.mod_count = text_label('0', 'sidebarMuted')
        library.addWidget(self.mod_count)
        rail.addLayout(library)
        self.mod_list = QListWidget()
        self.mod_list.setObjectName('modNavigation')
        self.mod_list.setAccessibleName('Available mods')
        self.mod_list.setItemDelegate(ModDelegate(self.mod_list))
        self.mod_list.setMouseTracking(True)
        self.mod_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mod_list.currentRowChanged.connect(self.select_mod)
        rail.addWidget(self.mod_list, 1)
        self.nav_empty = text_label('Refresh the catalogue to discover your mods.', 'sidebarMuted')
        self.nav_empty.setContentsMargins(14, 0, 14, 8)
        rail.addWidget(self.nav_empty)
        self.source_label = text_label('Catalogue not loaded', 'sidebarMuted')
        self.source_label.setContentsMargins(12, 0, 8, 0)
        rail.addWidget(self.source_label)
        self.refresh_button = QPushButton('Refresh catalogue')
        self.refresh_button.setObjectName('sideRefresh')
        self.refresh_button.setIcon(icon('refresh', '#ffffff'))
        self.refresh_button.setShortcut('Ctrl+R')
        self.refresh_button.clicked.connect(self.refresh_catalogue)
        rail.addWidget(self.refresh_button)
        self.cached_button = QPushButton('Use offline copy')
        self.cached_button.setObjectName('sideLink')
        self.cached_button.setToolTip('Open the last downloaded catalogue without a connection')
        self.cached_button.clicked.connect(self.use_cached)
        rail.addWidget(self.cached_button)
        rail.addSpacing(8)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(12, 0, 4, 0)
        bottom.addWidget(text_label('v' + __version__, 'sidebarMuted'), 1)
        repo = QPushButton('GitHub')
        repo.setObjectName('sideLink')
        repo.setIcon(icon('link', '#b8bdb0'))
        repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPOSITORY)))
        bottom.addWidget(repo)
        rail.addLayout(bottom)
        shell.addWidget(sidebar)

        workspace = QWidget()
        workspace.setObjectName('mainWorkspace')
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(28, 24, 28, 12)
        outer.setSpacing(18)
        game = QFrame()
        game.setObjectName('gamePanel')
        game_layout = QVBoxLayout(game)
        game_layout.setContentsMargins(14, 11, 14, 12)
        game_layout.setSpacing(8)
        heading = QHBoxLayout()
        heading.addWidget(text_label('Game folder', 'sectionTitle'), 1)
        self.loader_icon = QLabel()
        self.loader_icon.setFixedSize(16, 16)
        heading.addWidget(self.loader_icon)
        self.loader_label = text_label('Choose a game folder', 'muted')
        heading.addWidget(self.loader_label)
        self.loader_button = QPushButton('Install UE4SS')
        self.loader_button.setIcon(icon('download'))
        self.loader_button.clicked.connect(self.install_loader)
        heading.addWidget(self.loader_button)
        game_layout.addLayout(heading)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText('Select your PUKEY Steam installation')
        self.path_edit.setAccessibleName('Game folder')
        self.path_edit.editingFinished.connect(self.accept_typed_path)
        path_row.addWidget(self.path_edit, 1)
        self.browse_button = QPushButton('Browse…')
        self.browse_button.setIcon(icon('folder'))
        self.browse_button.setShortcut('Ctrl+O')
        self.browse_button.clicked.connect(self.browse_game)
        path_row.addWidget(self.browse_button)
        self.detect_button = QPushButton('Find in Steam')
        self.detect_button.clicked.connect(self.detect_games)
        path_row.addWidget(self.detect_button)
        game_layout.addLayout(path_row)
        if sys.platform.startswith('linux'):
            proton = QHBoxLayout()
            proton.addWidget(text_label('Proton requires a Steam launch option.', 'muted'), 1)
            copy = QPushButton('Copy launch option')
            copy.clicked.connect(lambda: QApplication.clipboard().setText(PROTON_OPTION))
            proton.addWidget(copy)
            game_layout.addLayout(proton)
        outer.addWidget(game)

        self.mod_header = QWidget()
        header = QHBoxLayout(self.mod_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        self.mod_icon_label = QLabel()
        self.mod_icon_label.setObjectName('modIcon')
        self.mod_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mod_icon_label.setFixedSize(52, 52)
        header.addWidget(self.mod_icon_label)
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self.mod_title = text_label('Your mods', 'modTitle')
        title_block.addWidget(self.mod_title)
        self.mod_status_label = text_label('Select a mod to get started', 'modStatus')
        title_block.addWidget(self.mod_status_label)
        header.addLayout(title_block, 1)
        self.install_button = QPushButton('Install mod')
        self.install_button.setIcon(icon('download'))
        self.install_button.clicked.connect(self.install_current)
        header.addWidget(self.install_button)
        self.enabled_checkbox = QPushButton('Disabled')
        self.enabled_checkbox.setObjectName('activation')
        self.enabled_checkbox.setCheckable(True)
        self.enabled_checkbox.toggled.connect(self.toggle_current)
        header.addWidget(self.enabled_checkbox)
        self.guide_button = QPushButton()
        self.guide_button.setObjectName('iconAction')
        self.guide_button.setFixedSize(38, 38)
        self.guide_button.setIcon(icon('book'))
        self.guide_button.setToolTip('Open mod guide')
        self.guide_button.setAccessibleName('Open mod guide')
        self.guide_button.clicked.connect(self.open_guide)
        header.addWidget(self.guide_button)
        self.remove_button = QPushButton()
        self.remove_button.setObjectName('iconAction')
        self.remove_button.setFixedSize(38, 38)
        self.remove_button.setIcon(icon('trash'))
        self.remove_button.setAccessibleName('Remove mod')
        self.remove_button.clicked.connect(self.remove_current)
        header.addWidget(self.remove_button)
        outer.addWidget(self.mod_header)
        self.description = text_label('Connect the catalogue, then choose your game folder to start.', 'muted')
        outer.addWidget(self.description)
        self.controls_label = None
        self.tabs = QTabWidget()
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.keys_scroll = QScrollArea()
        self.keys_scroll.setWidgetResizable(True)
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.tabs.addTab(self.settings_scroll, 'Settings')
        self.tabs.currentChanged.connect(lambda index: self.update_controls())
        outer.addWidget(self.tabs, 1)
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setSpacing(12)
        empty_layout.addStretch()
        empty_icon = QLabel()
        empty_icon.setPixmap(icon('package', '#595c53').pixmap(48, 48))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        self.empty_heading = text_label('Set up your mod library', 'emptyTitle')
        self.empty_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_heading)
        setup_hint = text_label('Find your Steam game folder above.\nRefresh the catalogue to load the available mods.', 'muted')
        setup_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(setup_hint)
        empty_layout.addStretch()
        outer.addWidget(self.empty_state, 1)

        footer = QFrame()
        self.detail_footer = footer
        footer.setObjectName('detailFooter')
        self.save_row = QHBoxLayout(footer)
        self.save_row.setContentsMargins(0, 14, 0, 0)
        self.unsaved_label = text_label('Restart the game after applying changes.', 'muted')
        self.save_row.addWidget(self.unsaved_label, 1)
        self.apply_footer_button = QPushButton('Use preview image')
        self.apply_footer_button.setObjectName('primary')
        self.apply_footer_button.setIcon(icon('check'))
        self.apply_footer_button.clicked.connect(self.apply_image)
        self.apply_footer_button.hide()
        self.save_row.addWidget(self.apply_footer_button)
        self.save_button = QPushButton('Save settings')
        self.save_button.setObjectName('primary')
        self.save_button.setIcon(icon('check'))
        self.save_button.setShortcut('Ctrl+S')
        self.save_button.clicked.connect(self.save_settings)
        self.save_row.addWidget(self.save_button)
        outer.addWidget(footer)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.hide()
        outer.addWidget(self.progress_bar)
        self.status_label = text_label('Ready. Personal files are kept during updates.', 'operationStatus')
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setMinimumHeight(26)
        outer.addWidget(self.status_label)
        shell.addWidget(workspace, 1)
        self.update_controls()

    def notice(self, message, error=False):
        self.status_label.setText(message)
        self.status_label.setStyleSheet('color: #a52b2b;' if error else '')

    def run_job(self, label, operation, callback=None):
        if self._busy:
            return
        self._busy = True
        self.notice(label)
        self.progress_bar.show()
        self.update_controls()
        worker = Job(operation, self)
        self._job = worker
        worker.progress.connect(self.notice)
        worker.error.connect(lambda message: self.notice(message + ' Check the folder or connection and try again.', True))
        def success(value):
            try:
                if callback:
                    callback(value)
                else:
                    if self._dirty:
                        self.refresh_status_rows()
                    else:
                        self.populate()
                    self.notice('Done. Restart the game to apply changes.')
            except Exception as error:
                self.notice(str(error), True)
        worker.result.connect(success)
        def finished():
            self._busy = False
            self._job = None
            self.progress_bar.hide()
            self.update_controls()
            worker.deleteLater()
        worker.finished.connect(finished)
        worker.start()

    def startup(self):
        try:
            preferences = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            if preferences.get('game'):
                self.set_game(Path(preferences['game']))
        except (OSError, ValueError, TypeError):
            pass
        self.refresh_catalogue()

    def refresh_catalogue(self):
        from .catalog import fetch_latest
        if not self.allow_discard():
            return
        self.run_job('Checking GitHub for mods…', lambda progress: fetch_latest(self.cache_dir, progress), self.accept_snapshot)

    def use_cached(self):
        from .catalog import load_cached
        if not self.allow_discard():
            return
        def accepted(snapshot):
            self.accept_snapshot(snapshot)
            self.source_label.setText('Offline catalogue')
            self.notice('Using the last downloaded catalogue. Refresh when you are online to check for updates.')
        self.run_job('Opening cached catalogue…', lambda progress: load_cached(self.cache_dir), accepted)

    def accept_snapshot(self, snapshot):
        self.snapshot = snapshot
        if self.manager:
            self.manager.snapshot = snapshot
        self.source_label.setText('Catalogue from GitHub')
        self.source_label.setToolTip('Repository snapshot: ' + snapshot.revision)
        self.populate()
        self.notice('Catalogue updated. Select a mod to install or configure it.')
        if self.manager is None:
            QTimer.singleShot(100, self.detect_games)

    def detect_games(self):
        from .platforms import find_games
        if self._busy:
            QTimer.singleShot(100, self.detect_games)
            return
        def detected(games):
            if len(games) == 1:
                self.set_game(games[0])
                self.notice('Found your Steam installation. Select a mod to continue.')
            elif games:
                self.notice('Multiple installations found. Use Browse to choose one: ' + '; '.join(map(str, games)))
            else:
                self.notice('No Steam installation found. Use Browse to select the game folder.')
        self.run_job('Looking for the game in Steam libraries…', lambda progress: find_games(), detected)

    def browse_game(self):
        path = QFileDialog.getExistingDirectory(self, 'Select PUKEY game folder', self.path_edit.text())
        if path:
            self.try_game(Path(path))

    def accept_typed_path(self):
        if not self._busy and self.path_edit.text().strip():
            self.try_game(Path(self.path_edit.text().strip().strip('"')))

    def try_game(self, path):
        if not self.allow_discard():
            return
        try:
            self.set_game(path)
            self.notice('Game folder selected. Installed mods are detected automatically.')
        except Exception as error:
            self.notice(str(error), True)

    def set_game(self, path):
        from .service import Manager
        manager = Manager(path, self.snapshot)
        self.manager = manager
        self.path_edit.setText(str(path))
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.preferences_path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'game': str(path)}), encoding='utf-8')
        temporary.replace(self.preferences_path)
        self.populate()

    def mod_status(self, mod):
        if self.manager:
            try:
                return self.manager.status(mod)
            except Exception as error:
                self._state_error = str(error)
                self.notice('Installation configuration could not be read: ' + str(error), True)
        return {'installed': False, 'enabled': False, 'update': False, 'version': '', 'managed': False}

    def populate(self):
        self._state_error = None
        selected = self.current_mod['id'] if self.current_mod else None
        self.mod_list.blockSignals(True)
        self.mod_list.clear()
        chosen = 0
        for index, mod in enumerate(self.snapshot.mods if self.snapshot else []):
            state = self.mod_status(mod)
            status = ('Update available' if state['update'] else
                      'Enabled' if state['installed'] and state['enabled'] else
                      'Disabled' if state['installed'] else 'Not installed')
            item = QListWidgetItem(mod['name'] + '\n' + status)
            item.setData(Qt.ItemDataRole.UserRole, mod)
            self.mod_list.addItem(item)
            if mod['id'] == selected:
                chosen = index
        self.mod_list.setCurrentRow(chosen if self.mod_list.count() else -1)
        self.mod_list.blockSignals(False)
        self._dirty = False
        self.current_mod = self.mod_list.currentItem().data(Qt.ItemDataRole.UserRole) if self.mod_list.currentItem() else None
        self.render_details()

    def refresh_status_rows(self):
        """Update installation status without rebuilding forms with unsaved edits."""
        for index in range(self.mod_list.count()):
            item = self.mod_list.item(index)
            mod = item.data(Qt.ItemDataRole.UserRole)
            state = self.mod_status(mod)
            status = ('Update available' if state['update'] else
                      'Enabled' if state['installed'] and state['enabled'] else
                      'Disabled' if state['installed'] else 'Not installed')
            item.setText(mod['name'] + '\n' + status)
        self.update_controls()

    def allow_discard(self):
        if not self._dirty:
            return True
        answer = QMessageBox.question(self, 'Unsaved settings', 'Discard your unsaved settings?',
                                      QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Discard:
            self._dirty = False
            return True
        return False

    def select_mod(self, row):
        previous = self.current_mod
        if not self.allow_discard():
            self.mod_list.blockSignals(True)
            for index in range(self.mod_list.count()):
                if self.mod_list.item(index).data(Qt.ItemDataRole.UserRole)['id'] == previous['id']:
                    self.mod_list.setCurrentRow(index)
            self.mod_list.blockSignals(False)
            return
        item = self.mod_list.item(row)
        self.current_mod = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.render_details()

    def render_details(self):
        self.settings_widgets = {}
        self._settings_error = False
        self._dirty = False
        self._image_bytes = None
        self._image_target = None
        mod = self.current_mod
        self.mod_title.setText(mod['name'] if mod else 'Your mod library')
        self.mod_icon_label.setPixmap(mod_icon(mod or {}).pixmap(30, 30))
        self.description.setText(mod['description'] if mod else 'Refresh the catalogue to discover mods, then choose your game folder to begin.')
        self.settings_page = QWidget()
        self.keys_page = QWidget()
        preferences = QVBoxLayout(self.settings_page)
        bindings = QVBoxLayout(self.keys_page)
        for layout in (preferences, bindings):
            layout.setContentsMargins(0, 10, 12, 12)
            layout.setSpacing(0)
        defaults = {field['key']: field['default'] for field in mod.get('settings', [])} if mod else {}
        if mod and self.manager:
            try:
                defaults = self.manager.settings(mod)
            except Exception as error:
                self._settings_error = True
                self.notice(str(error) + ' Settings were not overwritten.', True)
        general_count = key_count = 0
        for field in mod.get('settings', []) if mod else []:
            value = defaults.get(field['key'], field['default'])
            if field['type'] == 'boolean':
                widget = QCheckBox('On' if value else 'Off')
                widget.setChecked(bool(value))
                widget.toggled.connect(lambda checked, target=widget: target.setText('On' if checked else 'Off'))
                widget.toggled.connect(self.mark_dirty)
            elif field['type'] == 'number':
                widget = QDoubleSpinBox()
                numbers = [field['min'], field['max'], field['default'], field.get('step', 1), value]
                digits = max(max(0, -Decimal(str(number)).normalize().as_tuple().exponent) for number in numbers)
                widget.setDecimals(min(16, digits))
                widget.setRange(field['min'], field['max'])
                widget.setSingleStep(field.get('step', 1))
                widget.setValue(value)
                widget.valueChanged.connect(self.mark_dirty)
            else:
                widget = QComboBox()
                widget.addItems(KEYS if field['type'] == 'key' else field['options'])
                widget.setCurrentText(str(value))
                widget.currentTextChanged.connect(self.mark_dirty)
            widget.setAccessibleName(field['label'])
            widget.setToolTip('Default: ' + str(field['default']))
            widget.setFixedWidth(200)
            row = QWidget()
            row.setObjectName('fieldRow')
            row.setMinimumHeight(64)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 11, 0, 11)
            row_layout.setSpacing(20)
            label = text_label(field['label'])
            label.setBuddy(widget)
            row_layout.addWidget(label, 1)
            row_layout.addWidget(widget)
            if field['type'] == 'key':
                bindings.addWidget(row)
                key_count += 1
            else:
                preferences.addWidget(row)
                general_count += 1
            self.settings_widgets[field['key']] = widget
        if not general_count:
            preferences.addWidget(text_label('This mod has no adjustable preferences.' if mod else 'No mod selected.', 'muted'))
        preferences.addStretch()
        if mod and mod.get('controls'):
            bindings.addSpacing(20)
            bindings.addWidget(text_label('Default controls', 'sectionTitle'))
            bindings.addSpacing(8)
            self.controls_label = text_label(mod['controls'], 'muted')
            bindings.addWidget(self.controls_label)
        else:
            self.controls_label = text_label('', 'muted')
        bindings.addStretch()
        self.settings_scroll.setWidget(self.settings_page)
        self.keys_scroll.setWidget(self.keys_page)
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        if mod and (key_count or mod.get('controls')):
            self.tabs.addTab(self.keys_scroll, 'Keybindings')
        if mod and (mod.get('images') or mod.get('video_list')):
            self.build_media(mod)
            self.tabs.addTab(self.media_scroll, 'Images' if mod.get('images') else 'Videos')
        self.unsaved_label.setText('Restart the game after applying changes.')
        self.mod_count.setText(str(self.mod_list.count()))
        self.nav_empty.setVisible(self.mod_list.count() == 0)
        self.update_controls()

    def mark_dirty(self, *args):
        self._dirty = True
        self.unsaved_label.setText('Unsaved settings')
        self.update_controls()

    def update_controls(self):
        ready = not self._busy
        has_mod = self.current_mod is not None
        self.mod_header.setVisible(has_mod)
        self.description.setVisible(has_mod)
        self.tabs.setVisible(has_mod)
        self.detail_footer.setVisible(has_mod)
        self.empty_state.setVisible(not has_mod)
        self.empty_heading.setText('Preparing your library…' if self._busy else 'Set up your mod library')
        for widget in [self.refresh_button, self.cached_button, self.browse_button, self.detect_button, self.path_edit, self.mod_list]:
            widget.setEnabled(ready)
        state = self.mod_status(self.current_mod) if self.current_mod else {'installed': False, 'enabled': False}
        installed = state['installed']
        loader = bool(self.manager and (self.manager.win64 / 'dwmapi.dll').is_file() and
                      (self.manager.win64 / 'ue4ss/UE4SS.dll').is_file())
        self.loader_label.setText('UE4SS ready' if loader else 'UE4SS required' if self.manager else 'Choose a game folder')
        self.loader_label.setStyleSheet('color: #31633e;' if loader else '')
        self.loader_icon.setPixmap(icon('check' if loader else 'folder', '#31633e' if loader else '#595c53').pixmap(16, 16))
        self.loader_button.setText('UE4SS ready' if loader else 'Install UE4SS')
        writable = ready and not self._state_error
        self.loader_button.setEnabled(writable and self.manager is not None and not loader)
        self.loader_button.setVisible(self.manager is not None and not loader)
        for button, prominent in ((self.detect_button, self.manager is None),
                                  (self.install_button, bool(state.get('update') or not installed))):
            if button.property('prominent') != prominent:
                button.setProperty('prominent', prominent)
                button.style().unpolish(button)
                button.style().polish(button)
        self.install_button.setText('Update mod' if state.get('update') else 'Reinstall mod' if installed else 'Install mod')
        self.install_button.setEnabled(writable and loader and self.current_mod is not None and self.snapshot is not None)
        self.enabled_checkbox.blockSignals(True)
        self.enabled_checkbox.setChecked(state['enabled'])
        self.enabled_checkbox.setText('Enabled' if state['enabled'] else 'Disabled')
        self.enabled_checkbox.setIcon(icon('power', '#31633e' if state['enabled'] else '#595c53'))
        self.enabled_checkbox.blockSignals(False)
        self.enabled_checkbox.setEnabled(writable and installed)
        self.remove_button.setEnabled(writable and installed and state.get('managed', False))
        self.remove_button.setToolTip('Removes tracked program files; personal files remain.' if state.get('managed') else
                                      'Reinstall once to track this manually installed mod before removing its program files.')
        self.guide_button.setEnabled(ready and self.current_mod is not None)
        self.save_button.setEnabled(ready and installed and bool(self.settings_widgets) and not self._settings_error and self._dirty)
        image_tab = bool(self.current_mod and self.current_mod.get('images') and self.tabs.currentWidget() == self.media_scroll)
        self.save_button.setVisible(self.tabs.currentWidget() in (self.settings_scroll, self.keys_scroll))
        self.apply_footer_button.setVisible(image_tab)
        self.apply_footer_button.setEnabled(ready and installed and self._image_bytes is not None)
        if hasattr(self, 'settings_page'):
            self.settings_page.setEnabled(ready and installed and not self._settings_error)
        if hasattr(self, 'keys_page'):
            self.keys_page.setEnabled(ready and installed and not self._settings_error)
        self.media_scroll.setEnabled(ready and installed)
        if not self.current_mod:
            status = 'Choose a mod from your library'
        elif not installed:
            status = 'Not installed'
        elif not state.get('managed'):
            status = 'Installed manually'
        else:
            status = 'Installed'
            if state.get('version'):
                status += ' · v' + state['version']
            if state.get('update'):
                status += ' · update available'
        self.mod_status_label.setText(status)

    def install_current(self):
        if self.current_mod and self.allow_discard():
            mod, manager = self.current_mod, self.manager
            self.run_job('Installing ' + mod['name'] + '…', lambda progress: manager.install(mod, progress))

    def toggle_current(self, enabled):
        if self.current_mod and self.manager and not self._busy:
            mod, manager = self.current_mod, self.manager
            self.run_job('Updating mod activation…', lambda progress: manager.set_enabled(mod, enabled))

    def remove_current(self):
        if not self.current_mod or not self.allow_discard():
            return
        answer = QMessageBox.question(self, 'Remove ' + self.current_mod['name'],
            'Remove this mod’s program files? Your images, videos, settings and camera bookmarks will be kept.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            mod, manager = self.current_mod, self.manager
            self.run_job('Removing mod program files…', lambda progress: manager.remove(mod))

    def save_settings(self):
        if not self.current_mod or not self.save_button.isEnabled():
            return
        values = {}
        for key, widget in self.settings_widgets.items():
            values[key] = (widget.isChecked() if isinstance(widget, QCheckBox) else
                           widget.value() if isinstance(widget, QDoubleSpinBox) else widget.currentText())
        mod, manager = self.current_mod, self.manager
        def saved(result):
            self._dirty = False
            self.populate()
            self.notice('Settings saved. Restart the game to apply them.')
        self.run_job('Saving settings…', lambda progress: manager.save_settings(mod, values), saved)

    def install_loader(self):
        if self.manager:
            manager = self.manager
            self.run_job('Downloading UE4SS from its official release…', lambda progress: manager.install_loader(progress))

    def open_guide(self):
        if self.current_mod:
            QDesktopServices.openUrl(QUrl(REPOSITORY + '/tree/main/Mods/' + self.current_mod['id']))

    def build_media(self, mod):
        page = QWidget()
        if mod.get('images'):
            layout = QHBoxLayout(page)
            layout.setContentsMargins(0, 12, 10, 6)
            layout.setSpacing(22)
            options = QWidget()
            options.setObjectName('imageControls')
            options.setMinimumWidth(270)
            options.setMaximumWidth(310)
            controls = QVBoxLayout(options)
            controls.setContentsMargins(0, 0, 0, 0)
            controls.setSpacing(4)
            controls.addWidget(text_label('Replace', 'sectionTitle'))
            self.image_targets = QComboBox()
            self.image_targets.setAccessibleName('Image target')
            for target in mod['images']:
                self.image_targets.addItem(target['label'], target)
            controls.addWidget(self.image_targets)
            controls.addWidget(text_label('Source image', 'sectionTitle'))
            source_row = QHBoxLayout()
            source_row.setSpacing(6)
            self.image_source = QLineEdit()
            self.image_source.setReadOnly(True)
            self.image_source.setPlaceholderText('PNG, WebP or JPEG')
            self.image_source.setAccessibleName('Source image')
            source_row.addWidget(self.image_source, 1)
            choose = QPushButton('Choose…')
            choose.setIcon(icon('folder'))
            choose.clicked.connect(self.choose_image)
            source_row.addWidget(choose)
            controls.addLayout(source_row)
            adjustments = QFormLayout()
            adjustments.setVerticalSpacing(8)
            adjustments.setHorizontalSpacing(12)
            self.image_scale = QDoubleSpinBox()
            self.image_scale.setRange(1, 500)
            self.image_scale.setSuffix(' %')
            self.image_top = QDoubleSpinBox()
            self.image_top.setRange(-100, 100)
            self.image_top.setSuffix(' %')
            self.image_x = QDoubleSpinBox()
            self.image_x.setRange(-100, 100)
            self.image_x.setSuffix(' %')
            self.remove_green = QCheckBox('Remove green screen')
            for label, widget in [('Size', self.image_scale), ('Top offset', self.image_top), ('Horizontal offset', self.image_x)]:
                widget.setAccessibleName(label)
                widget.setFixedWidth(112)
                adjustments.addRow(label, widget)
                widget.valueChanged.connect(self.invalidate_preview)
            controls.addLayout(adjustments)
            self.remove_green.toggled.connect(self.invalidate_preview)
            controls.addWidget(self.remove_green)
            buttons = QHBoxLayout()
            buttons.setSpacing(6)
            preview = QPushButton('Preview')
            self.preview_button = preview
            preview.setIcon(icon('eye'))
            preview.clicked.connect(self.preview_image)
            buttons.addWidget(preview)
            restore = QPushButton('Restore')
            self.restore_image_button = restore
            restore.setIcon(icon('undo'))
            restore.setToolTip('Restore the original image after backing up your replacement')
            restore.clicked.connect(lambda: self.restore_media(self.image_targets.currentData()['file']))
            buttons.addWidget(restore)
            controls.addLayout(buttons)
            controls.addStretch()
            layout.addWidget(options)
            preview_area = QWidget()
            preview_layout = QVBoxLayout(preview_area)
            preview_layout.setContentsMargins(0, 0, 0, 0)
            preview_layout.setSpacing(8)
            preview_layout.addWidget(text_label('Preview', 'sectionTitle'))
            self.preview_label = PreviewCanvas('Choose an image, then select Preview to check its layout.')
            preview_layout.addWidget(self.preview_label, 1)
            self.image_note = text_label('', 'muted')
            preview_layout.addWidget(self.image_note)
            layout.addWidget(preview_area, 1)
            self.apply_image_button = self.apply_footer_button
            self.apply_image_button.setEnabled(False)
            self.image_targets.currentIndexChanged.connect(self.image_target_changed)
            self.image_target_changed()
        else:
            from .media import video_targets
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 22, 12, 14)
            layout.setSpacing(14)
            key = 'Mods/' + mod['id'] + '/' + mod['video_list']
            targets = video_targets(self.snapshot.files[key])
            layout.addWidget(text_label('Replace a game video', 'sectionTitle'))
            layout.addWidget(text_label('Choose the original clip, then import your replacement MP4.', 'muted'))
            self.video_choice = QComboBox()
            self.video_choice.setAccessibleName('Video to replace')
            self.video_choice.addItems(targets)
            self.video_choice.setMinimumContentsLength(18)
            self.video_choice.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            layout.addWidget(self.video_choice)
            buttons = QHBoxLayout()
            import_button = QPushButton('Import replacement MP4…')
            import_button.setObjectName('primary')
            import_button.setIcon(icon('folder'))
            import_button.clicked.connect(self.import_video)
            buttons.addWidget(import_button)
            restore = QPushButton('Restore original…')
            restore.setIcon(icon('undo'))
            restore.clicked.connect(lambda: self.restore_media(mod['video_folder'] + '/' + self.video_choice.currentText()))
            buttons.addWidget(restore)
            buttons.addStretch()
            layout.addLayout(buttons)
            layout.addSpacing(10)
            layout.addWidget(text_label('Match the original format', 'sectionTitle'))
            layout.addWidget(text_label('Most Fam videos use H.264 MP4, 2560×1440 at 24 fps, with a green background. Event and logo videos differ; see the mod guide for the selected clip.', 'muted'))
            layout.addStretch()
            layout.addWidget(text_label('Your source file is kept. Restart after restoring an original video.', 'muted'))
        self.media_scroll.setWidget(page)

    def image_target_changed(self, *args):
        target = self.image_targets.currentData()
        self.image_scale.setValue(target.get('scale', 100))
        self.image_top.setValue(target.get('top', 0))
        self.image_x.setValue(0)
        self.image_note.setText(f"Output: {target['width']} × {target['height']} · {target['background']} background. Previous files are backed up.")
        self.invalidate_preview()

    def invalidate_preview(self, *args):
        self._image_bytes = None
        self._image_target = None
        if hasattr(self, 'apply_image_button'):
            self.apply_image_button.setEnabled(False)
        if hasattr(self, 'preview_label'):
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview the image before applying it.')
        self.update_controls()

    def choose_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose replacement image', '',
            'Images (*.png *.webp *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)')
        if filename:
            self.image_source.setText(filename)
            self.invalidate_preview()

    def preview_image(self):
        from .media import compose_image
        if not self.image_source.text():
            self.notice('Choose an image first.', True)
            return
        source = Path(self.image_source.text())
        target = self.image_targets.currentData()
        arguments = (source, target, self.image_scale.value(), self.image_top.value(), self.image_x.value(), self.remove_green.isChecked())
        def ready(data):
            self._image_bytes = data
            self._image_target = target['file']
            pixmap = QPixmap()
            if not pixmap.loadFromData(data, 'PNG'):
                raise ValueError('The preview could not be opened.')
            self.preview_label.setText('')
            self.preview_label.setPixmap(pixmap)
            self.update_controls()
            self.notice('Preview ready. Use this image to save it to the installed mod.')
        self.run_job('Preparing image preview…', lambda progress: compose_image(*arguments), ready)

    def apply_image(self):
        if self._image_bytes and self._image_target:
            mod, target, data, manager = self.current_mod, self._image_target, self._image_bytes, self.manager
            self.run_job('Saving replacement image…', lambda progress: manager.write_user_file(mod, target, data))

    def import_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose replacement video', '', 'MP4 video (*.mp4)')
        if not filename:
            return
        mod, manager = self.current_mod, self.manager
        target = mod['video_folder'] + '/' + self.video_choice.currentText()
        def import_file(progress):
            source = Path(filename)
            if source.stat().st_size > 32 * 1024 * 1024:
                raise ValueError('Choose a replacement video smaller than 32 MB.')
            with source.open('rb') as stream:
                data = stream.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024 or b'ftyp' not in data[:64]:
                raise ValueError('The selected file is not a supported MP4 smaller than 32 MB.')
            manager.write_user_file(mod, target, data)
        self.run_job('Importing replacement video…', import_file)

    def restore_media(self, relative):
        if QMessageBox.question(self, 'Restore original',
            'Remove this custom replacement? A backup is kept. Restart the game afterwards.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            mod, manager = self.current_mod, self.manager
            self.run_job('Restoring original media…', lambda progress: manager.remove_user_file(mod, relative))

    def closeEvent(self, event: QCloseEvent):
        if self._busy:
            self.notice('Please wait for the current operation to finish before closing.')
            event.ignore()
        elif self.allow_discard():
            event.accept()
        else:
            event.ignore()
