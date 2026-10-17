import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gui'))
import claude_versions as versions


class ClaudeVersionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.manager = versions.ClaudeVersions(home=self.home, state_dir=self.home / 'state',
            data_dir=self.home / 'data', cache_dir=self.home / 'cache')
        self.catalog = {'versions': ['2.1.302', '2.1.292', '2.1.263'],
                        'stable': '2.1.292', 'fetched_at': time.time()}

    def executable(self, version):
        binary = self.manager.binary(version)
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text('#!/bin/sh\nprintf "%s\\n" "' + version + ' (Claude Code)"\n')
        binary.chmod(0o755)
        return binary

    def choose(self, value):
        with patch.object(self.manager, 'catalog', return_value=self.catalog):
            self.manager.choose(value)

    def test_status_does_not_write_or_download_and_preserves_legacy(self):
        legacy = self.home / '.local/share/claude-glm/bin/claude'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('#!/bin/sh\nexit 0\n')
        legacy.chmod(0o755)
        self.assertEqual(self.manager.resolve(background=False), (str(legacy), False))
        self.assertEqual(self.manager.status()['mode'], 'legacy')
        self.assertFalse(self.manager.state_dir.exists())

    def test_pinned_version_is_isolated_and_restore_returns_to_legacy(self):
        self.executable('2.1.302')
        self.choose('2.1.302')
        self.assertEqual(self.manager.status()['mode'], 'pinned')
        self.assertEqual(self.manager.status()['version'], '2.1.302')
        self.assertTrue(self.manager.status()['can_restore'])
        self.assertEqual(self.manager.selection_file.stat().st_mode & 0o777, 0o600)
        self.manager.restore()
        self.assertIsNone(self.manager.selection())
        self.assertFalse(self.manager.status()['can_restore'])
        self.assertTrue(self.manager.binary('2.1.302').exists())

    def test_undo_returns_to_immediately_previous_selection(self):
        self.executable('2.1.302')
        self.executable('2.1.263')
        self.choose('2.1.302')
        self.choose('2.1.263')
        self.manager.restore()
        self.assertEqual(self.manager.selection()['version'], '2.1.302')
        self.assertFalse(self.manager.status()['can_restore'])

    def test_install_failure_preserves_pointer_and_previous_backup(self):
        self.executable('2.1.263')
        self.choose('2.1.263')
        before = self.manager.selection_file.read_bytes()
        with patch.object(self.manager, 'catalog', return_value=self.catalog), patch.object(
                self.manager, 'install', side_effect=versions.VersionError('Download falhou')):
            with self.assertRaises(versions.VersionError):
                self.manager.choose('2.1.302')
        self.assertEqual(self.manager.selection_file.read_bytes(), before)

    def test_failed_verification_never_selects_the_download(self):
        with patch.object(self.manager, 'catalog', return_value=self.catalog), patch.object(
                self.manager, 'install', side_effect=versions.VersionError('Versão incorreta')):
            with self.assertRaises(versions.VersionError):
                self.manager.choose('2.1.302')
        self.assertIsNone(self.manager.selection())

    def test_invalid_versions_and_shell_arguments_are_rejected_before_network(self):
        for value in ('../2.1.302', 'latest', '2.1.302;exit', '--prefix=/tmp', '2.1.302-beta'):
            with self.subTest(value=value), patch.object(self.manager, 'catalog') as catalog:
                with self.assertRaises(versions.VersionError):
                    self.manager.choose(value)
                catalog.assert_not_called()

    def test_unpublished_version_is_not_installed(self):
        with patch.object(self.manager, 'catalog', return_value=self.catalog), patch.object(self.manager, 'install') as install:
            with self.assertRaises(versions.VersionError):
                self.manager.choose('9.9.999')
            install.assert_not_called()

    def test_stable_uses_real_stable_tag_even_if_latest_is_newer(self):
        self.executable('2.1.292')
        self.choose('stable')
        self.assertEqual(self.manager.selection()['mode'], 'stable')
        self.assertEqual(self.manager.selection()['version'], '2.1.292')

    def test_stable_refresh_is_atomic_and_keeps_existing_sessions_and_rollback(self):
        old = self.executable('2.1.292')
        new = self.executable('2.1.302')
        self.choose('stable')
        value = self.manager.selection()
        value['checked_at'] = 0
        versions.write_json(self.manager.selection_file, value)
        with patch.object(self.manager, 'catalog', return_value=dict(self.catalog, stable='2.1.302')):
            self.manager.refresh_stable()
        self.assertEqual(self.manager.resolve(background=False), (str(new), True))
        self.assertTrue(old.exists())
        self.assertIn('previous', self.manager.selection())
        self.manager.restore()
        self.assertIsNone(self.manager.selection())

    def test_failed_stable_refresh_keeps_working_version_and_retries_next_day(self):
        self.executable('2.1.292')
        self.choose('stable')
        value = self.manager.selection()
        value['checked_at'] = 0
        versions.write_json(self.manager.selection_file, value)
        with patch.object(self.manager, 'catalog', side_effect=versions.VersionError('Sem rede')) as catalog:
            self.manager.refresh_stable()
            self.manager.refresh_stable()
            self.assertEqual(catalog.call_count, 1)
        self.assertEqual(self.manager.selection()['version'], '2.1.292')
        self.assertEqual(self.manager.status()['update_error'], 'Sem rede')

    def test_pinned_mode_never_launches_a_background_update(self):
        self.executable('2.1.302')
        self.choose('2.1.302')
        with patch('claude_versions.subprocess.Popen') as launch:
            self.manager.resolve()
            launch.assert_not_called()

    def test_due_stable_update_is_background_and_does_not_block_startup(self):
        self.executable('2.1.292')
        self.choose('stable')
        value = self.manager.selection()
        value['checked_at'] = 0
        versions.write_json(self.manager.selection_file, value)
        with patch('claude_versions.subprocess.Popen') as launch:
            binary, managed = self.manager.resolve()
        self.assertEqual(binary, str(self.manager.binary('2.1.292')))
        self.assertTrue(managed)
        self.assertEqual(launch.call_args.args[0][-1], 'refresh-stable')
        self.assertTrue(launch.call_args.kwargs['start_new_session'])

    def test_catalog_sorts_versions_numerically_and_omits_prereleases(self):
        data = {'dist-tags': {'stable': '2.1.9'},
                'versions': {'2.1.9': {}, '2.1.10': {}, '2.1.11-beta': {}}}
        response = Mock()
        response.read.return_value = json.dumps(data).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch('claude_versions.urllib.request.urlopen', return_value=response):
            catalog = self.manager.catalog(refresh=True)
        self.assertEqual(catalog['versions'], ['2.1.10', '2.1.9'])
        with patch('claude_versions.urllib.request.urlopen') as fetch:
            self.manager.catalog()
            fetch.assert_not_called()

    def test_credentials_are_not_inherited_by_npm_or_background_updater(self):
        with patch.dict(os.environ, {'ZAI_API_KEY': 'unit-test-key',
                                    'ANTHROPIC_AUTH_TOKEN': 'unit-test-token',
                                    'GITHUB_TOKEN': 'unit-test-github'}):
            env = versions.clean_env()
        self.assertNotIn('ZAI_API_KEY', env)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', env)
        self.assertNotIn('GITHUB_TOKEN', env)

    def test_settings_and_api_key_files_are_untouched(self):
        settings = self.home / '.claude-glm/settings.json'
        key = self.home / '.config/zai/api_key'
        settings.parent.mkdir(parents=True)
        key.parent.mkdir(parents=True)
        settings.write_bytes(b'{"env":{"DISABLE_AUTOUPDATER":"1","custom":"keep"}}')
        key.write_bytes(b'unit-test-only')
        self.executable('2.1.302')
        self.choose('2.1.302')
        self.manager.restore()
        self.assertEqual(settings.read_bytes(), b'{"env":{"DISABLE_AUTOUPDATER":"1","custom":"keep"}}')
        self.assertEqual(key.read_bytes(), b'unit-test-only')

    def test_system_selection_bypasses_the_legacy_installation(self):
        with patch('claude_versions.shutil.which', return_value='/usr/bin/claude'):
            self.manager.choose('system')
        self.assertEqual(self.manager.resolve(background=False), ('claude', False))
        self.manager.restore()
        self.assertIsNone(self.manager.selection())

    def test_corrupt_selection_is_rejected_instead_of_running_another_version(self):
        versions.write_json(self.manager.selection_file, {'mode': 'pinned', 'version': '../other'})
        with self.assertRaises(versions.VersionError):
            self.manager.resolve(background=False)

    def test_refresh_does_not_race_with_another_version_change(self):
        with self.manager.lock(), patch.object(self.manager, 'catalog') as catalog:
            self.manager.refresh_stable()
            catalog.assert_not_called()

    def test_failed_npm_install_cleans_staging_and_does_not_activate_it(self):
        with patch('claude_versions.shutil.which', return_value='/usr/bin/npm'), patch(
                'claude_versions.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['npm'])):
            with self.assertRaises(versions.VersionError):
                self.manager.install('2.1.302')
        self.assertFalse(self.manager.binary('2.1.302').exists())
        self.assertFalse(list((self.manager.data_dir / 'versions').glob('.install-*')))
        self.assertIsNone(self.manager.selection())

    def test_undo_keeps_current_selection_if_previous_executable_was_removed(self):
        old = self.executable('2.1.263')
        self.executable('2.1.302')
        self.choose('2.1.263')
        self.choose('2.1.302')
        old.unlink()
        with self.assertRaises(versions.VersionError):
            self.manager.restore()
        self.assertEqual(self.manager.selection()['version'], '2.1.302')
        self.assertTrue(self.manager.status()['can_restore'])

    def test_invalid_environment_override_is_explicitly_rejected(self):
        with patch.dict(os.environ, {'ZCLAUDE_CLAUDE_BIN': str(self.home / 'missing')}):
            with self.assertRaises(versions.VersionError):
                self.manager.resolve(background=False)
            self.assertTrue(self.manager.status()['override'])

    def test_wrapper_passes_arguments_and_uses_selected_version_with_zai(self):
        env = dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.home / 'state-home'),
                   XDG_DATA_HOME=str(self.home / 'data-home'), XDG_CACHE_HOME=str(self.home / 'cache-home'),
                   ZAI_API_KEY='unit-test-key')
        env.pop('ZCLAUDE_CLAUDE_BIN', None)
        env.pop('CLAUDE_CONFIG_DIR', None)
        with patch.dict(os.environ, env, clear=True):
            manager = versions.ClaudeVersions()
            binary = manager.binary('2.1.302')
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/usr/bin/python3\nimport os,sys,json\nprint(json.dumps({"args":sys.argv[1:],"config":os.environ.get("CLAUDE_CONFIG_DIR"),"token":os.environ.get("ANTHROPIC_AUTH_TOKEN"),"updates":os.environ.get("DISABLE_AUTOUPDATER"),"url":os.environ.get("ANTHROPIC_BASE_URL")}))\n')
            binary.chmod(0o755)
            versions.write_json(manager.selection_file, {'mode': 'pinned', 'version': '2.1.302'})
            result = subprocess.run([str(ROOT / 'bin/zclaude'), '-p', 'texto com espaços'],
                                    env=env, capture_output=True, text=True, check=True)
        value = json.loads(result.stdout)
        self.assertEqual(value['args'], ['-p', 'texto com espaços'])
        self.assertEqual(value['config'], str(self.home / '.claude-glm'))
        self.assertEqual(value['token'], 'unit-test-key')
        self.assertEqual(value['updates'], '1')
        self.assertEqual(value['url'], 'https://api.z.ai/api/anthropic')


if __name__ == '__main__':
    unittest.main()
