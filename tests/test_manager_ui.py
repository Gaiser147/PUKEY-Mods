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
        viewport = window.media_scroll.viewport()
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
        self.assertGreaterEqual(window.tabs.indexOf(window.keys_scroll), 0)
        self.assertTrue(window.keys_scroll.isAncestorOf(window.settings_widgets['ToggleKey']))
        self.assertTrue(window.settings_scroll.isAncestorOf(window.settings_widgets['Speed']))
        window.tabs.setCurrentWidget(window.keys_scroll)
        window.settings_widgets['ToggleKey'].setCurrentText('F6')
        self.assertTrue(window.save_button.isEnabled())
        self.assertFalse(window.save_button.isHidden())
        window._dirty = False

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
