import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

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
