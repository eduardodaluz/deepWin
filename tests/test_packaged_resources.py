import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gui'))
from resources import Resources, ResourceError
from user_services import UserServices
import backend


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.source = self.home / 'source'
        self.source.mkdir()
        (self.source / 'VERSION').write_text('1.1.0\n')
        (self.source / 'sample.py').write_text('print("sample")\n')
        (self.source / 'resources.json').write_text(json.dumps({'format': 1,
            'files': ['VERSION', 'resources.json', 'sample.py']}))
        self.resources = Resources(home=self.home, root=self.source, data_home=self.home / 'data')

    def test_query_does_not_create_runtime_and_missing_files_fail_before_write(self):
        self.assertTrue(self.resources.available())
        self.assertFalse(self.resources.runtime.exists())
        (self.source / 'sample.py').unlink()
        with self.assertRaises(ResourceError):
            self.resources.ensure()
        self.assertFalse(self.resources.runtime.exists())

    def test_runtime_survives_removing_source_and_is_idempotent(self):
        current = self.resources.ensure()
        original = current.resolve()
        self.assertEqual(self.resources.ensure().resolve(), original)
        shutil.rmtree(self.source)
        self.assertEqual((current / 'sample.py').read_text(), 'print("sample")\n')
        self.resources.validate_release(original)

    def test_update_switches_atomically_and_retains_old_release(self):
        old = self.resources.ensure().resolve()
        (self.source / 'sample.py').write_text('print("updated")\n')
        new = self.resources.ensure().resolve()
        self.assertNotEqual(old, new)
        self.assertIn('updated', (new / 'sample.py').read_text())
        self.assertIn('sample', (old / 'sample.py').read_text())

    def test_custom_runtime_is_not_overwritten_or_replaced(self):
        current = self.resources.ensure()
        release = current.resolve()
        (current / 'sample.py').write_text('customization')
        (self.source / 'sample.py').write_text('update')
        with self.assertRaises(ResourceError):
            self.resources.ensure()
        self.assertEqual(current.resolve(), release)
        self.assertEqual((current / 'sample.py').read_text(), 'customization')

    def test_symlink_escape_in_manifest_is_rejected(self):
        (self.source / 'sample.py').unlink()
        (self.source / 'sample.py').symlink_to('/etc/passwd')
        with self.assertRaises(ResourceError):
            self.resources.ensure()
        self.assertFalse(self.resources.runtime.exists())

    def test_generated_bytecode_does_not_count_as_a_customization(self):
        current = self.resources.ensure()
        cache = current/'__pycache__'
        cache.mkdir()
        (cache/'sample.cpython-312.pyc').write_bytes(b'generated cache')
        self.assertEqual(self.resources.ensure(), current)

    def test_unknown_runtime_owner_is_preserved(self):
        current = self.resources.ensure()
        (current / 'runtime.json').write_text('{"owner":"custom"}')
        with self.assertRaises(ResourceError):
            self.resources.ensure()
        self.assertTrue((current / 'sample.py').exists())

    def test_full_runtime_imports_backend_after_source_is_removed(self):
        source = Resources(root=ROOT)
        try:
            files = source.files()
        except ResourceError:
            self.skipTest('Compile o plugin Qt antes de testar a cópia completa.')
        for name, path in files.items():
            destination = self.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        runtime = self.resources.ensure()
        shutil.rmtree(self.source)
        result = subprocess.run(['/usr/bin/python3', str(runtime / 'gui/backend.py'), '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('restore', result.stdout)
        self.assertTrue(os.access(runtime / 'bin/deepwin-restore', os.X_OK))
        self.resources.validate_release(runtime.resolve())


class ServiceNative:
    def __init__(self, units):
        self.units = units
        self.services = {}
        self.commands = []
        self.fail_start = False

    def call(self, command, check=True):
        self.commands.append(command)
        if command[-1] == 'daemon-reload':
            for name in backend.SERVICES.values():
                if (self.units / name).exists():
                    self.services.setdefault(name, {'active': False, 'enabled': 'disabled', 'dry_run': False})
                else:
                    self.services.pop(name, None)
        return ''

    def requirements(self, feature):
        pass

    def service(self, name):
        if name not in self.services:
            raise backend.ServiceMissing('Ausente')
        return copy.deepcopy(self.services[name])

    def set_service(self, name, active, enabled):
        if active and self.fail_start:
            raise backend.ConfigError('Falha de teste no início')
        self.services[name].update(active=active, enabled=enabled)

    def native_slideshow(self):
        return False


class FreshInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.units = self.home / 'config/systemd/user'
        self.environ = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home/'config'),
                                  'XDG_DATA_HOME': str(self.home/'data')})
        self.environ.start()
        self.addCleanup(self.environ.stop)
        self.resources = Resources(home=self.home, root=ROOT)
        try:
            self.resources.available()
        except ResourceError:
            self.skipTest('Compile o plugin antes dos testes de instalação.')
        self.native = ServiceNative(self.units)
        self.manager = backend.Manager(home=self.home, native=self.native,
                                       state_dir=self.home/'state', resources=self.resources)

    def test_new_installation_reports_preparable_resource_without_writing(self):
        item = self.manager.feature_status('clipboard')
        self.assertTrue(item['available'])
        self.assertFalse(item['enabled'])
        self.assertEqual(item['status'], 'Pronto para ativar')
        self.assertFalse(self.resources.data.exists())
        self.assertFalse(self.units.exists())

    def test_first_activation_and_manual_disable_restore_original_absence(self):
        self.manager.change('clipboard', True)
        unit = self.units / 'deepin-clipboard-autopaste.service'
        self.assertIn('runtime/current/bin/deepin-clipboard-autopaste', unit.read_text())
        self.assertNotIn('--dry-run', unit.read_text())
        self.assertTrue(self.manager.load_state()['clipboard']['absent'])
        self.manager.change('clipboard', False)
        self.assertFalse(unit.exists())
        self.assertEqual(self.manager.load_state(), {})

    def test_wallpaper_timer_is_hourly_and_restore_removes_only_created_units(self):
        self.manager.change('wallpaper', True)
        self.assertIn('OnUnitActiveSec=1h', (self.units/'deepin-wallpaper.timer').read_text())
        self.assertIn('runtime/current/bin/refresh-deepin-wallpaper',
                      (self.units/'deepin-wallpaper.service').read_text())
        self.manager.restore('wallpaper')
        self.assertFalse((self.units/'deepin-wallpaper.timer').exists())
        self.assertFalse((self.units/'deepin-wallpaper.service').exists())
        self.assertTrue(self.resources.current.exists())
        self.assertEqual(self.manager.load_state(), {})

    def test_failed_start_rolls_back_new_files_and_clears_backup(self):
        self.native.fail_start = True
        with self.assertRaises(backend.ConfigError):
            self.manager.change('clipboard', True)
        self.assertFalse((self.units/'deepin-clipboard-autopaste.service').exists())
        self.assertEqual(self.manager.load_state(), {})

    def test_customized_unit_after_activation_is_preserved_on_restore(self):
        self.manager.change('clipboard', True)
        unit = self.units/'deepin-clipboard-autopaste.service'
        unit.write_text('customization')
        with self.assertRaises(backend.ConfigError):
            self.manager.restore('clipboard')
        self.assertEqual(unit.read_text(), 'customization')
        self.assertIn('clipboard', self.manager.load_state())

    def test_removed_marker_with_custom_unit_is_not_overwritten_on_restore(self):
        # Backup com arquivos: a unidade gerenciada já existia na primeira mudança.
        self.manager.user_services.prepare('clipboard')
        self.native.call(['systemctl', '--user', 'daemon-reload'])
        self.native.services['deepin-clipboard-autopaste.service'] = {
            'active': True, 'enabled': 'enabled', 'dry_run': False}
        self.manager.change('clipboard', False)
        value = self.manager.load_state()['clipboard']
        self.assertIn('files', value)
        # O usuário assumiu a unidade e removeu o registro do painel.
        (self.resources.data/'service-clipboard.json').unlink()
        unit = self.units/'deepin-clipboard-autopaste.service'
        unit.write_text('customization')
        with self.assertRaises(backend.ConfigError):
            self.manager.restore('clipboard')
        self.assertEqual(unit.read_text(), 'customization')
        self.assertIn('clipboard', self.manager.load_state())

    def test_existing_unit_is_preserved_when_enabling(self):
        self.units.mkdir(parents=True)
        unit = self.units/'deepin-clipboard-autopaste.service'
        unit.write_text('custom existing unit')
        self.native.call(['systemctl','--user','daemon-reload'])
        self.manager.change('clipboard', True)
        self.manager.restore('clipboard')
        self.assertEqual(unit.read_text(), 'custom existing unit')
        self.assertFalse(self.native.service('deepin-clipboard-autopaste.service')['active'])

    def test_unknown_state_schema_is_rejected_without_overwriting_backup(self):
        self.manager.state_dir.mkdir()
        self.manager.state_file.write_text('{}')
        (self.manager.state_dir/'schema.json').write_text('{"format":999}')
        with self.assertRaises(backend.ConfigError):
            self.manager.change('clipboard', True)
        self.assertEqual(self.manager.state_file.read_text(), '{}')
        self.assertEqual((self.manager.state_dir/'schema.json').read_text(), '{"format":999}')

    def test_new_manager_resolves_runtime_helper_for_dropin_check(self):
        runtime = self.resources.ensure()
        fresh = backend.Manager(home=self.home, native=self.native,
                                state_dir=self.home/'state', resources=self.resources)
        self.assertTrue(str(fresh.dock_preview.helper).endswith('runtime/current/gui/dock_preview.py'))
        dropin = fresh.dock_preview.dropin
        dropin.parent.mkdir(parents=True, exist_ok=True)
        dropin.write_text(fresh.dock_preview.dropin_text())
        fresh.dock_preview.check_dropin()


