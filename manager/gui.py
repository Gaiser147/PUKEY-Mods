"""Native desktop interface. All downloads and mutations run in a worker."""
import json
import os
from decimal import Decimal
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QEvent, QThread, Signal, QTimer, QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QCloseEvent, QFontDatabase, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QListWidget, QListWidgetItem,
    QScrollArea, QFormLayout, QDoubleSpinBox, QComboBox,
    QCheckBox, QTabWidget, QProgressBar, QMessageBox, QFrame, QToolButton,
)

from . import __version__
from .theme import stylesheet, load_fonts
from .fields import ChoiceField, KeyCaptureButton, NumberField
from .setting_help import HelpButton, default_label, key_label, range_label
from .widgets import icon, state_icon, mod_icon, ModDelegate, PreviewCanvas, DialoguePanel, ModNavigation, OrnamentHeading, texture

REPOSITORY = 'https://github.com/Gaiser147/PUKEY-Mods'
PROTON_OPTION = 'WINEDLLOVERRIDES="dwmapi.dll=n,b" %command%'
COMPACT_HEIGHT = 800
# Wide windows keep settings next to their labels and give the extra room to the key sheet.
SETTINGS_MAX_WIDTH = 760
WIDE_WIDTH = 1600
KEY_SHEET_WIDTH = (280, 340)
# Qt ignores the style sheet's left padding on spin boxes; match the 9px inset of other fields.
SPIN_TEXT_INSET = 8
KEYS = ([f'F{i}' for i in range(1, 13)] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') +
        ['HOME', 'END', 'PAGE_UP', 'PAGE_DOWN', 'INSERT', 'DELETE', 'SPACE',
         'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'])


