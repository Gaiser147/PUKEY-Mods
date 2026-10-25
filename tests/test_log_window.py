import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
except ImportError:
    QApplication = None
else:
    from manager.log_window import LogsWindow, MAX_RENDER_LINES, MAX_LINE_CHARS


@unittest.skipIf(QApplication is None, 'Install manager/requirements.txt for Qt smoke tests')
class LogsWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.log = self.root / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64/ue4ss/UE4SS.log'
        self.log.parent.mkdir(parents=True)
        self.window = LogsWindow(self.root)
        self.addCleanup(self.window.close)

    def wait_for(self, predicate, timeout=3000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            QTest.qWait(10)
        self.fail('Timed out waiting for log worker')

    def test_modeless_readonly_view_waits_for_missing_file(self):
        self.assertFalse(self.window.isModal())
        self.assertTrue(self.window.text.isReadOnly())
        self.assertFalse(self.window._timer.isActive())
        self.window.show()
        self.wait_for(lambda: 'Waiting' in self.window.status.text())
        self.assertTrue(self.window._timer.isActive())
        self.assertEqual(self.window._timer.interval(), 1000)
        self.window.hide()
        self.assertFalse(self.window._timer.isActive())

    def test_filter_copy_pause_and_resume(self):
        self.log.write_bytes(b'alpha\nbeta\n')
        self.window.show()
        self.wait_for(lambda: 'beta' in self.window.text.toPlainText())
        self.window.filter_edit.setText('alpha')
        self.assertEqual(self.window.text.toPlainText().strip(), 'alpha')
        self.window.copy_visible()
        self.assertEqual(self.app.clipboard().text().strip(), 'alpha')
        self.window.live_button.click()
        self.assertFalse(self.window._timer.isActive())
        with self.log.open('ab') as stream:
            stream.write(b'alpha new\n')
        self.window._tick()
        QTest.qWait(20)
        self.assertNotIn('new', self.window.text.toPlainText())
        self.window.live_button.click()
        self.wait_for(lambda: 'alpha new' in self.window.text.toPlainText())

    def test_render_caps_lines_and_unterminated_long_line(self):
        self.log.write_bytes((b'line\n' * (MAX_RENDER_LINES + 2000)) + b'x' * (MAX_LINE_CHARS * 3))
        self.window.show()
        self.wait_for(lambda: 'x' in self.window.text.toPlainText())
        self.assertLessEqual(self.window.text.document().blockCount(), MAX_RENDER_LINES)
        self.assertLessEqual(max(map(len, self.window.text.toPlainText().splitlines())), MAX_LINE_CHARS)
        self.assertIn('truncated', self.window.text.toPlainText())

    def test_close_while_reading_does_not_wait_for_worker(self):
        from manager.logs import TailReader
        original = TailReader.poll
        def slow_poll(reader):
            time.sleep(.2)
            return original(reader)
        with patch.object(TailReader, 'poll', slow_poll):
            self.window.show()
            self.wait_for(lambda: self.window._job is not None and self.window._job.kind == 'read')
            started = time.monotonic()
            self.window.close()
            self.assertLess(time.monotonic() - started, .1)
            self.assertFalse(self.window._timer.isActive())
            self.wait_for(lambda: self.window._job is None)

    def test_open_folder_uses_local_existing_ancestor(self):
        with patch('manager.log_window.QDesktopServices.openUrl') as opening:
            self.window.open_folder()
        self.assertTrue(opening.call_args.args[0].isLocalFile())
        self.assertTrue(Path(opening.call_args.args[0].toLocalFile()).is_dir())
    def test_reopen_refreshes_after_a_read_completed_while_closed(self):
        from manager.logs import TailReader
        self.log.write_bytes(b'before\n')
        self.window.show()
        self.wait_for(lambda: 'before' in self.window.text.toPlainText())
        self.wait_for(lambda: self.window._job is None)
        original = TailReader.poll
        def slow_poll(reader):
            time.sleep(.1)
            return original(reader)
        self.window._timer.stop()
        with patch.object(TailReader, 'poll', slow_poll):
            with self.log.open('ab') as stream:
                stream.write(b'closed update\n')
            self.window._tick()
            self.window.close()
            self.wait_for(lambda: self.window._job is None)
        self.window.show()
        self.wait_for(lambda: 'closed update' in self.window.text.toPlainText())
