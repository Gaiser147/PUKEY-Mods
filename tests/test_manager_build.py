import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


class ManagerBuildTests(unittest.TestCase):
    def test_windows_build_excludes_unrelated_native_dll_directories(self):
        from tools.build_manager import build_environment
        with patch.dict(os.environ, {'PATH': 'foreign-poppler-dlls', 'SystemRoot': 'C:/Windows'}):
            with patch('tools.build_manager.sys.platform', 'win32'):
                result = build_environment()
            self.assertEqual(os.environ['PATH'], 'foreign-poppler-dlls')
        self.assertNotIn('foreign-poppler-dlls', result['PATH'])
        self.assertIn(str(Path(sys.executable).parent), result['PATH'])
        self.assertIn(str(Path('C:/Windows') / 'System32'), result['PATH'])

    def test_linux_build_preserves_toolchain_search_path(self):
        from tools.build_manager import build_environment
        with patch.dict(os.environ, {'PATH': '/usr/bin:/bin'}):
            with patch('tools.build_manager.sys.platform', 'linux'):
                self.assertEqual(build_environment()['PATH'], '/usr/bin:/bin')

    def test_windows_build_honours_non_default_uppercase_system_root(self):
        from tools.build_manager import build_environment
        with patch.dict(os.environ, {'SYSTEMROOT': 'D:/Windows', 'PATH': 'foreign-dlls'}, clear=True):
            with patch('tools.build_manager.sys.platform', 'win32'):
                result = build_environment()
        self.assertIn(str(Path('D:/Windows') / 'System32'), result['PATH'])
