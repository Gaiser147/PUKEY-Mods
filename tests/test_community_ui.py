import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox
from PySide6.QtTest import QTest

from manager.gui import Window


class CommunityUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def window(self, count=1):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        mods = [{'id': f'Mod{i}', 'name': f'Mod {i}', 'version': '1', 'description': '', 'controls': '',
                 'settings': [{'key': 'Mode', 'label': 'Camera mode', 'type': 'enum', 'default': 'possess',
                               'options': ['possess', 'viewtarget'], 'description': 'Choose camera ownership.',
                               'option_descriptions': {'possess': 'Possesses a spectator pawn.',
                                                       'viewtarget': 'Keeps the player pawn.'}}]}
                for i in range(count)]
        window = Window(SimpleNamespace(mods=mods, files={}, revision='test'),
                        preferences_path=Path(directory.name) / 'preferences.json', start_online=False)
        window.manager = SimpleNamespace(win64=Path(directory.name),
            status=lambda mod: {'installed': True, 'enabled': True, 'update': False, 'managed': True, 'version': '1'},
            settings=lambda mod: {'Mode': 'viewtarget'})
        window.render_details()
        window.show()
        self.addCleanup(lambda: (setattr(window, '_dirty', False), window.close()))
        return window

    def test_reset_changes_only_form_and_requires_save(self):
        window = self.window()
        self.assertTrue(hasattr(window, 'reset_buttons'))
        self.assertTrue(window.reset_buttons['Mode'].isEnabled())
        window.reset_buttons['Mode'].click()
        self.assertEqual(window.settings_widgets['Mode'].currentText(), 'possess')
        self.assertTrue(window._dirty)
        self.assertFalse(window.reset_buttons['Mode'].isEnabled())

    def test_info_contains_field_options_and_default_and_accepts_focus(self):
        window = self.window()
        self.assertTrue(hasattr(window, 'help_buttons'))
        button = window.help_buttons['Mode']
        self.assertIn('Keeps the player pawn', button.toolTip())
        self.assertIn('possess', button.toolTip())
        self.assertIn('Choose camera ownership', button.accessibleDescription())
        self.assertNotEqual(button.focusPolicy(), Qt.FocusPolicy.NoFocus)

    def test_vertical_wheel_scrolls_mods_without_selecting_them(self):
        window = self.window(30)
        window.resize(1024, 768)
        QTest.qWait(30)
        before = window.mod_list.currentRow()
        event = QWheelEvent(QPointF(80, 20), QPointF(80, 20), QPoint(), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(window.mod_list.viewport(), event)
        self.assertGreater(window.mod_list.horizontalScrollBar().value(), 0)
        self.assertEqual(window.mod_list.currentRow(), before)

    def test_mod_row_displays_enabled_even_when_update_available(self):
        window = self.window()
        window.manager.status = lambda mod: {'installed': True, 'enabled': True, 'update': True, 'managed': True, 'version': '1'}
        window.refresh_status_rows()
        text = window.mod_list.item(0).text()
        self.assertIn('Enabled', text)
        self.assertIn('Update', text)

    def test_external_source_adds_separate_tab_and_installation_entrypoints(self):
        from tests.test_community_service import package
        window = self.window()
        self.assertTrue(hasattr(window, 'add_mod_button'))
        self.assertTrue(hasattr(window, 'logs_button'))
        window.source_added('community-a', package(), ['Community'])
        self.assertEqual(window.mod_list.count(), 2)
        window.mod_list.setCurrentRow(1)
        self.assertEqual(window.current_mod['_source_id'], 'community-a')
        self.assertEqual(window.snapshot_for(window.current_mod).source_id, 'community-a')

    def test_external_video_targets_use_selected_source(self):
        from tests.test_manager import definition, snapshot
        window = self.window()
        mod = definition()
        mod.pop('images')
        external = snapshot(mod)
        external.source_id = 'community-a'
        window._source_packages['community-a'] = external
        window.current_mod = dict(mod, _source_id='community-a')
        window.render_details()
        self.assertEqual(window.video_choice.currentData(), 'Bacchus/Movie/Fam/test.mp4')

    def test_external_image_apply_uses_source_bound_manager(self):
        window = self.window()
        window._image_bytes = b'synthetic preview'
        window._image_target = 'bar.png'
        bound = SimpleNamespace(write_user_file=Mock())
        with patch.object(window, 'manager_for', return_value=bound), \
                patch.object(window, 'run_job', side_effect=lambda label, operation: operation(lambda _: None)):
            window.apply_image()
        bound.write_user_file.assert_called_once_with(window.current_mod, 'bar.png', b'synthetic preview')


if __name__ == '__main__':
    unittest.main()
