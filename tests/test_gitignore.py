"""Verifica as regras usando o proprio Git em um repositorio temporario."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class GitignoreTests(unittest.TestCase):
    def test_local_outputs_and_secrets_are_ignored_while_sources_remain_visible(self):
        root = Path(__file__).resolve().parents[1]
        ignored = [
            '.build/deepwin/sdk/usr/include/QtCore.h', 'build/CMakeCache.txt',
            'cmake-build-debug/DeepWin', 'build-Debug/DeepWin',
            'CMakeCache.txt', 'CMakeUserPresets.json', 'compile_commands.json',
            'CMakeFiles/test.o', 'DeepWin_autogen/mocs_compilation.cpp',
            'moc_main.cpp', 'ui_main.h', 'qrc_assets.cpp', 'pt_BR.qm',
            '.qmake.stash', 'DeepWin.pro.user', 'CMakeLists.txt.user',
            'devedu.deepin-configs_1.0.0_amd64.deb', 'DeepWin.uab',
            'debian/.debhelper/state', 'debian/devedu.deepin-configs/bin/deepwin',
            'debian/devedu.deepin-configs.substvars',
            '__pycache__/backend.cpython-312.pyc', '.venv/bin/python',
            '.env', '.env.local', 'private/api_key', 'credentials.json',
            'server.key', 'server.pem', '.aws/credentials', '.codex/auth.json',
            '.local/state/devedu.deepin-configs/originals.json',
            'state/controller.lock', 'backups/settings.json', 'test.log',
            'claude-selection.json', 'claude-versions.lock', 'claude-versions.json',
            'calculator-enabled.json',
        ]
        visible = [
            'gui/main.cpp', 'gui/backend.py', 'gui/preview.png',
            'gui/calculator_decimal.cpp', 'gui/calculator_decimal.json',
            'bin/deepwin', 'bin/build-deepwin', 'deepwin.yml', '.gitignore',
            'CMakeLists.txt', 'CMakePresets.json', 'cmake/Options.cmake',
            'translations/pt_BR.ts', 'resources/assets.qrc',
            'packaging/devedu.deepin-configs.desktop',
            'debian/control', 'debian/changelog', 'debian/rules',
            '.env.example', '.env.sample',
        ]
        with tempfile.TemporaryDirectory(prefix='deepwin-ignore-') as directory:
            subprocess.run(['git', 'init', '-q', directory], check=True)
            shutil.copyfile(root / '.gitignore', Path(directory) / '.gitignore')
            result = subprocess.run(['git', '-C', directory, 'check-ignore', '--no-index',
                                     '-z', '--stdin'], input='\0'.join(ignored + visible) + '\0',
                                    text=True, capture_output=True, check=False)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            matched = set(result.stdout.rstrip('\0').split('\0'))
            for name in ignored:
                with self.subTest(ignored=name):
                    self.assertIn(name, matched)
            for name in visible:
                with self.subTest(visible=name):
                    self.assertNotIn(name, matched)


if __name__ == '__main__':
    unittest.main()