class LegacyKeybindingAPI:
    """Proxy da geração antiga do serviço de atalhos: GetShortcut exige (id, tipo)."""

    def __init__(self, lag=0):
        self.accels = ['<Control><Alt>A']
        self.lag = lag
        self.pending = None

    def _apply_pending(self):
        if self.pending is not None:
            if self.lag > 0:
                self.lag -= 1
            else:
                self.accels = self.pending
                self.pending = None

    def GetShortcut(self, identifier, *args, timeout=None):
        if len(args) != 1:
            raise TypeError('More items found in D-Bus signature than in Python arguments')
        self._apply_pending()
        return json.dumps({'Id': identifier, 'Type': 0, 'Accels': list(self.accels),
                           'Name': 'Captura de Tela'})

    def LookupConflictingShortcut(self, key, timeout=None):
        if key in self.accels:
            return json.dumps({'Id': 'screenshot', 'Type': 0, 'Accels': [key],
                               'Name': 'Captura de Tela'})
        return ''

    def ModifiedAccel(self, identifier, kind, key, add, timeout=None):
        base = self.pending if self.pending is not None else self.accels
        accels = list(base)
        if add:
            if key not in accels:
                accels.append(key)
        else:
            accels = [item for item in accels if item != key]
        self.pending = accels
        return (False, '')

    def Disable(self, identifier, kind, timeout=None):
        self.pending = []


