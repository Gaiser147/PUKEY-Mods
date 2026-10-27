import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox
    from PySide6.QtTest import QTest
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, 'Install manager/requirements.txt for Qt smoke tests')
class ManagerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def make_window(self, snapshot=None):
        from manager.gui import Window
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        window = Window(snapshot=snapshot, preferences_path=Path(directory.name) / 'prefs.json', start_online=False)
        self.addCleanup(window.close)
        return window

    def test_empty_state_keeps_installation_disabled(self):
        window = self.make_window()
        self.assertFalse(window.install_button.isEnabled())
        self.assertTrue(window.refresh_button.isEnabled())

    def test_first_run_shows_setup_instead_of_an_inactive_editor(self):
        window = self.make_window()
        self.assertFalse(window.empty_state.isHidden())
        self.assertTrue(window.tabs.isHidden())
        self.assertTrue(window.detail_footer.isHidden())

    def test_startup_needs_no_game_artwork(self):
        window = self.make_window()
        self.assertTrue(hasattr(window, 'theme_directory'), 'The interface must start without bundled game art')
        self.assertIsNone(window.theme_directory)
        self.assertTrue(window.logo_label.pixmap().isNull())
        self.assertEqual(window.logo_label.text(), 'PUKEY')

    def test_cached_game_art_is_not_applied_without_an_installation(self):
        window = self.make_window()
        self.assertTrue(hasattr(window, 'apply_game_theme'), 'Game artwork must be installation-gated')
        self.assertFalse(window.apply_game_theme(window.preferences_path.parent))
        self.assertIsNone(window.theme_directory)

    def test_game_art_is_cleared_when_the_selected_game_disappears(self):
        from PIL import Image
        window = self.make_window()
        self.assertTrue(hasattr(window, 'apply_game_theme'), 'Game artwork must be installation-gated')
        win64 = window.preferences_path.parent / 'Game'
        window.manager = SimpleNamespace(win64=win64)
        cache = window.preferences_path.parent / 'game-ui'
        cache.mkdir()
        for name in ('logo', 'dialogue', 'sheet', 'ribbon', 'button-pink', 'heading', 'divider'):
            Image.new('RGBA', (160, 160), (20, 35, 30, 255)).save(cache / (name + '.png'))
        with patch('manager.game_assets.game_present', return_value=True):
            self.assertTrue(window.apply_game_theme(cache, win64))
        self.assertEqual(window.theme_directory, cache)
        self.assertFalse(window.logo_label.pixmap().isNull())
        with patch('manager.game_assets.game_present', return_value=False):
            window.refresh_game_theme_presence()
        self.assertIsNone(window.theme_directory)
        self.assertTrue(window.logo_label.pixmap().isNull())

    def test_game_theme_paints_primary_action_artwork(self):
        from PIL import Image
        window = self.make_window()
        win64 = window.preferences_path.parent / 'Game'
        window.manager = SimpleNamespace(win64=win64)
        cache = window.preferences_path.parent / 'game ui'
        cache.mkdir()
        for name in ('logo', 'dialogue', 'sheet', 'ribbon', 'heading', 'divider'):
            Image.new('RGBA', (160, 160), (20, 35, 30, 255)).save(cache / (name + '.png'))
        Image.new('RGBA', (120, 60), (0, 200, 40, 255)).save(cache / 'button-pink.png')
        with patch('manager.game_assets.game_present', return_value=True):
            self.assertTrue(window.apply_game_theme(cache, win64))
        button = window.save_button
        button.setEnabled(True)
        button.resize(200, 40)
        button.ensurePolished()
        pixel = button.grab().toImage().pixelColor(100, 20)
        self.assertGreater(pixel.green(), 150, 'The enabled primary action must show its button artwork')

    def test_image_preparation_actions_fit_the_small_desktop_view(self):
        from manager.catalog import Snapshot
        snapshot = Snapshot.from_directory(Path(__file__).resolve().parents[1])
        with patch('manager.gui.sys.platform', 'linux'):
            window = self.make_window(snapshot)
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True, 'version': mod['version']},
            settings=lambda mod: {field['key']: field['default'] for field in mod.get('settings', [])})
        window.mod_list.setCurrentRow(2)
        window.tabs.setCurrentWidget(window.media_scroll)
        window.resize(1024, 768)
        window.show()
        QTest.qWait(30)
        viewport = window.detail_footer
        for button in (window.preview_button, window.restore_image_button):
            self.assertTrue(viewport.rect().contains(button.mapTo(viewport, button.rect().topLeft())))
            self.assertTrue(viewport.rect().contains(button.mapTo(viewport, button.rect().bottomRight())))

    def test_keybindings_have_their_own_view_and_share_save_state(self):
        mod = {'id': 'Example', 'name': 'Example', 'version': '1.0', 'description': '', 'controls': 'F5: toggle',
               'settings': [{'key': 'Speed', 'label': 'Speed', 'type': 'number', 'default': 20,
                             'min': 1, 'max': 100, 'step': 1},
                            {'key': 'ToggleKey', 'label': 'Toggle', 'type': 'key', 'default': 'F5'}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True, 'version': '1.0'},
            settings=lambda mod: {'Speed': 20, 'ToggleKey': 'F5'})
        window.render_details()
        self.assertTrue(hasattr(window, 'keys_panel'), 'Keybindings need their own dialogue sheet')
        self.assertTrue(window.keys_panel.isAncestorOf(window.keys_scroll))
        self.assertTrue(window.keys_scroll.isAncestorOf(window.settings_widgets['ToggleKey']))
        self.assertTrue(window.settings_scroll.isAncestorOf(window.settings_widgets['Speed']))
        window.settings_widgets['ToggleKey'].setCurrentText('F6')
        self.assertTrue(window.save_button.isEnabled())
        self.assertFalse(window.save_button.isHidden())
        window._dirty = False

    def test_video_actions_stay_visible_with_game_setup_expanded(self):
        from manager.catalog import Snapshot
        snapshot = Snapshot.from_directory(Path(__file__).resolve().parents[1])
        window = self.make_window(snapshot)
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True, 'version': mod['version']},
            settings=lambda mod: {field['key']: field['default'] for field in mod.get('settings', [])})
        window.mod_list.setCurrentRow(3)
        window.tabs.setCurrentWidget(window.media_scroll)
        window.resize(1024, 768)
        window.show()
        QTest.qWait(30)
        self.assertFalse(window.game_panel.isHidden())
        self.assertTrue(hasattr(window, 'import_video_button'), 'Video import needs a persistent action')
        for button in (window.import_video_button, window.restore_video_button):
            self.assertFalse(button.isHidden())
            self.assertTrue(window.detail_footer.rect().contains(
                button.mapTo(window.detail_footer, button.rect().bottomRight())))

    def test_horizontal_catalogue_keeps_future_mods_reachable(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListView
        mods = [{'id': f'Example{i}', 'name': f'Future mod {i}', 'version': '1.0',
                 'description': '', 'controls': '', 'settings': []} for i in range(12)]
        window = self.make_window(SimpleNamespace(mods=mods, files={}, revision='test'))
        window.resize(1024, 768)
        window.show()
        self.assertEqual(window.mod_list.flow(), QListView.Flow.LeftToRight)
        window.mod_list.setFocus()
        QTest.keyClick(window.mod_list, Qt.Key.Key_End)
        QTest.qWait(30)
        self.assertEqual(window.current_mod['id'], 'Example11')
        self.assertTrue(window.mod_list.viewport().rect().intersects(
            window.mod_list.visualItemRect(window.mod_list.currentItem())))

    def test_popup_and_confirmation_surfaces_are_opaque_and_dark(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QMessageBox
        mod = {'id': 'Example', 'name': 'Example', 'version': '1.0', 'description': '', 'controls': '',
               'settings': [{'key': 'Mode', 'label': 'Mode', 'type': 'enum', 'default': 'idle',
                             'options': ['idle', 'always', 'other']}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.show()
        combo = window.settings_widgets['Mode']
        combo.setEnabled(True)
        combo.showPopup()
        QTest.qWait(30)
        view = combo.view()
        point = view.visualRect(combo.model().index(2, 0)).bottomLeft() + QPoint(3, -2)
        pixel = view.viewport().grab().toImage().pixelColor(point)
        combo.hidePopup()
        self.assertGreater(pixel.alpha(), 240)
        self.assertLess(pixel.lightness(), 100)
        box = QMessageBox(window)
        self.addCleanup(box.close)
        box.setText('Remove the selected mod? Personal files are preserved.')
        box.show()
        QTest.qWait(30)
        pixel = box.grab().toImage().pixelColor(5, box.height() // 2)
        self.assertGreater(pixel.alpha(), 240)
        self.assertLess(pixel.lightness(), 100)

    def test_game_setup_can_be_reopened_after_selecting_a_ready_game(self):
        window = self.make_window()
        game = window.preferences_path.parent / 'Game'
        win64 = game / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64'
        (win64 / 'ue4ss').mkdir(parents=True)
        for filename in ('PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe', 'dwmapi.dll', 'ue4ss/UE4SS.dll'):
            (win64 / filename).touch()
        window.set_game(game)
        self.assertTrue(hasattr(window, 'game_panel'), 'Game setup needs a collapsible panel')
        self.assertTrue(window.game_panel.isHidden())
        window.folder_button.click()
        self.assertFalse(window.game_panel.isHidden())
        self.assertEqual(window.path_edit.text(), str(game))

    def test_selected_mod_header_exposes_installation_state(self):
        mod = {'id': 'Example', 'name': 'Example', 'version': '1.1', 'description': '', 'controls': '', 'settings': []}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True, 'version': '1.1'},
            settings=lambda mod: {})
        window.render_details()
        self.assertIn('1.1', window.mod_status_label.text())
        self.assertIn('Installed', window.mod_status_label.text())

    def test_new_catalogue_mod_generates_settings_without_ui_changes(self):
        mod = {'id': 'FutureMod', 'name': 'Future Mod', 'version': '1.0',
               'description': 'A later mod', 'controls': 'F12', 'files': ['Scripts/main.lua'],
               'settings': [{'key': 'Speed', 'label': 'Speed', 'type': 'number', 'default': 20,
                             'min': 1, 'max': 100, 'step': 1},
                            {'key': 'Mode', 'label': 'Mode', 'type': 'enum', 'default': 'idle',
                             'options': ['idle', 'always']}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        self.assertEqual(window.mod_list.count(), 1)
        self.assertEqual(window.current_mod['id'], 'FutureMod')
        self.assertIsInstance(window.settings_widgets['Speed'], QDoubleSpinBox)
        self.assertIsInstance(window.settings_widgets['Mode'], QComboBox)
        self.assertEqual(window.settings_widgets['Speed'].value(), 20)

    def test_failed_background_job_recovers_controls_and_shows_error(self):
        window = self.make_window()
        def fail(progress):
            raise RuntimeError('Download failed. Try again.')
        window.run_job('Loading', fail)
        for _ in range(100):
            QTest.qWait(20)
            if not window._busy:
                break
        self.assertFalse(window._busy)
        self.assertTrue(window.refresh_button.isEnabled())
        self.assertIn('Download failed', window.status_label.text())

    def test_errors_name_their_own_next_step(self):
        from urllib.error import HTTPError, URLError
        from manager.gui import describe_error
        self.assertIn('internet connection', describe_error(URLError('getaddrinfo failed')))
        forbidden = HTTPError('https://example.invalid', 403, 'Forbidden', {}, None)
        self.addCleanup(forbidden.close)
        self.assertIn('HTTP 403', describe_error(forbidden))
        locked = describe_error(PermissionError(13, 'Access is denied', 'C:/Game/dwmapi.dll'))
        self.assertIn('C:/Game/dwmapi.dll', locked)
        self.assertIn('Close the game', locked)
        self.assertEqual(describe_error(ValueError('Invalid ZIP archive')), 'Invalid ZIP archive')
        self.assertNotIn('connection', describe_error(ValueError('Invalid ZIP archive')))

    def test_background_notices_keep_an_unhandled_error_visible(self):
        window = self.make_window()
        window.notice('The download server could not be reached.', True)
        window.notice('Game interface artwork loaded from your installation.', background=True)
        self.assertIn('could not be reached', window.status_label.text())
        self.assertFalse(window.status_icon.isHidden())
        window.notice('Installing FreeCam…')
        self.assertEqual(window.status_label.text(), 'Installing FreeCam…')
        self.assertTrue(window.status_icon.isHidden())

    def test_key_conflicts_are_flagged_within_and_across_mods(self):
        key = lambda name, default: {'key': name, 'label': name, 'type': 'key', 'default': default}
        first = {'id': 'First', 'name': 'First', 'version': '1.0', 'description': '', 'controls': '',
                 'settings': [key('Toggle', 'F5'), key('Mode', 'F6')]}
        other = {'id': 'Other', 'name': 'Other', 'version': '1.0', 'description': '', 'controls': '',
                 'settings': [key('Flood', 'F1')]}
        idle = {'id': 'Idle', 'name': 'Idle', 'version': '1.0', 'description': '', 'controls': '',
                'settings': [key('Reload', 'F2')]}
        window = self.make_window(SimpleNamespace(mods=[first, other, idle], files={}, revision='test'))
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': mod['id'] != 'Idle', 'update': False, 'managed': True},
            settings=lambda mod: {field['key']: field['default'] for field in mod['settings']})
        window.mod_list.setCurrentRow(0)
        window.render_details()
        self.assertTrue(window.key_warnings['Toggle'].isHidden())
        toggle = window.settings_widgets['Toggle']
        toggle.setCurrentIndex(toggle.findData('F6'))
        self.assertFalse(window.key_warnings['Toggle'].isHidden())
        self.assertIn('Mode', window.key_warnings['Toggle'].text())
        self.assertIn('Toggle', window.key_warnings['Mode'].text())
        toggle.setCurrentIndex(toggle.findData('F1'))
        self.assertIn('Other: Flood', window.key_warnings['Toggle'].text())
        self.assertTrue(window.key_warnings['Mode'].isHidden())
        toggle.setCurrentIndex(toggle.findData('F2'))
        self.assertTrue(window.key_warnings['Toggle'].isHidden(), 'Disabled mods do not compete for keys')
        self.assertEqual(window.field_value(toggle), 'F2')
        window._dirty = False

    def input_window(self):
        mod = {'id': 'Example', 'name': 'Example', 'version': '1.0', 'description': '', 'controls': '',
               'settings': [{'key': 'Boost', 'label': 'Boost', 'type': 'number', 'default': 4, 'min': 1, 'max': 20, 'step': 0.5},
                            {'key': 'Sens', 'label': 'Sensitivity', 'type': 'number', 'default': 0.15, 'min': 0.01, 'max': 5, 'step': 0.01},
                            {'key': 'Mode', 'label': 'Mode', 'type': 'enum', 'default': 'a', 'options': ['a', 'b']},
                            {'key': 'Toggle', 'label': 'Toggle', 'type': 'key', 'default': 'F5'}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True},
            settings=lambda mod: {'Boost': 4, 'Sens': 0.15, 'Mode': 'a', 'Toggle': 'F5'})
        window.render_details()
        window.show()
        window.activateWindow()
        QTest.qWait(20)
        self.addCleanup(setattr, window, '_dirty', False)
        return window

    def test_wheel_scrolls_past_unfocused_fields(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        window = self.input_window()
        window.mod_list.setFocus()
        for key in ('Boost', 'Mode', 'Toggle'):
            widget = window.settings_widgets[key]
            before = window.field_value(widget)
            event = QWheelEvent(QPointF(5, 5), widget.mapToGlobal(QPointF(5, 5)), QPoint(0, 0), QPoint(0, -120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(widget, event)
            self.assertEqual(window.field_value(widget), before, key + ' must not change without focus')
        self.assertFalse(window._dirty)

    def test_number_fields_accept_both_decimal_marks_and_explain_corrections(self):
        from PySide6.QtCore import QLocale, Qt
        window = self.input_window()
        boost, sens = window.settings_widgets['Boost'], window.settings_widgets['Sens']
        for widget in (boost, sens):
            widget.setLocale(QLocale(QLocale.Language.German))
        for text, expected in (('1.5', 1.5), ('2,5', 2.5)):
            boost.setFocus()
            boost.selectAll()
            QTest.keyClicks(boost, text)
            QTest.keyClick(boost, Qt.Key.Key_Return)
            self.assertEqual(boost.value(), expected)
        boost.selectAll()
        QTest.keyClicks(boost, '99999')
        QTest.keyClick(boost, Qt.Key.Key_Return)
        self.assertEqual(boost.value(), 20)
        self.assertFalse(window.field_notes['Boost'].isHidden())
        self.assertIn('Maximum is 20', window.field_notes['Boost'].text())
        sens.setFocus()
        sens.selectAll()
        QTest.keyClicks(sens, '0.005')
        QTest.keyClick(sens, Qt.Key.Key_Return)
        self.assertEqual(sens.value(), 0.01)
        self.assertIn('Rounded', window.field_notes['Sens'].text())
        self.assertIn('Range', sens.toolTip())

    def test_help_numbers_follow_the_field_locale(self):
        from PySide6.QtCore import QLocale
        from manager.setting_help import explanation
        previous = QLocale()
        QLocale.setDefault(QLocale(QLocale.Language.German))
        self.addCleanup(QLocale.setDefault, previous)
        text = explanation({'key': 'Sens', 'label': 'Sensitivity', 'type': 'number', 'default': 0.15, 'min': 0.01, 'max': 5})
        self.assertIn('Default: 0,15', text)
        self.assertIn('Range: 0,01 – 5', text)

    def test_keys_can_be_assigned_by_pressing_them(self):
        from PySide6.QtCore import Qt
        window = self.input_window()
        capture, toggle = window.capture_buttons['Toggle'], window.settings_widgets['Toggle']
        capture.click()
        self.assertTrue(capture.isChecked())
        QTest.keyClick(capture, Qt.Key.Key_F7)
        self.assertEqual(window.field_value(toggle), 'F7')
        self.assertFalse(capture.isChecked())
        capture.click()
        QTest.keyClick(capture, Qt.Key.Key_Escape)
        self.assertEqual(window.field_value(toggle), 'F7')
        capture.click()
        QTest.keyClick(capture, Qt.Key.Key_5, Qt.KeyboardModifier.KeypadModifier)
        self.assertEqual(window.field_value(toggle), 'F7')
        self.assertIn('cannot be assigned', window.status_label.text())

    def test_wide_windows_keep_settings_near_their_labels(self):
        window = self.input_window()
        window.resize(2000, 1000)
        QTest.qWait(20)
        self.assertLessEqual(window.settings_page.width(), 760)
        self.assertEqual(window.keys_panel.width(), 340)
        window.resize(1280, 860)
        QTest.qWait(20)
        self.assertEqual(window.keys_panel.width(), 280)

    def test_fractional_values_do_not_round_to_step_precision(self):
        mod = {'id': 'Example', 'name': 'Example', 'description': '', 'controls': '',
               'settings': [{'key': 'Intensity', 'label': 'Intensity', 'type': 'number',
                             'default': 0.25, 'min': 0.01, 'max': 100, 'step': 1}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        field = window.settings_widgets['Intensity']
        self.assertEqual(field.minimum(), 0.01)
        self.assertEqual(field.value(), 0.25)

    def test_invalidated_preview_disables_footer_action(self):
        mod = {'id': 'Example', 'name': 'Example', 'description': '', 'controls': '', 'settings': [],
               'images': [{'file': 'bar.png', 'label': 'Bar', 'width': 10, 'height': 10,
                           'background': 'transparent'}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.manager = SimpleNamespace(win64=window.preferences_path.parent,
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True},
            settings=lambda mod: {})
        window.render_details()
        window.tabs.setCurrentIndex(1)
        window._image_bytes = b'preview'
        window.update_controls()
        self.assertTrue(window.apply_footer_button.isEnabled())
        window.invalidate_preview()
        self.assertFalse(window.apply_footer_button.isEnabled())

    def test_background_action_preserves_unsaved_settings(self):
        mod = {'id': 'Example', 'name': 'Example', 'description': '', 'controls': '',
               'settings': [{'key': 'Speed', 'label': 'Speed', 'type': 'number',
                             'default': 20, 'min': 1, 'max': 100, 'step': 1}]}
        window = self.make_window(SimpleNamespace(mods=[mod], files={}, revision='test'))
        window.settings_widgets['Speed'].setValue(77)
        self.assertTrue(window._dirty)
        window.run_job('Another action', lambda progress: None)
        for _ in range(100):
            QTest.qWait(20)
            if not window._busy:
                break
        self.assertEqual(window.settings_widgets['Speed'].value(), 77)
        self.assertTrue(window._dirty)
        window._dirty = False
