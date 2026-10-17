from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gui'))
import calculator_decimal as decimal

SOURCE = '''[Desktop Entry]
Type=Application
Name=Deepin Calculator
Name[pt_BR]=Calculadora
Icon=deepin-calculator
Exec=/usr/bin/ll-cli run org.deepin.calculator -- deepin-calculator
TryExec=/usr/bin/ll-cli
'''


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.source = root / 'official.desktop'
        self.source.write_text(SOURCE)
        self.refresh = Mock()
        self.manager = decimal.CalculatorDecimal(home=root, data_home=root / 'user data',
                                                   sources=[self.source], refresh=self.refresh)
        for file in (self.manager.plugin, self.manager.launcher):
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('test resource')

    def test_query_is_read_only(self):
        self.assertFalse(self.manager.status()['enabled'])
        self.assertFalse(self.manager.desktop.exists())
        self.assertFalse(self.manager.flag.exists())

    def test_enable_and_rollback_preserve_official_launcher(self):
        self.manager.configure(True)
        self.assertTrue(self.manager.status()['enabled'])
        content = self.manager.desktop.read_text()
        self.assertIn('Name[pt_BR]=Calculadora', content)
        self.assertIn('Icon=deepin-calculator', content)
        self.assertIn('Exec="' + str(self.manager.launcher) + '"', content)
        self.assertEqual(self.manager.flag.stat().st_mode & 0o777, 0o600)
        self.manager.configure(False)
        self.assertFalse(self.manager.desktop.exists())
        self.assertFalse(self.manager.flag.exists())
        self.assertEqual(self.source.read_text(), SOURCE)
        self.assertTrue(self.manager.plugin.exists())
        self.assertEqual(self.refresh.call_count, 2)

    def test_custom_launcher_and_symlink_are_never_overwritten(self):
        self.manager.desktop.parent.mkdir(parents=True)
        self.manager.desktop.write_text('custom launcher')
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(True)
        self.assertEqual(self.manager.desktop.read_text(), 'custom launcher')
        self.manager.desktop.unlink()
        self.manager.desktop.symlink_to(self.source)
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(True)
        self.assertEqual(self.source.read_text(), SOURCE)

    def test_manually_edited_managed_launcher_is_not_removed(self):
        self.manager.configure(True)
        self.manager.desktop.write_text('custom launcher')
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(False)
        self.assertTrue(self.manager.flag.exists())
        self.assertEqual(self.manager.desktop.read_text(), 'custom launcher')

    def test_invalid_or_unowned_marker_is_preserved(self):
        self.manager.flag.write_text('[]')
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(True)
        self.assertEqual(self.manager.flag.read_text(), '[]')

    def test_missing_plugin_does_not_change_desktop(self):
        self.manager.plugin.unlink()
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(True)
        self.assertFalse(self.manager.desktop.exists())

    def test_unsupported_launcher_is_not_executed_or_modified(self):
        self.source.write_text(SOURCE.replace('deepin-calculator\nTryExec', 'unknown-argument\nTryExec'))
        with self.assertRaises(decimal.CalculatorError):
            self.manager.configure(True)
        self.assertFalse(self.manager.flag.exists())

    def test_flag_write_failure_removes_new_override(self):
        original = decimal.atomic
        def fail_flag(path, data, mode=0o644):
            if path == self.manager.flag:
                raise OSError('test failure')
            return original(path, data, mode)
        with patch.object(decimal, 'atomic', side_effect=fail_flag):
            with self.assertRaises(OSError):
                self.manager.configure(True)
        self.assertFalse(self.manager.desktop.exists())
        self.assertEqual(self.manager.capture(), {'enabled': False})

    def test_official_metadata_update_is_used_on_reenable(self):
        self.manager.configure(True)
        self.source.write_text(SOURCE.replace('Name=Deepin Calculator', 'Name=Calculator Updated'))
        self.manager.configure(True)
        self.assertIn('Name=Calculator Updated', self.manager.desktop.read_text())
        self.manager.configure(False)

    def test_desktop_quoting_escapes_expansion_characters(self):
        result = decimal.desktop_quote('/tmp/space $name`x"%.sh')
        self.assertEqual(result, '"/tmp/space \\$name\\`x\\"%%.sh"')