class FakeSchemaSource:
    def lookup(self, schema, recursive=False):
        return object()


class FakeSettings:
    def __init__(self):
        self.values = {}

    def get_strv(self, key):
        return list(self.values.get(key, []))

    def set_strv(self, key, value):
        self.values[key] = list(value)
        return True

    @staticmethod
    def sync():
        pass


class LegacyScreenshotTests(unittest.TestCase):
    def setUp(self):
        import gi  # noqa: F401 — garante que a falha seja clara se python3-gi faltar
        self.api = LegacyKeybindingAPI(lag=2)
        self.native = object.__new__(backend.Native)
        keybindings = patch.object(backend.Native, 'keybindings', return_value=self.api)
        keybindings.start()
        self.addCleanup(keybindings.stop)
        source = patch('gi.repository.Gio.SettingsSchemaSource.get_default',
                       return_value=FakeSchemaSource())
        settings = patch('gi.repository.Gio.Settings.new', return_value=FakeSettings())
        source.start()
        settings.start()
        self.addCleanup(source.stop)
        self.addCleanup(settings.stop)

    def test_set_screenshot_tolerates_async_application(self):
        value = {'active': ['<Shift><Super>S'], 'saved': ['<Control><Alt>A', '<Shift><Super>S']}
        self.native.set_screenshot(value)
        self.assertEqual(self.native.screenshot(), value)


class OptionalNativeTests(unittest.TestCase):
    def test_missing_settings_schema_is_a_python_error_instead_of_process_abort(self):
        from gi.repository import Gio
        with patch.object(Gio.SettingsSchemaSource, 'get_default', return_value=None):
            native = object.__new__(backend.Native)
            with self.assertRaises(backend.ConfigError):
                native.screenshot()
