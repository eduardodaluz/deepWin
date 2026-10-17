import copy
import errno
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location('config_backend',
    Path(__file__).resolve().parents[1] / 'gui/backend.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class FakeNative:
    def __init__(self):
        self.shortcuts = {action: [key, 123] for action, key in backend.SHORTCUTS.values()}
        self.services = {name: {'active': True, 'enabled': 'enabled', 'dry_run': False}
                         for name in backend.SERVICES.values()}
        self.screenshot_value = {'active': [backend.SCREENSHOT_KEY, '<Alt>A'],
                                 'saved': [backend.SCREENSHOT_KEY, '<Control>A']}
        self.commands = []
        self.fail_key = None

    def service(self, name):
        if name not in self.services:
            raise backend.ConfigError('Serviço ausente')
        return copy.deepcopy(self.services[name])

    def set_service(self, name, active, enabled):
        self.services[name].update(active=active, enabled=enabled)

    def shortcut(self, action):
        return list(self.shortcuts[action])

    def set_shortcut(self, action, keys):
        if self.fail_key in keys:
            raise backend.ConfigError('Conflito de atalho')
        self.shortcuts[action] = list(keys)

    def screenshot(self):
        return copy.deepcopy(self.screenshot_value)

    def set_screenshot(self, value):
        self.screenshot_value = copy.deepcopy(value)

    def call(self, command):
        self.commands.append(command)

    def native_slideshow(self):
        return True


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / 'state'
        self.source = self.home / 'resource-zclaude'
        self.source.write_text('#!/bin/bash\nexec claude "$@"\n')
        self.native = FakeNative()
        self.manager = self.new_manager()

    def new_manager(self):
        return backend.Manager(native=self.native, home=self.home,
                               state_dir=self.state, source=self.source)

    def test_status_reports_real_resources_without_writing_files(self):
        result = self.manager.status()
        self.assertEqual(len(result['features']), 9)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.manager.feature_status('zclaude')['enabled'])

    def test_dock_preview_is_backed_up_and_restored_independently(self):
        class FakeDock:
            enabled = False
            def capture(self): return {'enabled': self.enabled}
            def status(self): return {'enabled': self.enabled, 'available': True}
            def configure(self, enabled): self.enabled = enabled
        self.manager.dock_preview = FakeDock()
        self.manager.change('dock_preview', True)
        self.assertTrue(self.manager.feature_status('dock_preview')['enabled'])
        self.assertEqual(self.manager.load_state()['dock_preview'], {'enabled': False})
        self.manager.restore('dock_preview')
        self.assertFalse(self.manager.feature_status('dock_preview')['enabled'])
        self.assertEqual(self.manager.load_state(), {})

    def test_failed_dock_activation_restores_prior_state_and_clears_new_backup(self):
        class FakeDock:
            def capture(self): return {'enabled': False}
            def configure(self, enabled):
                if enabled: raise backend.ConfigError('Falha ao recarregar')
        self.manager.dock_preview = FakeDock()
        with self.assertRaises(backend.ConfigError):
            self.manager.change('dock_preview', True)
        self.assertEqual(self.manager.load_state(), {})

    def test_shortcut_disable_preserves_other_combinations(self):
        self.manager.change('desktop_next', False)
        action = backend.SHORTCUTS['desktop_next'][0]
        self.assertEqual(self.native.shortcut(action), [123])

    def test_enable_shortcut_keeps_alternatives(self):
        action, key = backend.SHORTCUTS['desktop_next']
        self.native.shortcuts[action] = [123]
        self.manager.change('desktop_next', True)
        self.assertEqual(self.native.shortcut(action), [123, key])

    def test_backup_survives_restart_and_restores_exact_order(self):
        original = self.manager.capture('desktop_next')
        self.manager.change('desktop_next', False)
        self.new_manager().restore('desktop_next')
        self.assertEqual(self.manager.capture('desktop_next'), original)
        self.assertEqual(self.manager.load_state(), {})

    def test_service_restore_keeps_session_only_and_runtime_enablement(self):
        name = backend.SERVICES['clipboard']
        self.native.services[name].update(active=False, enabled='enabled-runtime')
        original = self.manager.capture('clipboard')
        self.manager.change('clipboard', True)
        self.manager.restore('clipboard')
        self.assertEqual(self.manager.capture('clipboard'), original)

    def test_clipboard_does_not_stop_wallpaper_or_native_history(self):
        previous = self.manager.capture('wallpaper')
        self.manager.change('clipboard', False)
        self.assertEqual(self.manager.capture('wallpaper'), previous)
        self.assertEqual(self.native.commands, [])

    def test_wallpaper_disable_also_stops_its_pending_download(self):
        self.manager.change('wallpaper', False)
        self.assertEqual(self.native.commands,
                         [['systemctl', '--user', 'stop', 'deepin-wallpaper.service']])

    def test_wallpaper_note_distinguishes_native_slideshow(self):
        self.assertIn('independente', self.manager.feature_status('wallpaper')['note'])

    def test_screenshot_preserves_separate_active_and_saved_alternatives(self):
        original = self.manager.capture('screenshot')
        self.manager.change('screenshot', False)
        self.assertEqual(self.native.screenshot(), {'active': ['<Alt>A'], 'saved': ['<Control>A']})
        self.manager.restore('screenshot')
        self.assertEqual(self.native.screenshot(), original)

    def test_failed_enable_preserves_previous_shortcut_and_clears_new_backup(self):
        action, key = backend.SHORTCUTS['desktop_next']
        self.native.shortcuts[action] = [123]
        self.native.fail_key = key
        with self.assertRaises(backend.ConfigError):
            self.manager.change('desktop_next', True)
        self.assertEqual(self.native.shortcut(action), [123])
        self.assertEqual(self.manager.load_state(), {})

    def test_original_backup_is_not_replaced_by_later_changes(self):
        original = self.manager.capture('clipboard')
        self.manager.change('clipboard', False)
        self.manager.change('clipboard', False)
        self.assertEqual(self.manager.load_state()['clipboard'], original)

    def test_return_to_original_state_clears_restore_entry(self):
        self.manager.change('clipboard', False)
        self.manager.change('clipboard', True)
        self.assertEqual(self.manager.load_state(), {})

    def test_wrapper_disable_enable_preserves_custom_bytes_and_permissions(self):
        self.manager.wrapper.parent.mkdir(parents=True)
        self.manager.wrapper.write_bytes(b'#!/bin/bash\n# meu wrapper\n')
        self.manager.wrapper.chmod(0o751)
        original = self.manager.capture('zclaude')
        self.manager.change('zclaude', False)
        self.assertFalse(self.manager.wrapper.exists())
        self.assertTrue(self.manager.disabled.exists())
        self.manager.change('zclaude', True)
        self.assertEqual(self.manager.capture('zclaude'), original)

    def test_wrapper_symlink_is_preserved(self):
        self.source.chmod(0o755)
        self.manager.wrapper.parent.mkdir(parents=True)
        self.manager.wrapper.symlink_to(self.source)
        self.manager.change('zclaude', False)
        self.manager.restore('zclaude')
        self.assertTrue(self.manager.wrapper.is_symlink())
        self.assertEqual(self.manager.wrapper.resolve(), self.source)

    def test_wrapper_can_be_disabled_when_state_is_on_another_filesystem(self):
        self.manager.wrapper.parent.mkdir(parents=True)
        self.manager.wrapper.write_bytes(b'#!/bin/bash\n# custom\n')
        self.manager.wrapper.chmod(0o751)
        original = self.manager.capture('zclaude')
        replace = os.replace

        def cross_device(source, destination):
            if source == self.manager.wrapper and destination == self.manager.disabled:
                raise OSError(errno.EXDEV, 'cross-device')
            return replace(source, destination)

        with patch.object(backend.os, 'replace', side_effect=cross_device):
            self.manager.change('zclaude', False)
        self.assertFalse(self.manager.wrapper.exists())
        self.manager.change('zclaude', True)
        self.assertEqual(self.manager.capture('zclaude'), original)

    def test_wrapper_restore_originally_missing_removes_only_wrapper(self):
        key = self.home / '.config/zai/api_key'
        key.parent.mkdir(parents=True)
        key.write_text('secret-for-test-only')
        self.manager.change('zclaude', True)
        self.manager.restore('zclaude')
        self.assertFalse(self.manager.wrapper.exists())
        self.assertEqual(key.read_text(), 'secret-for-test-only')
        self.assertNotIn('secret-for-test-only', json.dumps(self.manager.status()))
        self.assertNotIn('secret-for-test-only', self.manager.state_file.read_text())

    def test_non_executable_existing_wrapper_is_not_overwritten(self):
        self.manager.wrapper.parent.mkdir(parents=True)
        self.manager.wrapper.write_text('custom file')
        self.manager.wrapper.chmod(0o600)
        with self.assertRaises(backend.ConfigError):
            self.manager.change('zclaude', True)
        self.assertEqual(self.manager.wrapper.read_text(), 'custom file')

    def test_missing_service_is_unavailable_instead_of_reported_disabled(self):
        del self.native.services[backend.SERVICES['clipboard']]
        result = self.manager.feature_status('clipboard')
        self.assertFalse(result['available'])
        self.assertEqual(result['status'], 'Indisponível')

    def test_original_files_are_private(self):
        self.manager.change('clipboard', False)
        self.assertEqual(stat.S_IMODE(self.manager.state_file.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o700)

    def test_unknown_backup_format_is_preserved_and_rejected(self):
        self.state.mkdir()
        value = '{"unknown_feature": {"active": true}}'
        self.manager.state_file.write_text(value)
        with self.assertRaises(backend.ConfigError):
            self.manager.restore()
        self.assertEqual(self.manager.state_file.read_text(), value)

    def test_restore_all_preserves_unrelated_keys(self):
        other = self.manager.capture('screen_previous')
        self.manager.change('clipboard', False)
        self.manager.change('desktop_next', False)
        self.manager.restore()
        self.assertTrue(self.manager.feature_status('clipboard')['enabled'])
        self.assertTrue(self.manager.feature_status('desktop_next')['enabled'])
        self.assertEqual(self.manager.capture('screen_previous'), other)
        self.assertEqual(self.manager.load_state(), {})

    def test_partial_restore_failure_keeps_the_failed_backup(self):
        self.manager.change('clipboard', False)
        self.manager.change('desktop_next', False)
        self.native.fail_key = backend.SHORTCUTS['desktop_next'][1]
        with self.assertRaises(backend.ConfigError):
            self.manager.restore()
        self.assertTrue(self.manager.feature_status('clipboard')['enabled'])
        self.assertEqual(list(self.manager.load_state()), ['desktop_next'])

    def test_unknown_feature_is_rejected_before_state_is_created(self):
        with self.assertRaises(backend.ConfigError):
            self.manager.change('unknown', True)
        self.assertFalse(self.state.exists())


class NativeShortcutTests(unittest.TestCase):
    def test_disabled_display_label_is_not_treated_as_hotkey_in_any_language(self):
        api = Mock()
        api.LookupConflictShortcut.return_value = ['']
        for label in ('None', 'Nenhum', 'Aucun', '无', '任意の翻訳'):
            api.GetShortcut.return_value = [backend.SCREENSHOT_ID, '', '', [label]]
            self.assertEqual(backend.screenshot_keys(api), [])

    def test_actual_registered_accelerator_is_preserved(self):
        api = Mock()
        api.GetShortcut.return_value = [backend.SCREENSHOT_ID, '', '', [backend.SCREENSHOT_KEY]]
        api.LookupConflictShortcut.return_value = [backend.SCREENSHOT_ID]
        self.assertEqual(backend.screenshot_keys(api), [backend.SCREENSHOT_KEY])


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.legacy = self.home / 'deepin-configs'
        self.target = self.home / backend.APP_ID

    def test_state_migration_preserves_backups_permissions_and_disabled_wrapper(self):
        self.legacy.mkdir(mode=0o700)
        originals = self.legacy / 'originals.json'
        originals.write_text('{"clipboard": {"active": true, "enabled": "enabled"}}')
        originals.chmod(0o600)
        (self.legacy / 'disabled').mkdir()
        (self.legacy / 'disabled/zclaude').symlink_to('/tmp/only-a-test-path')
        expected = originals.read_bytes()
        self.assertTrue(backend.migrate_legacy_state(self.home))
        self.assertFalse(self.legacy.exists())
        self.assertEqual((self.target / 'originals.json').read_bytes(), expected)
        self.assertEqual(stat.S_IMODE((self.target / 'originals.json').stat().st_mode), 0o600)
        self.assertEqual(os.readlink(self.target / 'disabled/zclaude'), '/tmp/only-a-test-path')

    def test_migration_can_be_run_again_without_changes(self):
        self.legacy.mkdir()
        self.assertTrue(backend.migrate_legacy_state(self.home))
        self.assertFalse(backend.migrate_legacy_state(self.home))

    def test_existing_new_state_is_never_overwritten(self):
        self.legacy.mkdir()
        self.target.mkdir()
        (self.legacy / 'originals.json').write_text('old backup')
        (self.target / 'originals.json').write_text('new backup')
        with self.assertRaises(backend.ConfigError):
            backend.migrate_legacy_state(self.home)
        self.assertEqual((self.legacy / 'originals.json').read_text(), 'old backup')
        self.assertEqual((self.target / 'originals.json').read_text(), 'new backup')

    def test_default_manager_uses_new_app_identifier_and_xdg_state_home(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': str(self.home)}):
            manager = backend.Manager(native=FakeNative(), home=self.home)
            self.assertEqual(manager.state_dir, self.target)


if __name__ == '__main__':
    unittest.main()
