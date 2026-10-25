import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
import time
import unittest
import zipfile

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from manager.import_dialog import ImportDialog
from manager.sources import SourceStore


class ImportDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait(self, dialog):
        end = time.monotonic() + 10
        while dialog.busy and time.monotonic() < end: QTest.qWait(10)
        self.assertFalse(dialog.busy, 'Source operation did not finish')

    def test_inspect_select_add_and_reopen_cached_source_without_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'Example.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('Example/scripts/main.lua', 'print("synthetic only")')
                package.writestr('Example/config.ini', '[Camera]\nSpeed=1\n')
            store = SourceStore(root / 'library')
            added = []
            dialog = ImportDialog(store, lambda *result: added.append(result))
            dialog.show()
            dialog.origin.setText(str(archive))
            dialog.analyze()
            self.wait(dialog)
            self.assertEqual(dialog.mods.count(), 1)
            self.assertTrue(dialog.add_button.isEnabled())
            self.assertEqual(store.records, [])
            dialog.add_button.click()
            self.wait(dialog)
            self.assertEqual(len(added), 1)
            source_id, snapshot, selected = added[0]
            self.assertEqual(snapshot.source_id, source_id)
            self.assertEqual(selected, ['Example'])
            self.assertEqual(store.load(source_id).mods[0]['default_files'], ['config.ini'])
            dialog.origin.setText('https://example.invalid/another.zip')
            self.assertFalse(dialog.add_button.isEnabled())
            self.assertIsNone(dialog.snapshot)
            dialog.close()

    def test_editing_origin_hides_previous_release_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            dialog = ImportDialog(SourceStore(Path(directory)), lambda *args: None)
            dialog.show()
            dialog.choices.addItem('Old asset', 'https://example.invalid/old.zip')
            dialog.choices.show()
            dialog.use_choice.show()
            dialog.origin.setText('https://example.invalid/new.zip')
            self.assertTrue(dialog.choices.isHidden())
            self.assertTrue(dialog.use_choice.isHidden())
            dialog.close()


if __name__ == '__main__':
    unittest.main()
