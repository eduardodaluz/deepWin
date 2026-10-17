"""Teste do plugin Qt real; usa os headers em cache sem instalar pacotes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QtCalculatorTests(unittest.TestCase):
    def test_native_event_filter_and_rollback(self):
        sdk = ROOT / '.build/deepwin/sdk'
        headers = sdk / 'usr/include/x86_64-linux-gnu/qt6'
        moc = sdk / 'usr/lib/qt6/libexec/moc'
        plugins = ROOT / '.build/deepwin/qt6/plugins'
        if not (headers / 'QtWidgets/QApplication').exists() or not moc.exists() or not plugins.exists():
            self.skipTest('Compile o DeepWin com --fetch-sdk para executar o teste Qt nativo.')
        with tempfile.TemporaryDirectory() as temporary:
            build = Path(temporary)
            flags = [arg for path in (headers, headers/'QtCore', headers/'QtGui', headers/'QtWidgets')
                     for arg in ('-I', str(path))]
            source = ROOT / 'tests/calculator_decimal_qt.cpp'
            subprocess.run([str(moc), *flags, str(source), '-o', str(build/'calculator_decimal_qt.moc')],
                           check=True, capture_output=True, timeout=20)
            subprocess.run(['g++', '-std=c++17', '-fPIC', *flags, '-I', str(build), str(source),
                            '-o', str(build/'qt-test'), '-l:libQt6Widgets.so.6',
                            '-l:libQt6Gui.so.6', '-l:libQt6Core.so.6'],
                           check=True, capture_output=True, timeout=40)
            result = subprocess.run([str(build/'qt-test'), str(plugins)], capture_output=True,
                                    text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS Qt: 3000 teclas sem perda', result.stdout)