def describe_error(error):
    """Plain message plus the next step that fits this failure, not a generic suffix."""
    from urllib.error import HTTPError, URLError
    if isinstance(error, HTTPError):
        return 'The download server answered with HTTP {}. Try again later.'.format(error.code)
    if isinstance(error, (TimeoutError, ConnectionError, URLError)):
        return 'The download server could not be reached. Check your internet connection and try again.'
    name = getattr(error, 'filename', None)
    if isinstance(error, PermissionError):
        return (name or 'A file') + ' is locked or read-only. Close the game and try again.'
    if isinstance(error, FileNotFoundError):
        return (name or 'A required file') + ' was not found. Check the game folder and try again.'
    if isinstance(error, OSError):
        return (error.strerror or str(error)) + (' (' + name + ')' if name else '') + '. Check the folder and try again.'
    return str(error) or type(error).__name__


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
            self.error.emit(describe_error(error))


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
        load_fonts()
        self.resize(1280, 860)
        self.setMinimumSize(900, 640)
        self.snapshot = snapshot
        self.manager = None
        self.current_mod = None
        self.settings_widgets = {}
        self._other_keys = {}
        self._busy = False
        self._dirty = False
        self._job = None
        self._settings_error = False
        self._state_error = None
        self._image_bytes = None
        self._image_target = None
        self._has_keys = False
        self._loader_ready = False
        self.theme_directory = None
        self._theme_generation = 0
        self.preferences_path = preferences_path or Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / 'preferences.json'
        self.cache_dir = self.preferences_path.parent / 'cache'
        from .sources import SourceStore
        self.source_store = SourceStore(self.preferences_path.parent / 'library')
        self._source_packages = {}
        self._source_selected = {}
        self._import_dialog = None
        self._logs_window = None
        self._build()
        self.setStyleSheet(stylesheet())
        self._theme_presence_timer = QTimer(self)
        self._theme_presence_timer.setInterval(10000)
        self._theme_presence_timer.timeout.connect(self.refresh_game_theme_presence)
        self._theme_presence_timer.start()
        if self.snapshot:
            self.source_label.setText('Local catalogue')
            self.populate()
            # Start on the library rather than painting a focus ring on the first header button.
            self.mod_list.setFocus()
        else:
            self.render_details()
        if start_online:
            QTimer.singleShot(0, self.startup)
        if self.source_store.registry.exists():
            QTimer.singleShot(0, self.load_sources)

    def _build(self):
        body = QWidget()
        body.setObjectName('mainWorkspace')
        self.setCentralWidget(body)
        outer = QVBoxLayout(body)
        outer.setContentsMargins(24, 14, 24, 10)
        outer.setSpacing(10)

        masthead = QHBoxLayout()
        masthead.setSpacing(22)
        logo = QLabel('PUKEY')
        self.logo_label = logo
        logo.setObjectName('brandName')
        logo.setAccessibleName('PUKEY Goddess Shot Trick')
        logo.setFixedSize(188, 108)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        masthead.addWidget(logo)
        masthead.addWidget(text_label('Mod Manager', 'brandName'), 1)
        header_actions = QVBoxLayout()
        header_actions.setSpacing(3)
        top_actions = QHBoxLayout()
        self.folder_button = QPushButton('Game folder…')
        self.folder_button.setObjectName('headerAction')
        self.folder_button.setCheckable(True)
        self.folder_button.setChecked(True)
        self.folder_button.toggled.connect(self.toggle_game_panel)
        top_actions.addWidget(self.folder_button)
        self.add_mod_button = QPushButton('Add mod…')
        self.add_mod_button.setObjectName('headerAction')
        self.add_mod_button.clicked.connect(self.add_mods)
        top_actions.addWidget(self.add_mod_button)
        self.refresh_button = QPushButton('Refresh catalogue')
        self.refresh_button.setObjectName('headerAction')
        self.refresh_button.setShortcut('Ctrl+R')
        self.refresh_button.clicked.connect(self.refresh_catalogue)
        top_actions.addWidget(self.refresh_button)
        header_actions.addLayout(top_actions)
        bottom_actions = QHBoxLayout()
        bottom_actions.addStretch()
        self.source_label = text_label('Catalogue not loaded', 'sidebarMuted')
        bottom_actions.addWidget(self.source_label)
        self.cached_button = QPushButton('Use offline copy')
        self.cached_button.setObjectName('sideLink')
        self.cached_button.setToolTip('Open the last downloaded catalogue without a connection')
        self.cached_button.clicked.connect(self.use_cached)
        bottom_actions.addWidget(self.cached_button)
        self.masthead_links = bottom_actions
        header_actions.addLayout(bottom_actions)
        masthead.addLayout(header_actions)
        outer.addLayout(masthead)

        self.game_panel = QFrame()
        self.game_panel.setObjectName('gamePanel')
        game_layout = QVBoxLayout(self.game_panel)
        game_layout.setContentsMargins(12, 7, 12, 8)
        game_layout.setSpacing(5)
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
        if sys.platform.startswith('linux'):
            copy = QPushButton('Copy Proton launch option')
            copy.setToolTip("Copy the DLL override required in the game's Steam launch options")
            copy.clicked.connect(lambda: QApplication.clipboard().setText(PROTON_OPTION))
            heading.addWidget(copy)
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
        outer.addWidget(self.game_panel)

        self.mod_list = ModNavigation()
        self.mod_list.setObjectName('modNavigation')
        self.mod_list.setAccessibleName('Available mods')
        self.mod_list.setItemDelegate(ModDelegate(self.mod_list))
        self.mod_list.setMouseTracking(True)
        self.mod_list.currentRowChanged.connect(self.select_mod)
        outer.addWidget(self.mod_list)
        self.nav_empty = text_label('Refresh the catalogue to discover your mods.', 'muted')
        outer.addWidget(self.nav_empty)
        self.mod_count = QLabel()

        self.sheets = QHBoxLayout()
        self.sheets.setSpacing(18)
        self.main_panel = DialoguePanel('dialogue')
        content = QVBoxLayout(self.main_panel)
        content.setContentsMargins(22, 18, 22, 17)
        content.setSpacing(9)
        self.mod_header = QWidget()
        header = QHBoxLayout(self.mod_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        self.mod_icon_label = QLabel()
        self.mod_icon_label.hide()
        self.mod_title = text_label('Your mods', 'modTitle')
        title_block.addWidget(self.mod_title)
        self.mod_status_label = text_label('Select a mod to get started', 'modStatus')
        title_block.addWidget(self.mod_status_label)
        header.addLayout(title_block, 1)
        action_column = QVBoxLayout()
        action_column.setSpacing(3)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.install_button = QPushButton('Install mod')
        self.install_button.setIcon(icon('download'))
        self.install_button.clicked.connect(self.install_current)
        actions.addWidget(self.install_button)
        self.enabled_checkbox = QPushButton('Disabled')
        self.enabled_checkbox.setObjectName('activation')
        self.enabled_checkbox.setCheckable(True)
        self.enabled_checkbox.toggled.connect(self.toggle_current)
        actions.addWidget(self.enabled_checkbox)
        action_column.addLayout(actions)
        utility = QHBoxLayout()
        utility.addStretch()
        self.guide_button = QPushButton()
        self.guide_button.setObjectName('iconAction')
        self.guide_button.setIcon(icon('book'))
        self.guide_button.setToolTip('Open mod guide')
        self.guide_button.setAccessibleName('Open mod guide')
        self.guide_button.clicked.connect(self.open_guide)
        utility.addWidget(self.guide_button)
        self.config_button = QPushButton()
        self.config_button.setObjectName('iconAction')
        self.config_button.setIcon(icon('folder'))
        self.config_button.setAccessibleName('Open configuration files')
        self.config_button.setToolTip('Open the mod folder to edit configuration files')
        self.config_button.clicked.connect(self.open_configuration)
        utility.addWidget(self.config_button)
        self.remove_button = QPushButton()
        self.remove_button.setObjectName('iconAction')
        self.remove_button.setIcon(icon('trash'))
        self.remove_button.setAccessibleName('Remove mod')
        self.remove_button.clicked.connect(self.remove_current)
        utility.addWidget(self.remove_button)
        action_column.addLayout(utility)
        self.initial_enable = QCheckBox('Enable after installation')
        self.initial_enable.setChecked(True)
        action_column.addWidget(self.initial_enable)
        self.zip_update_button = QPushButton('Update from ZIP…')
        self.zip_update_button.clicked.connect(self.update_from_zip)
        action_column.addWidget(self.zip_update_button)
        header.addLayout(action_column)
        content.addWidget(self.mod_header)
        self.description = text_label('', 'muted')
        content.addWidget(self.description)
        self.origin_label = text_label('', 'muted')
        content.addWidget(self.origin_label)
        self.controls_label = None
        self.tabs = QTabWidget()
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.keys_scroll = QScrollArea()
        self.keys_scroll.setWidgetResizable(True)
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.tabs.addTab(self.settings_scroll, 'Settings')
        self.tabs.currentChanged.connect(lambda index: self.update_controls())
        content.addWidget(self.tabs, 1)
        self.sheets.addWidget(self.main_panel, 1)

        self.keys_panel = DialoguePanel()
        self.keys_panel.setFixedWidth(KEY_SHEET_WIDTH[0])
        key_layout = QVBoxLayout(self.keys_panel)
        key_layout.setContentsMargins(18, 16, 18, 16)
        key_layout.setSpacing(8)
        key_heading = OrnamentHeading('Keybindings')
        key_heading.setTextFormat(Qt.TextFormat.PlainText)
        key_heading.setObjectName('keyHeading')
        key_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        key_layout.addWidget(key_heading)
        key_layout.addWidget(self.keys_scroll, 1)
        self.sheets_container = QWidget()
        self.sheets_container.setLayout(self.sheets)
        outer.addWidget(self.sheets_container, 1)
        self.sheets.addWidget(self.keys_panel)

        self.empty_state = DialoguePanel('dialogue')
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(28, 24, 28, 24)
        empty_layout.setSpacing(12)
        empty_layout.addStretch()
        self.empty_heading = text_label('Set up your mod library', 'emptyTitle')
        self.empty_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_heading)
        hint = text_label('Find your Steam game folder above. Refresh the catalogue to load the available mods.', 'muted')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(hint)
        empty_layout.addStretch()
        outer.addWidget(self.empty_state, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.hide()
        outer.addWidget(self.progress_bar)
        # One bar carries operation status and the persistent actions; a second status line cost a row.
        status = QHBoxLayout()
        status.setContentsMargins(8, 0, 6, 0)
        status.setSpacing(16)
        self.status_icon = QLabel()
        self.status_icon.setPixmap(icon('alert', '#ff8ba5').pixmap(16, 16))
        self.status_icon.setFixedSize(16, 16)
        self.status_icon.setAccessibleName('Error')
        self.status_icon.hide()
        message = QHBoxLayout()
        message.setSpacing(8)
        message.addWidget(self.status_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self._error_shown = False
        self.status_label = text_label('Ready. Personal files are kept during updates.', 'operationStatus')
        self.status_label.setMinimumHeight(24)
        message.addWidget(self.status_label, 1)
        status.addLayout(message, 1)
        self.detail_footer = QFrame()
        self.detail_footer.setObjectName('detailFooter')
        self.save_row = QHBoxLayout(self.detail_footer)
        self.save_row.setContentsMargins(0, 1, 0, 1)
        self.save_row.setSpacing(10)
        self.unsaved_label = text_label('Unsaved changes')
        self.unsaved_label.setWordWrap(False)
        self.unsaved_label.hide()
        self.save_row.addWidget(self.unsaved_label)
        self.preview_button = QPushButton('Preview')
        self.preview_button.setIcon(icon('eye'))
        self.preview_button.clicked.connect(self.preview_image)
        self.save_row.addWidget(self.preview_button)
        self.restore_image_button = QPushButton('Restore')
        self.restore_image_button.setIcon(icon('undo'))
        self.restore_image_button.setToolTip('Restore the original image after backing up your replacement')
        self.restore_image_button.clicked.connect(lambda: self.restore_media(self.image_targets.currentData()['file']))
        self.save_row.addWidget(self.restore_image_button)
        self.import_video_button = QPushButton('Import replacement MP4…')
        self.import_video_button.setObjectName('primary')
        self.import_video_button.setIcon(icon('folder'))
        self.import_video_button.clicked.connect(self.import_video)
        self.save_row.addWidget(self.import_video_button)
        self.restore_video_button = QPushButton('Restore original…')
        self.restore_video_button.setIcon(icon('undo'))
        self.restore_video_button.clicked.connect(lambda: self.restore_media(
            self.current_mod['video_folder'] + '/' + self.video_choice.currentData()))
        self.save_row.addWidget(self.restore_video_button)
        self.save_button = QPushButton('Save settings')
        self.save_button.setObjectName('primary')
        self.save_button.setShortcut('Ctrl+S')
        self.save_button.clicked.connect(self.save_settings)
        self.save_row.addWidget(self.save_button)
        self.apply_footer_button = QPushButton('Use preview image')
        self.apply_footer_button.setObjectName('primary')
        self.apply_footer_button.clicked.connect(self.apply_image)
        self.save_row.addWidget(self.apply_footer_button)
        status.addWidget(self.detail_footer)
        outer.addLayout(status)
        self.logs_button = QPushButton('Logs…')
        self.logs_button.setObjectName('sideLink')
        self.logs_button.clicked.connect(self.open_logs)
        self.masthead_links.addWidget(self.logs_button)
        repo = QPushButton('v' + __version__ + '  ·  GitHub')
        repo.setObjectName('sideLink')
        repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPOSITORY)))
        self.masthead_links.addWidget(repo)
        self.update_controls()

    def snapshot_for(self, mod):
        source = mod.get('_source_id', 'official')
        return self.snapshot if source == 'official' else self._source_packages[source]

    def manager_for(self, mod):
        from .service import Manager
        if not isinstance(self.manager, Manager): return self.manager
        return Manager(self.manager.game_root, self.snapshot_for(mod))

    def library_mods(self):
        result = [dict(mod, _source_id='official') for mod in self.snapshot.mods] if self.snapshot else []
        for source_id, snapshot in self._source_packages.items():
            if source_id == 'official': continue
            chosen = self._source_selected.get(source_id, [])
            result.extend(dict(mod, _source_id=source_id) for mod in snapshot.mods if mod['id'] in chosen)
        return result

    def source_added(self, source_id, snapshot, selected_ids):
        self._source_packages[source_id] = snapshot
        self._source_selected[source_id] = selected_ids
        self.populate()
        self.notice('Mods added. Select a tab and choose Install mod.')

    def load_sources(self):
        if self._busy or self._dirty:
            QTimer.singleShot(250, self.load_sources)
            return
        def load(progress):
            packages, selected, errors = {}, {}, []
            for record in self.source_store.records:
                try:
                    packages[record['id']] = self.source_store.load(record['id'])
                    selected[record['id']] = record['selected_ids']
                except Exception as error: errors.append(str(error))
            return packages, selected, errors
        def accepted(result):
            self._source_packages, self._source_selected, errors = result
            if self.snapshot is None:
                self.snapshot = self._source_packages.get('official')
                self.source_label.setText('Saved library')
            self.populate()
            self.notice('Saved library loaded.' if not errors else 'Some saved sources could not be loaded: ' + '; '.join(errors),
                        bool(errors), background=True)
        self.run_job('Loading saved mod sources…', load, accepted, True)

    def add_mods(self):
        if not self.allow_discard(): return
        from .import_dialog import ImportDialog
        if self._import_dialog is None:
            self._import_dialog = ImportDialog(self.source_store, self.source_added, self)
        self._import_dialog.update_source_id = None
        self._import_dialog.show()
        self._import_dialog.raise_()
        self._import_dialog.activateWindow()

    def update_from_zip(self):
        if not self.current_mod or not self.allow_discard(): return
        source_id = self.current_mod.get('_source_id', 'official')
        if source_id == 'official': return
        snapshot = self._source_packages[source_id]
        if getattr(snapshot, 'origin', {}).get('kind') != 'local':
            from .import_dialog import ImportDialog
            if self._import_dialog and self._import_dialog.busy: return
            self._import_dialog = ImportDialog(self.source_store, self.source_added, self)
            self._import_dialog.update_source_id = source_id
            record = next(record for record in self.source_store.records if record['id'] == source_id)
            self._import_dialog.origin.setText(record['origin'])
            self._import_dialog.show()
            self._import_dialog.analyze()
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Update this source from ZIP', '', 'Mod archives (*.zip)')
        if not path: return
        selected = self._source_selected[source_id]
        self.run_job('Validating replacement ZIP…',
            lambda progress: self.source_store.update_from_package(source_id, Path(path), progress),
            lambda snapshot: self.source_added(source_id, snapshot, selected))

    def open_logs(self):
        from .log_window import LogsWindow
        root = self.manager.game_root if self.manager and hasattr(self.manager, 'game_root') else None
        if self._logs_window is None or getattr(self._logs_window, '_game_root', None) != root:
            if self._logs_window: self._logs_window.close()
            self._logs_window = LogsWindow(root, self)
            self._logs_window._game_root = root
        self._logs_window.show()
        self._logs_window.raise_()
        self._logs_window.activateWindow()

    def open_configuration(self):
        if self.manager and self.current_mod:
            folder = self.manager.win64 / 'ue4ss/Mods' / self.current_mod['id']
            if folder.is_dir(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def toggle_game_panel(self, expanded):
        self.game_panel.setVisible(expanded)
        self.folder_button.setToolTip(self.path_edit.text() or 'Choose your game installation')

    def apply_game_theme(self, directory, win64=None):
        from .game_assets import game_present
        if directory is not None:
            if not self.manager or (win64 is not None and Path(win64) != self.manager.win64):
                return False
            if not game_present(self.manager.win64):
                self.apply_game_theme(None)
                return False
            directory = Path(directory)
        self.theme_directory = directory
        self.setProperty('gameThemePath', str(directory) if directory else '')
        texture.cache_clear()
        self.setStyleSheet(stylesheet(directory))
        self.update_logo()
        self.update()
        return directory is not None

    def update_logo(self):
        # Short windows give the logo's height to the settings; the ribbon still carries the game identity.
        compact = self.height() < COMPACT_HEIGHT
        width, height = (112, 64) if compact else (188, 108)
        self.logo_label.setFixedSize(width, height)
        logo = texture('logo', self.theme_directory)
        if logo.isNull():
            self.logo_label.setPixmap(QPixmap())
            self.logo_label.setText('PUKEY')
        else:
            # Scale to device pixels so the logo stays sharp at 150 % and 200 % display scaling.
            ratio = self.devicePixelRatioF()
            scaled = logo.scaled(round(width * ratio), round(height * ratio), Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            scaled.setDevicePixelRatio(ratio)
            self.logo_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if (self.height() < COMPACT_HEIGHT) != (self.logo_label.height() < 108):
            self.update_logo()
        self.keys_panel.setFixedWidth(KEY_SHEET_WIDTH[self.width() >= WIDE_WIDTH])

    def event(self, event):
        if event.type() == QEvent.Type.DevicePixelRatioChange:
            self.update_logo()
        return super().event(event)

    def refresh_game_theme_presence(self):
        from .game_assets import game_present
        if self.theme_directory and (not self.manager or not game_present(self.manager.win64)):
            self._theme_generation += 1
            self.apply_game_theme(None)

    def load_game_theme(self, win64, generation):
        from .game_assets import extract_theme, game_present
        if generation != self._theme_generation or not self.manager or self.manager.win64 != win64:
            return
        if self._busy:
            QTimer.singleShot(100, lambda: self.load_game_theme(win64, generation))
            return
        if not game_present(win64):
            return
        def accepted(directory):
            if generation == self._theme_generation and self.apply_game_theme(directory, win64):
                self.notice('Game interface artwork loaded from your installation.', background=True)
        self.run_job('Reading interface artwork from the installed game…',
            lambda progress: extract_theme(win64, self.preferences_path.parent / 'game-ui', progress), accepted, True)

    def notice(self, message, error=False, background=False):
        """Background work (detection, artwork) never replaces an error the user has not acted on yet."""
        if background and self._error_shown and not error:
            return
        self._error_shown = error
        self.status_label.setText(message)
        self.status_label.setToolTip(message)
        self.status_label.setStyleSheet('color: #ff8ba5;' if error else '')
        self.status_icon.setVisible(error)

    def run_job(self, label, operation, callback=None, background=False):
        if self._busy:
            return
        self._busy = True
        self.notice(label, background=background)
        self.progress_bar.show()
        self.update_controls()
        worker = Job(operation, self)
        self._job = worker
        worker.progress.connect(lambda message: self.notice(message, background=background))
        worker.error.connect(lambda message: self.notice(message, True))
        def success(value):
            try:
                if callback:
                    callback(value)
                else:
                    if self._dirty:
                        self.refresh_status_rows()
                    else:
                        self.populate()
                    self.notice('Done. Restart the game to apply changes.', background=background)
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
        def refresh(progress):
            errors, packages, selected = [], {}, {}
            official = None
            try:
                official = fetch_latest(self.cache_dir, progress)
                records = self.source_store.records
                if any(r['id'] == 'official' for r in records):
                    official = self.source_store.update('official', official)
                else:
                    self.source_store.add(official, REPOSITORY, [m['id'] for m in official.mods], 'official')
            except Exception as error: errors.append('Official catalogue: ' + describe_error(error))
            for record in self.source_store.records:
                if record['id'] == 'official': continue
                selected[record['id']] = record['selected_ids']
                try:
                    packages[record['id']] = (self.source_store.load(record['id']) if record['kind'] == 'local'
                                              else self.source_store.refresh(record['id'], progress))
                except Exception as error:
                    errors.append(record['origin'] + ': ' + describe_error(error))
                    try: packages[record['id']] = self.source_store.load(record['id'])
                    except Exception: pass
            return official, packages, selected, errors
        def accepted(result):
            official, packages, selected, errors = result
            self._source_packages.update(packages)
            self._source_selected.update(selected)
            if official: self.accept_snapshot(official)
            else: self.populate()
            if errors: self.notice('Some sources could not refresh; saved copies were kept. ' + '; '.join(errors), True)
        self.run_job('Checking mod sources…', refresh, accepted)

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
            QTimer.singleShot(100, lambda: self.detect_games(background=True))

    def detect_games(self, checked=False, background=False):
        from .platforms import find_games
        if self._busy:
            QTimer.singleShot(100, lambda: self.detect_games(background=background))
            return
        def detected(games):
            if len(games) == 1:
                self.set_game(games[0])
                self.notice('Found your Steam installation. Select a mod to continue.', background=background)
            elif games:
                self.notice('Multiple installations found. Use Browse to choose one: ' + '; '.join(map(str, games)), background=background)
            else:
                self.notice('No Steam installation found. Use Browse to select the game folder.', background=background)
        self.run_job('Looking for the game in Steam libraries…', lambda progress: find_games(), detected, background)

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
        self._theme_generation += 1
        self.apply_game_theme(None)
        self.path_edit.setText(str(path))
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.preferences_path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'game': str(path)}), encoding='utf-8')
        temporary.replace(self.preferences_path)
        self.populate()
        win64, generation = manager.win64, self._theme_generation
        QTimer.singleShot(0, lambda: self.load_game_theme(win64, generation))

    def mod_status(self, mod):
        if self.manager:
            try:
                return self.manager_for(mod).status(mod)
            except Exception as error:
                self._state_error = str(error)
                self.notice('Installation configuration could not be read: ' + str(error), True)
        return {'installed': False, 'enabled': False, 'update': False, 'version': '', 'managed': False}

    def populate(self):
        self._state_error = None
        selected = ((self.current_mod.get('_source_id', 'official'), self.current_mod['id']) if self.current_mod else None)
        self.mod_list.blockSignals(True)
        self.mod_list.clear()
        chosen = 0
        for index, mod in enumerate(self.library_mods()):
            state = self.mod_status(mod)
            status = ('Enabled' if state['installed'] and state['enabled'] else
                      'Disabled' if state['installed'] else 'Not installed')
            if state.get('conflict'): status = 'Source conflict'
            if state['update']: status += ' · Update available'
            item = QListWidgetItem(mod['name'] + '\n' + status)
            item.setData(Qt.ItemDataRole.UserRole, mod)
            item.setToolTip(mod['name'] + '\n' + status + '\nSource: ' + mod.get('_source_id', 'official'))
            self.mod_list.addItem(item)
            if (mod.get('_source_id', 'official'), mod['id']) == selected:
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
            status = ('Enabled' if state['installed'] and state['enabled'] else
                      'Disabled' if state['installed'] else 'Not installed')
            if state.get('conflict'): status = 'Source conflict'
            if state['update']: status += ' · Update available'
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
                candidate = self.mod_list.item(index).data(Qt.ItemDataRole.UserRole)
                if (candidate.get('_source_id', 'official'), candidate['id']) == (previous.get('_source_id', 'official'), previous['id']):
                    self.mod_list.setCurrentRow(index)
            self.mod_list.blockSignals(False)
            return
        item = self.mod_list.item(row)
        self.current_mod = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.render_details()

    def render_details(self):
        self.settings_widgets = {}
        self._other_keys = {}
        self.reset_buttons = {}
        self.help_buttons = {}
        self.key_warnings = {}
        self.capture_buttons = {}
        self.field_notes = {}
        self._settings_error = False
        self._dirty = False
        self._image_bytes = None
        self._image_target = None
        mod = self.current_mod
        self.mod_title.setText(mod['name'] if mod else 'Your mod library')
        self.mod_icon_label.setPixmap(mod_icon(mod or {}).pixmap(30, 30))
        self.description.setText(mod['description'] if mod else 'Refresh the catalogue to discover mods, then choose your game folder to begin.')
        source = mod.get('_source_id', 'official') if mod else 'official'
        details = getattr(self.snapshot_for(mod), 'origin', {}) if mod else {}
        self.origin_label.setText(('Source: ' + str(details.get('origin', source)) +
                                  (' · by ' + mod['author'] if mod.get('author') else '') +
                                  (' · No longer offered by the source' if mod.get('available') is False else '')) if source != 'official' else '')
        self.origin_label.setVisible(source != 'official')
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
                defaults = self.manager_for(mod).settings(mod)
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
                widget = NumberField()
                numbers = [field['min'], field['max'], field['default'], field.get('step', 1), value]
                digits = max(max(0, -Decimal(str(number)).normalize().as_tuple().exponent) for number in numbers)
                widget.setDecimals(min(16, digits))
                widget.setRange(field['min'], field['max'])
                widget.setSingleStep(field.get('step', 1))
                widget.setValue(value)
                widget.lineEdit().setTextMargins(SPIN_TEXT_INSET, 0, 0, 0)
                widget.valueChanged.connect(self.mark_dirty)
            elif field['type'] == 'string':
                widget = QLineEdit(str(value))
                widget.setMaxLength(4096)
                widget.textChanged.connect(self.mark_dirty)
            elif field['type'] == 'key':
                widget = ChoiceField()
                for code in KEYS:
                    widget.addItem(key_label(code), code)
                if widget.findData(str(value)) < 0:
                    widget.addItem(str(value), str(value))
                widget.setCurrentIndex(widget.findData(str(value)))
                widget.currentIndexChanged.connect(self.mark_dirty)
                widget.currentIndexChanged.connect(self.update_key_conflicts)
            else:
                widget = ChoiceField()
                widget.addItems(field['options'])
                widget.setCurrentText(str(value))
                widget.currentTextChanged.connect(self.mark_dirty)
            widget.setAccessibleName(field['label'])
            widget.setToolTip(('Range ' + range_label(field) + ' · ' if field['type'] == 'number' else '') +
                              'Default ' + default_label(field))
            widget.setFixedWidth(116 if field['type'] == 'key' else 180)
            row = QWidget()
            row.setObjectName('keyRow' if field['type'] == 'key' else 'fieldRow')
            row.setMinimumHeight(56)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 8, 0, 8)
            row_layout.setSpacing(12)
            label = text_label(field['label'])
            label.setBuddy(widget)
            help_button = HelpButton(field)
            self.help_buttons[field['key']] = help_button
            reset = QToolButton()
            reset.setIcon(state_icon('undo'))
            reset.setAutoRaise(True)
            reset.setFixedSize(26, 28)
            reset.setAccessibleName('Reset ' + field['label'])
            reset.setToolTip('Reset to default: ' + default_label(field) + '. Save settings to apply.')
            reset.clicked.connect(lambda checked=False, key=field['key'], default=field['default']: self.reset_setting(key, default))
            self.reset_buttons[field['key']] = reset
            if field['type'] == 'key':
                row.setMinimumHeight(84)
                stack = QVBoxLayout()
                top = QHBoxLayout()
                top.addWidget(label, 1)
                top.addWidget(help_button)
                bottom = QHBoxLayout()
                bottom.addWidget(widget, 1)
                capture = KeyCaptureButton(field['label'])
                capture.toggled.connect(lambda listening, name=field['label']: listening and self.notice(
                    'Press a key for ' + name + '. Esc cancels.'))
                capture.captured.connect(lambda code, target=widget: target.setCurrentIndex(target.findData(code)))
                capture.rejected.connect(lambda key: self.notice(
                    key + ' cannot be assigned here. Choose a key from the list.'))
                self.capture_buttons[field['key']] = capture
                bottom.addWidget(capture)
                bottom.addStretch()
                bottom.addWidget(reset)
                stack.addLayout(top)
                stack.addLayout(bottom)
                warning = text_label('', 'keyConflict')
                warning.hide()
                stack.addWidget(warning)
                self.key_warnings[field['key']] = warning
                row_layout.addLayout(stack)
                bindings.addWidget(row)
                key_count += 1
            else:
                caption = QVBoxLayout()
                caption.setSpacing(2)
                caption.addWidget(label)
                if field['type'] == 'number':
                    # Corrections are explained where they happen instead of silently replacing input.
                    note = text_label('', 'fieldNote')
                    note.hide()
                    caption.addWidget(note)
                    widget.adjusted.connect(lambda message, target=note: (target.setText(message),
                                                                          target.setVisible(bool(message))))
                    self.field_notes[field['key']] = note
                row_layout.addLayout(caption, 1)
                row_layout.addWidget(help_button)
                row_layout.addWidget(widget)
                row_layout.addWidget(reset)
                preferences.addWidget(row)
                general_count += 1
            self.settings_widgets[field['key']] = widget
        self._other_keys = self.keys_in_use(mod)
        self.update_key_conflicts()
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
        self.settings_page.setMaximumWidth(SETTINGS_MAX_WIDTH)
        self.settings_scroll.setWidget(self.settings_page)
        self.keys_scroll.setWidget(self.keys_page)
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        self._has_keys = bool(mod and (key_count or mod.get('controls')))
        if mod and (mod.get('images') or mod.get('video_list')):
            self.build_media(mod)
            self.tabs.addTab(self.media_scroll, 'Images' if mod.get('images') else 'Videos')
        self.unsaved_label.hide()
        self.mod_count.setText(str(self.mod_list.count()))
        self.nav_empty.setVisible(self.mod_list.count() == 0)
        self.update_controls()

    def keys_in_use(self, current):
        """Keys bound by the other installed, enabled mods; in game every binding of a key fires."""
        used = {}
        if not (current and self.manager):
            return used
        for mod in self.library_mods():
            fields = [field for field in mod.get('settings', []) if field['type'] == 'key']
            if mod['id'] == current['id'] or not fields:
                continue
            try:
                manager = self.manager_for(mod)
                state = manager.status(mod)
                if not (state['installed'] and state['enabled']):
                    continue
                values = manager.settings(mod)
            except Exception:
                continue
            for field in fields:
                used.setdefault(str(values.get(field['key'], field['default'])), []).append(
                    mod['name'] + ': ' + field['label'])
        return used

    def update_key_conflicts(self, *args):
        labels = {field['key']: field['label'] for field in (self.current_mod or {}).get('settings', [])}
        values = {key: self.field_value(self.settings_widgets[key]) for key in self.key_warnings}
        for key, warning in self.key_warnings.items():
            others = [labels[other] for other, value in values.items() if other != key and value == values[key]]
            others += self._other_keys.get(values[key], [])
            text = 'Also used by ' + '; '.join(others) + '.' if others else ''
            warning.setText(text)
            warning.setVisible(bool(others))
            widget = self.settings_widgets[key]
            widget.setAccessibleDescription(text)
            if widget.property('conflict') != bool(others):
                widget.setProperty('conflict', bool(others))
                widget.style().unpolish(widget)
                widget.style().polish(widget)

    def mark_dirty(self, *args):
        self._dirty = True
        self.unsaved_label.show()
        self.update_controls()

    @staticmethod
    def field_value(widget):
        return (widget.isChecked() if isinstance(widget, QCheckBox) else
                widget.value() if isinstance(widget, QDoubleSpinBox) else
                widget.text() if isinstance(widget, QLineEdit) else
                widget.currentData() if widget.currentData() is not None else widget.currentText())

    def reset_setting(self, key, default):
        widget = self.settings_widgets[key]
        if isinstance(widget, QCheckBox): widget.setChecked(default)
        elif isinstance(widget, QDoubleSpinBox): widget.setValue(default)
        elif isinstance(widget, QLineEdit): widget.setText(default)
        elif widget.findData(default) >= 0: widget.setCurrentIndex(widget.findData(default))
        else: widget.setCurrentText(default)

    def update_controls(self):
        fields = {field['key']: field for field in (self.current_mod or {}).get('settings', [])}
        for key, button in getattr(self, 'reset_buttons', {}).items():
            button.setEnabled(self.field_value(self.settings_widgets[key]) != fields[key]['default'])
        ready = not self._busy
        has_mod = self.current_mod is not None
        self.sheets_container.setVisible(has_mod)
        self.mod_list.setVisible(self.mod_list.count() > 0)
        self.nav_empty.hide()
        self.main_panel.setVisible(has_mod)
        self.mod_header.setVisible(has_mod)
        self.description.setVisible(has_mod)
        self.tabs.setVisible(has_mod)
        self.detail_footer.setVisible(has_mod)
        self.empty_state.setVisible(not has_mod)
        self.empty_heading.setText('Preparing your library…' if self._busy else 'Set up your mod library')
        for widget in [self.refresh_button, self.cached_button, self.browse_button, self.detect_button, self.path_edit, self.mod_list, self.add_mod_button]:
            widget.setEnabled(ready)
        state = self.mod_status(self.current_mod) if self.current_mod else {'installed': False, 'enabled': False}
        installed = state['installed']
        loader = bool(self.manager and (self.manager.win64 / 'dwmapi.dll').is_file() and
                      (self.manager.win64 / 'ue4ss/UE4SS.dll').is_file())
        self.loader_label.setText('UE4SS ready' if loader else 'UE4SS required' if self.manager else 'Choose a game folder')
        self.loader_label.setStyleSheet('color: #02e5a2;' if loader else '')
        self.loader_icon.setPixmap(icon('check' if loader else 'folder', '#02e5a2' if loader else '#b5adb5').pixmap(16, 16))
        if loader and not self._loader_ready:
            self.folder_button.setChecked(False)
        self._loader_ready = loader
        self.loader_button.setText('UE4SS ready' if loader else 'Install UE4SS')
        writable = ready and not self._state_error and not state.get('conflict')
        self.loader_button.setEnabled(writable and self.manager is not None and not loader)
        self.loader_button.setVisible(self.manager is not None and not loader)
        for button, prominent in ((self.detect_button, self.manager is None),
                                  (self.install_button, bool(state.get('update') or not installed))):
            if button.property('prominent') != prominent:
                button.setProperty('prominent', prominent)
                button.style().unpolish(button)
                button.style().polish(button)
        self.install_button.setText('Update mod' if state.get('update') else 'Reinstall mod' if installed else 'Install mod')
        self.install_button.setEnabled(writable and loader and self.current_mod is not None and self.current_mod.get('available') is not False)
        external = bool(self.current_mod and self.current_mod.get('_source_id', 'official') != 'official')
        self.initial_enable.setVisible(external and not installed)
        self.initial_enable.setEnabled(writable and not installed)
        self.zip_update_button.setVisible(external)
        self.zip_update_button.setEnabled(ready)
        if external:
            source = self.current_mod['_source_id']
            local = getattr(self._source_packages.get(source), 'origin', {}).get('kind') == 'local'
            self.zip_update_button.setText('Update from ZIP…' if local else 'Source options…')
        self.enabled_checkbox.blockSignals(True)
        self.enabled_checkbox.setChecked(state['enabled'])
        self.enabled_checkbox.setText('Enabled' if state['enabled'] else 'Disabled')
        self.enabled_checkbox.setIcon(icon('power', '#02e5a2' if state['enabled'] else '#b5adb5'))
        self.enabled_checkbox.blockSignals(False)
        self.enabled_checkbox.setEnabled(writable and installed)
        self.remove_button.setEnabled(writable and installed and state.get('managed', False))
        self.remove_button.setToolTip('Removes tracked program files; personal files remain.' if state.get('managed') else
                                      'Reinstall once to track this manually installed mod before removing its program files.')
        self.guide_button.setEnabled(ready and self.current_mod is not None)
        self.config_button.setEnabled(ready and installed and not state.get('conflict'))
        self.save_button.setEnabled(ready and installed and bool(self.settings_widgets) and not self._settings_error and self._dirty)
        media_tab = has_mod and self.tabs.currentWidget() == self.media_scroll
        image_tab = bool(media_tab and self.current_mod.get('images'))
        self.keys_panel.setVisible(has_mod and self._has_keys and not media_tab)
        self.preview_button.setVisible(image_tab)
        self.restore_image_button.setVisible(image_tab)
        self.preview_button.setEnabled(ready and installed)
        self.restore_image_button.setEnabled(ready and installed)
        video_tab = bool(media_tab and self.current_mod.get('video_list'))
        self.import_video_button.setVisible(video_tab)
        self.restore_video_button.setVisible(video_tab)
        self.import_video_button.setEnabled(ready and installed)
        self.restore_video_button.setEnabled(ready and installed)
        self.save_button.setVisible(not media_tab or self._dirty)
        self.apply_footer_button.setVisible(image_tab)
        self.apply_footer_button.setEnabled(ready and installed and self._image_bytes is not None)
        if hasattr(self, 'settings_page'):
            self.settings_page.setEnabled(ready and installed and not self._settings_error)
        if hasattr(self, 'keys_page'):
            self.keys_page.setEnabled(ready and installed and not self._settings_error)
        self.media_scroll.setEnabled(ready and installed)
        if not self.current_mod:
            status = 'Choose a mod from your library'
        elif state.get('conflict'):
            status = state['conflict']
        elif not installed:
            status = ('Choose a game folder to install this mod.' if not self.manager else
                      'Install UE4SS in Game folder… before installing this mod.' if not loader else 'Not installed')
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
            mod = self.current_mod
            manager = self.manager_for(mod)
            enabled = self.initial_enable.isChecked() if mod.get('_source_id', 'official') != 'official' else None
            self.run_job('Installing ' + mod['name'] + '…', lambda progress: manager.install(mod, progress, enabled=enabled))

    def toggle_current(self, enabled):
        if self.current_mod and self.manager and not self._busy:
            mod = self.current_mod
            manager = self.manager_for(mod)
            self.run_job('Updating mod activation…', lambda progress: manager.set_enabled(mod, enabled))

    def remove_current(self):
        if not self.current_mod or not self.allow_discard():
            return
        answer = QMessageBox.question(self, 'Remove ' + self.current_mod['name'],
            'Remove this mod’s program files? Your images, videos, settings and camera bookmarks will be kept.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            mod = self.current_mod
            manager = self.manager_for(mod)
            self.run_job('Removing mod program files…', lambda progress: manager.remove(mod))

    def save_settings(self):
        if not self.current_mod or not self.save_button.isEnabled():
            return
        values = {}
        for key, widget in self.settings_widgets.items():
            values[key] = self.field_value(widget)
        mod = self.current_mod
        manager = self.manager_for(mod)
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
            mod = self.current_mod
            if mod.get('_source_id', 'official') == 'official':
                QDesktopServices.openUrl(QUrl(REPOSITORY + '/tree/main/Mods/' + mod['id']))
                return
            homepage = mod.get('homepage', '')
            if homepage.startswith('https://'):
                QDesktopServices.openUrl(QUrl(homepage))
                return
            snapshot = self.snapshot_for(mod)
            readmes = [p for p in mod['files'] if Path(p).name.lower().startswith('readme')]
            if readmes:
                from PySide6.QtWidgets import QDialog, QPlainTextEdit
                dialog = QDialog(self)
                dialog.setWindowTitle(mod['name'] + ' · Guide')
                dialog.resize(700, 500)
                layout = QVBoxLayout(dialog)
                view = QPlainTextEdit()
                view.setReadOnly(True)
                view.setPlainText(snapshot.files['Mods/' + mod['id'] + '/' + readmes[0]].decode('utf-8', errors='replace'))
                layout.addWidget(view)
                dialog.show()
            else:
                self.notice('This mod includes no guide. Use Source options or open its configuration folder.')

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
            self.image_targets = ChoiceField()
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
            self.image_scale = NumberField()
            self.image_scale.setRange(1, 500)
            self.image_scale.setSuffix(' %')
            self.image_top = NumberField()
            self.image_top.setRange(-100, 100)
            self.image_top.setSuffix(' %')
            self.image_x = NumberField()
            self.image_x.setRange(-100, 100)
            self.image_x.setSuffix(' %')
            self.remove_green = QCheckBox('Remove green screen')
            for label, widget in [('Size', self.image_scale), ('Top offset', self.image_top), ('Horizontal offset', self.image_x)]:
                widget.setAccessibleName(label)
                widget.setDecimals(0)
                widget.adjusted.connect(lambda message, name=label: message and self.notice(name + ': ' + message))
                widget.setFixedWidth(112)
                widget.lineEdit().setTextMargins(SPIN_TEXT_INSET, 0, 0, 0)
                adjustments.addRow(label, widget)
                widget.valueChanged.connect(self.invalidate_preview)
            controls.addLayout(adjustments)
            self.remove_green.toggled.connect(self.invalidate_preview)
            controls.addWidget(self.remove_green)
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
            from .media import video_formats, video_targets
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 22, 12, 14)
            layout.setSpacing(14)
            key = 'Mods/' + mod['id'] + '/' + mod['video_list']
            data = self.snapshot_for(mod).files[key]
            targets, self._video_formats = video_targets(data), video_formats(data)
            mods_dir = getattr(self.manager_for(mod), 'mods_dir', None) if self.manager else None
            replaced_folder = mods_dir / mod['id'] / mod['video_folder'] if mods_dir else None
            layout.addWidget(text_label('Replace a game video', 'sectionTitle'))
            layout.addWidget(text_label('Choose the original clip, then import your replacement MP4. '
                                        'Clips you already replaced are marked with a check.', 'muted'))
            self.video_choice = ChoiceField()
            self.video_choice.setAccessibleName('Video to replace')
            group = None
            for path in targets:
                folder = path.split('/')[2] if path.count('/') > 2 else 'Other'
                if group is not None and folder != group:
                    self.video_choice.insertSeparator(self.video_choice.count())
                group = folder
                name = path.rsplit('/', 1)[-1].rsplit('.', 1)[0]
                replaced = bool(replaced_folder and (replaced_folder / path).is_file())
                self.video_choice.addItem(icon('check', '#02e5a2') if replaced else QIcon(),
                                          folder + '  ·  ' + name, path)
                self.video_choice.setItemData(self.video_choice.count() - 1,
                                              path + ('\nReplaced by your video' if replaced else ''),
                                              Qt.ItemDataRole.ToolTipRole)
            self.video_choice.setMinimumContentsLength(18)
            self.video_choice.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            layout.addWidget(self.video_choice)
            layout.addSpacing(10)
            layout.addWidget(text_label('Match the original format', 'sectionTitle'))
            self.video_format = text_label('', 'muted')
            layout.addWidget(self.video_format)
            self.video_choice.currentIndexChanged.connect(self.video_target_changed)
            self.video_target_changed()
            layout.addStretch()
            layout.addWidget(text_label('Your source file is kept. Restart after restoring an original video.', 'muted'))
        self.media_scroll.setWidget(page)

    def video_target_changed(self, *args):
        path = self.video_choice.currentData() or ''
        original = self._video_formats.get(path)
        text = ('Original: ' + original + '.' if original else
                'The original format of this clip is not listed; see the mod guide.')
        if '/Fam/' in path:
            text += ' Fam clips need a pure green background (RGB 0, 255, 0).'
        self.video_format.setText(text)

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
            mod, target, data = self.current_mod, self._image_target, self._image_bytes
            manager = self.manager_for(mod)
            self.run_job('Saving replacement image…', lambda progress: manager.write_user_file(mod, target, data))

    def import_video(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose replacement video', '', 'MP4 video (*.mp4)')
        if not filename:
            return
        mod = self.current_mod
        manager = self.manager_for(mod)
        target = mod['video_folder'] + '/' + self.video_choice.currentData()
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
            mod = self.current_mod
            manager = self.manager_for(mod)
            self.run_job('Restoring original media…', lambda progress: manager.remove_user_file(mod, relative))

    def closeEvent(self, event: QCloseEvent):
        if self._busy or (self._import_dialog and self._import_dialog.busy):
            self.notice('Please wait for the current operation to finish before closing.')
            event.ignore()
        elif self.allow_discard():
            event.accept()
        else:
            event.ignore()
