#!/usr/bin/python3
"""Controlador local do DeepWin. JSON na saída; nenhuma chave de API é lida."""

import argparse
import base64
from contextlib import contextmanager
import errno
import fcntl
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import time
import sys
import tempfile

# Raiz do hospedeiro exposta em leitura dentro de um container Linyaps.
HOST_ROOT = '/run/host/rootfs'


def bootstrap_runtime_python(root=None):
    """Carregar dbus/gi extraídos para o runtime por usuário (pacote Linyaps).

    O .deb instala python3-dbus/python3-gi por Depends e este bootstrap não
    faz nada. No pacote Linyaps as cópias beige ficam em pydeps/ junto ao
    código distribuído; a biblioteca nativa é pré-carregada em escopo global
    para que o _gi.so resolva o soname sem LD_LIBRARY_PATH.
    """
    if Path(HOST_ROOT).is_dir():
        # Os helpers executam no host; os schemas do dsettings, os launchers
        # e os catálogos da sessão ficam na raiz do hospedeiro exposta em
        # leitura, não no rootfs do aplicativo.
        host = Path(HOST_ROOT)
        shares = [str(host / 'usr/share'),
                  str(host / 'var/lib/linglong/entries/apps/share'),
                  str(host / 'var/lib/linglong/entries/share')]
        os.environ['XDG_DATA_DIRS'] = ':'.join(shares) + ':' + \
            os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
    base = Path(root or Path(__file__).resolve().parents[1]) / 'pydeps'
    if not base.is_dir():
        return
    packages = base / 'dist-packages'
    if packages.is_dir():
        sys.path.insert(0, str(packages))
    lib = base / 'lib'
    if lib.is_dir():
        import ctypes
        for soname in sorted(lib.glob('lib*.so.*')):
            if soname.is_symlink():
                continue
            try:
                ctypes.CDLL(str(soname), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass
    typelib = base / 'girepository-1.0'
    if typelib.is_dir():
        current = os.environ.get('GI_TYPELIB_PATH')
        paths = [str(typelib)] + ([current] if current else [])
        os.environ['GI_TYPELIB_PATH'] = os.pathsep.join(paths)


bootstrap_runtime_python()
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_versions import ClaudeVersions
from dock_preview import DockPreview
from calculator_decimal import CalculatorDecimal
from resources import Resources
from user_services import UserServices


SCREENSHOT_ID = 'org.deepin.dde.keybinding.shortcut.app.screenshot'
# Instalações anteriores ao dde-shell com plugin de atalhos usam o
# dde-session-daemon, com identificador curto e resposta em JSON.
SCREENSHOT_LEGACY_ID = 'screenshot'
APP_ID = 'devedu.deepin-configs'
SCREENSHOT_KEY = '<Shift><Super>S'
SHORTCUTS = {
    'desktop_next': ('Switch to Next Desktop', 0x15000014),
    'desktop_previous': ('Switch to Previous Desktop', 0x15000012),
    'screen_next': ('Window to Next Screen', 0x13000014),
    'screen_previous': ('Window to Previous Screen', 0x13000012),
}
SERVICES = {
    'clipboard': 'deepin-clipboard-autopaste.service',
    'wallpaper': 'deepin-wallpaper.timer',
}
FEATURES = [
    ('clipboard', 'Produtividade', 'Colar ao confirmar no histórico',
     'Win + V → selecione um item → Enter. Reconhece terminais automaticamente.'),
    ('calculator_decimal', 'Produtividade', 'Vírgula decimal na calculadora',
     'Aceita a vírgula como separador decimal. Após ativar, feche a calculadora e reabra pelo menu.'),
    ('desktop_previous', 'Atalhos', 'Área de trabalho anterior', 'Ctrl + Win + ←'),
    ('desktop_next', 'Atalhos', 'Próxima área de trabalho', 'Ctrl + Win + →'),
    ('screen_previous', 'Atalhos', 'Janela no monitor anterior', 'Shift + Win + ←'),
    ('screen_next', 'Atalhos', 'Janela no próximo monitor', 'Shift + Win + →'),
    ('screenshot', 'Atalhos', 'Capturar uma área da tela', 'Win + Shift + S · Recorte e edição do Deepin.'),
    ('dock_preview', 'Aparência', 'Miniaturas ao clicar em grupos de janelas',
     'Clique em um ícone com duas ou mais janelas para escolher uma miniatura. Recarrega a barra de tarefas.'),
    ('wallpaper', 'Aparência', 'Baixar novas paisagens automaticamente',
     'Busca imagens no Unsplash conforme o timer configurado. Ao desativar, mantém a imagem atual.'),
    ('zclaude', 'Ferramentas', 'Disponibilizar o comando zclaude',
     'Usa a Z.AI com a configuração já salva. Sua chave permanece protegida.'),
]


class ConfigError(RuntimeError):
    pass


class ServiceMissing(ConfigError):
    pass


def migrate_legacy_state(state_home=None):
    state_home = Path(state_home or os.environ.get(
        'XDG_STATE_HOME', str(Path.home() / '.local/state')))
    legacy = state_home / 'deepin-configs'
    target = state_home / APP_ID
    if not legacy.exists():
        return False
    if not legacy.is_dir():
        raise ConfigError('O estado antigo não é um diretório. Nenhum arquivo foi alterado: ' + str(legacy))
    if target.exists() or target.is_symlink():
        raise ConfigError('Existem diretórios de estado antigo e novo. Nenhum backup foi sobrescrito: ' +
                          str(legacy) + ' e ' + str(target))
    legacy.rename(target)
    return True


def screenshot_keys(api):
    try:
        info = api.GetShortcut(SCREENSHOT_ID, timeout=3)
    except TypeError:
        # dbus-python recusa a chamada nova quando a assinatura é da
        # geração antiga do serviço (identificador curto + tipo + JSON).
        raw = str(api.GetShortcut(SCREENSHOT_LEGACY_ID, 0, timeout=3) or '').strip()
        try:
            info = json.loads(raw) if raw else {}
        except ValueError as error:
            raise ConfigError('Resposta inesperada do serviço de atalhos do Deepin.') from error
        if 'Accels' not in info:
            raise ConfigError('O serviço de atalhos do Deepin não registrou o atalho de captura.')
        return [str(key) for key in info['Accels'] if str(key)]
    if str(info[0]) != SCREENSHOT_ID:
        raise ConfigError('O atalho de captura não está disponível nesta sessão.')
    # O serviço retorna "None" traduzido quando não há combinação. Consultar
    # a associação real evita interpretar esse texto como uma tecla, em qualquer idioma.
    return [str(key) for key in info[3] if str(api.LookupConflictShortcut(key, timeout=3)[0]) == SCREENSHOT_ID]


def atomic_bytes(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def relocate(source, destination):
    try:
        os.replace(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        if source.is_symlink():
            fd, temporary = tempfile.mkstemp(prefix='.link-', dir=destination.parent)
            os.close(fd)
            os.unlink(temporary)
            try:
                os.symlink(os.readlink(source), temporary)
                os.replace(temporary, destination)
            finally:
                if os.path.lexists(temporary):
                    os.unlink(temporary)
        else:
            atomic_bytes(destination, source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
        source.unlink()


class Native:
    def __init__(self):
        import dbus
        self.dbus = dbus
        self.bus = dbus.SessionBus()

    def interface(self, name, path, interface=None):
        return self.dbus.Interface(self.bus.get_object(name, path), interface or name)

    def call(self, command, check=True):
        result = subprocess.run(command, capture_output=True, text=True, timeout=12)
        if check and result.returncode:
            raise ConfigError(result.stderr.strip() or 'Não foi possível aplicar a alteração.')
        return result.stdout

    def service(self, name):
        output = self.call(['systemctl', '--user', 'show', name,
                            '-p', 'LoadState', '-p', 'ActiveState', '-p', 'UnitFileState',
                            '-p', 'ExecStart'], check=False)
        values = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        if values.get('LoadState') != 'loaded':
            raise ServiceMissing('Recurso ainda não instalado.')
        if values.get('UnitFileState') in ('masked', 'masked-runtime'):
            raise ConfigError('O serviço está bloqueado pelo usuário.')
        return {'active': values.get('ActiveState') in ('active', 'activating'),
                'enabled': values.get('UnitFileState', 'disabled'),
                'dry_run': '--dry-run' in values.get('ExecStart', '')}

    def host_tool(self, name, host_root='/run/host/rootfs'):
        # Os helpers executam no host; dentro de um container Linyaps o
        # binário é conferido na raiz do hospedeiro exposta em leitura.
        candidate = Path(host_root) / 'usr/bin' / name
        if candidate.is_file():
            return str(candidate)
        return shutil.which(name)

    def requirements(self, feature):
        if feature == 'clipboard':
            if os.environ.get('XDG_SESSION_TYPE') != 'x11':
                raise ConfigError('A colagem automática requer uma sessão X11.')
            for name in ('org.deepin.dde.Clipboard1', 'org.deepin.dde.XEventMonitor1'):
                if not self.bus.name_has_owner(name):
                    raise ConfigError('O serviço nativo de colagem não está disponível nesta sessão.')
            if not self.host_tool('xdotool'):
                raise ConfigError('Instale xdotool no sistema para usar a colagem automática.')
        elif feature == 'wallpaper':
            for command in ('curl', 'file', 'gsettings'):
                if not self.host_tool(command):
                    raise ConfigError('Dependência ausente: ' + command)
            from gi.repository import Gio
            source = Gio.SettingsSchemaSource.get_default()
            if source is None or source.lookup('com.deepin.dde.appearance', True) is None:
                raise ConfigError('A configuração nativa de aparência do Deepin está ausente.')

    def set_service(self, name, active, enabled):
        flag = ['--runtime'] if enabled.endswith('-runtime') else []
        action = 'enable' if enabled.startswith('enabled') else 'disable'
        self.call(['systemctl', '--user', *flag, action, name])
        self.call(['systemctl', '--user', 'start' if active else 'stop', name])

    def global_accel(self):
        return self.interface('org.kde.kglobalaccel', '/kglobalaccel', 'org.kde.KGlobalAccel')

    def shortcut(self, action):
        return [int(key) for key in self.global_accel().shortcut(
            ['kwin', action, 'KWin', action], timeout=3) if key]

    def set_shortcut(self, action, keys):
        api = self.global_accel()
        for key in keys:
            for info in api.getGlobalShortcutsByKey(key, timeout=3):
                if str(info[0]) != action or str(info[2]) != 'kwin':
                    raise ConfigError('Esta combinação já está em uso por ' + str(info[1]) + '.')
        api.setForeignShortcut(['kwin', action, 'KWin', action],
                               self.dbus.Array(keys, signature='i'), timeout=3)
        if self.shortcut(action) != keys:
            raise ConfigError('O KWin não confirmou o atalho solicitado.')

    def keybindings(self):
        return self.interface('org.deepin.dde.Keybinding1', '/org/deepin/dde/Keybinding1')

    def screenshot(self):
        from gi.repository import Gio
        source = Gio.SettingsSchemaSource.get_default()
        if source is None or source.lookup('com.deepin.dde.keybinding.system', True) is None:
            raise ConfigError('O schema de atalhos do Deepin não está disponível nesta sessão.')
        settings = Gio.Settings.new('com.deepin.dde.keybinding.system')
        return {'active': screenshot_keys(self.keybindings()),
                'saved': list(settings.get_strv('screenshot'))}

    def screenshot_generation(self, api):
        try:
            api.GetShortcut(SCREENSHOT_ID, timeout=3)
            return 'dde-shell'
        except TypeError:
            return 'legacy'

    def screenshot_conflict_owner(self, api, key, legacy):
        if legacy:
            raw = str(api.LookupConflictingShortcut(key, timeout=3) or '').strip()
            if not raw:
                return ''
            try:
                info = json.loads(raw)
            except ValueError as error:
                raise ConfigError('Resposta inesperada do serviço de atalhos do Deepin.') from error
            identifier = str(info.get('Id', ''))
            if identifier in (SCREENSHOT_LEGACY_ID, SCREENSHOT_ID):
                return ''  # O próprio atalho de captura não é conflito.
            return str(info.get('Name') or identifier)
        conflict = api.LookupConflictShortcut(key, timeout=3)
        if str(conflict[0]) and str(conflict[0]) != SCREENSHOT_ID:
            return str(conflict[1])
        return ''

    def set_screenshot(self, value):
        from gi.repository import Gio
        api = self.keybindings()
        legacy = self.screenshot_generation(api) == 'legacy'
        for key in value['active']:
            owner = self.screenshot_conflict_owner(api, key, legacy)
            if owner:
                raise ConfigError('Esta combinação já está em uso por ' + owner + '.')
        if legacy:
            # O daemon antigo retorna "false" no ModifiedAccel mesmo quando
            # aplica a troca; a confirmação é feita pela releitura ao final.
            raw = str(api.GetShortcut(SCREENSHOT_LEGACY_ID, 0, timeout=3) or '').strip()
            try:
                info = json.loads(raw) if raw else {}
            except ValueError as error:
                raise ConfigError('Resposta inesperada do serviço de atalhos do Deepin.') from error
            for key in info.get('Accels', []):
                api.ModifiedAccel(SCREENSHOT_LEGACY_ID, 0, str(key), False, timeout=3)
            if value['active']:
                for key in value['active']:
                    api.ModifiedAccel(SCREENSHOT_LEGACY_ID, 0, str(key), True, timeout=3)
            else:
                api.Disable(SCREENSHOT_LEGACY_ID, 0, timeout=3)
            # O daemon antigo aplica a troca de forma assíncrona; aguardar a
            # confirmação por releitura evita recusar uma alteração válida.
            expected = [str(key) for key in value['active']]
            for attempt in range(10):
                raw = str(api.GetShortcut(SCREENSHOT_LEGACY_ID, 0, timeout=3) or '').strip()
                try:
                    current = json.loads(raw).get('Accels', []) if raw else []
                except ValueError:
                    current = []
                if [str(key) for key in current] == expected:
                    break
                time.sleep(0.2)
            else:
                raise ConfigError('O Deepin não confirmou o atalho de captura.')
        elif value['active']:
            accepted = api.ModifyHotkeys(SCREENSHOT_ID,
                self.dbus.Array(value['active'], signature='s'), timeout=3)
            if not accepted:
                raise ConfigError('O Deepin não aceitou o atalho de captura.')
        else:
            api.Disable(SCREENSHOT_ID, timeout=3)
        source = Gio.SettingsSchemaSource.get_default()
        if source is None or source.lookup('com.deepin.dde.keybinding.system', True) is None:
            raise ConfigError('O schema de atalhos do Deepin não está disponível nesta sessão.')
        settings = Gio.Settings.new('com.deepin.dde.keybinding.system')
        if not settings.set_strv('screenshot', value['saved']):
            raise ConfigError('Não foi possível salvar o atalho de captura.')
        Gio.Settings.sync()
        if self.screenshot() != value:
            raise ConfigError('O Deepin não confirmou a configuração de captura.')

    def native_slideshow(self):
        try:
            api = self.interface('org.deepin.dde.Appearance1', '/org/deepin/dde/Appearance1',
                                 'org.freedesktop.DBus.Properties')
            policies = json.loads(str(api.Get('org.deepin.dde.Appearance1',
                                             'WallpaperSlideShow', timeout=3)))
            return any(value not in ('', 'none', '0') for value in policies.values())
        except Exception:
            return False


class Manager:
    def __init__(self, native=None, home=None, state_dir=None, source=None, resources=None):
        self.home = Path(home or Path.home())
        self.state_dir = Path(state_dir or Path(os.environ.get(
            'XDG_STATE_HOME', str(self.home / '.local/state'))) / APP_ID)
        self.source = Path(source or Path(__file__).resolve().parents[1] / 'bin/zclaude')
        self.wrapper = self.home / '.local/bin/zclaude'
        self.disabled = self.state_dir / 'disabled/zclaude'
        self.state_file = self.state_dir / 'originals.json'
        self.native = native if native is not None else Native()
        self.resources = resources or Resources(home=self.home)
        self.user_services = UserServices(self.native, self.resources)
        self.dock_preview = DockPreview(home=self.home)
        # O drop-in gravado na ativação aponta para o runtime persistente;
        # resolver o mesmo caminho aqui evita tratá-lo como personalização
        # nas consultas de status.
        if (self.resources.current / 'gui/dock_preview.py').is_file():
            self.dock_preview.helper = self.resources.current / 'gui/dock_preview.py'
        self.calculator_decimal = CalculatorDecimal(home=self.home,
            bundle=self.resources.file('bin/deepwin-calculator').parents[1])
        try:
            self.calculator_decimal.plugin = self.resources.file('qt6/plugins/generic/libdeepwin-calculator.so')
        except RuntimeError:
            pass

    def load_state(self):
        schema = self.state_dir / 'schema.json'
        if schema.exists():
            try:
                value = json.loads(schema.read_text())
                if value != {'format': 1, 'app_id': APP_ID}:
                    raise ValueError()
            except (ValueError, OSError) as error:
                raise ConfigError('Formato de estado incompatível. Nenhum backup foi alterado.') from error
        if not self.state_file.exists():
            return {}
        try:
            values = json.loads(self.state_file.read_text())
            if not isinstance(values, dict) or set(values) - {row[0] for row in FEATURES}:
                raise ValueError('Formato de backup desconhecido')
            return values
        except (ValueError, OSError) as error:
            raise ConfigError('Não foi possível ler o backup do painel. Preserve originals.json.') from error

    def save_state(self, values):
        atomic_bytes(self.state_file, json.dumps(values, ensure_ascii=False, indent=2).encode())
        atomic_bytes(self.state_dir / 'schema.json', json.dumps({'format': 1, 'app_id': APP_ID}).encode())

    @contextmanager
    def lock(self):
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        with (self.state_dir / 'controller.lock').open('a') as stream:
            os.chmod(stream.name, 0o600)
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def capture(self, feature):
        if feature == 'calculator_decimal':
            return self.calculator_decimal.capture()
        if feature == 'dock_preview':
            return self.dock_preview.capture()
        if feature in SERVICES:
            try:
                value = self.native.service(SERVICES[feature])
            except ServiceMissing:
                if self.user_services.existing(feature):
                    raise ConfigError('Existe uma unidade personalizada não carregada. Nenhum arquivo foi alterado.')
                return {'absent': True, 'files': self.user_services.snapshot(feature)}
            if self.user_services.managed(feature):
                value['files'] = self.user_services.snapshot(feature)
            return value
        if feature in SHORTCUTS:
            return self.native.shortcut(SHORTCUTS[feature][0])
        if feature == 'screenshot':
            return self.native.screenshot()
        if feature == 'zclaude':
            if self.wrapper.is_symlink():
                return {'symlink': os.readlink(self.wrapper)}
            if self.wrapper.exists():
                return {'data': base64.b64encode(self.wrapper.read_bytes()).decode(),
                        'mode': stat.S_IMODE(self.wrapper.stat().st_mode)}
            return {'absent': True}
        raise ConfigError('Recurso desconhecido.')

    def restore_value(self, feature, value):
        if feature == 'calculator_decimal':
            if value['enabled']:
                self.apply(feature, True)
            else:
                self.calculator_decimal.configure(False)
            return
        if feature == 'dock_preview':
            if value['enabled']:
                self.apply(feature, True)
            else:
                self.dock_preview.configure(False)
            return
        if feature in SERVICES:
            if value.get('absent'):
                if self.user_services.existing(feature):
                    if not self.user_services.managed(feature):
                        raise ConfigError('Uma unidade personalizada apareceu após o backup. Preserve-a antes de restaurar.')
                    self.native.set_service(SERVICES[feature], False, 'disabled')
                self.user_services.restore_files(feature, value['files'])
            else:
                if 'files' in value:
                    owned = self.user_services.managed(feature)
                    if not owned and self.user_services.existing(feature):
                        raise ConfigError('Uma unidade personalizada apareceu após o backup. Preserve-a antes de restaurar.')
                    self.user_services.restore_files(feature, value['files'])
                self.native.set_service(SERVICES[feature], value['active'], value['enabled'])
        elif feature in SHORTCUTS:
            self.native.set_shortcut(SHORTCUTS[feature][0], value)
        elif feature == 'screenshot':
            self.native.set_screenshot(value)
        elif feature == 'zclaude':
            if value.get('absent'):
                if self.wrapper.exists() or self.wrapper.is_symlink():
                    self.wrapper.unlink()
            elif 'symlink' in value:
                self.wrapper.parent.mkdir(parents=True, exist_ok=True)
                self.wrapper.unlink(missing_ok=True)
                self.wrapper.symlink_to(value['symlink'])
            else:
                atomic_bytes(self.wrapper, base64.b64decode(value['data']), value['mode'])

    def apply(self, feature, enabled):
        if feature == 'calculator_decimal':
            if enabled:
                runtime = self.resources.ensure()
                self.calculator_decimal.launcher = runtime / 'bin/deepwin-calculator'
                self.calculator_decimal.plugin = runtime / 'qt6/plugins/generic/libdeepwin-calculator.so'
            self.calculator_decimal.configure(enabled)
            return
        if feature == 'dock_preview':
            if enabled:
                runtime = self.resources.ensure()
                self.dock_preview.helper = runtime / 'gui/dock_preview.py'
            self.dock_preview.configure(enabled)
            return
        if feature in SERVICES:
            if enabled:
                if hasattr(self.native, 'requirements'):
                    self.native.requirements(feature)
                try:
                    self.native.service(SERVICES[feature])
                    prepare = self.user_services.managed(feature) is not None
                except ServiceMissing:
                    prepare = True
                if prepare:
                    self.user_services.prepare(feature)
            else:
                original = self.load_state().get(feature, {})
                if original.get('absent'):
                    self.restore_value(feature, original)
                    return
            self.native.set_service(SERVICES[feature], enabled,
                                    'enabled' if enabled else 'disabled')
            if feature == 'wallpaper' and not enabled:
                self.native.call(['systemctl', '--user', 'stop', 'deepin-wallpaper.service'])
        elif feature in SHORTCUTS:
            action, key = SHORTCUTS[feature]
            values = self.native.shortcut(action)
            values = list(dict.fromkeys(values + [key])) if enabled else [x for x in values if x != key]
            self.native.set_shortcut(action, values)
        elif feature == 'screenshot':
            values = self.native.screenshot()
            for name in ('active', 'saved'):
                keys = values[name]
                values[name] = list(dict.fromkeys(keys + [SCREENSHOT_KEY])) if enabled else [
                    key for key in keys if key != SCREENSHOT_KEY]
            self.native.set_screenshot(values)
        elif feature == 'zclaude':
            if enabled:
                self.resources.ensure()
                if self.wrapper.exists() and os.access(self.wrapper, os.X_OK):
                    return
                if self.wrapper.exists() or self.wrapper.is_symlink():
                    raise ConfigError('Já existe um arquivo zclaude não executável. Preserve-o antes de ativar.')
                self.wrapper.parent.mkdir(parents=True, exist_ok=True)
                if self.disabled.exists() or self.disabled.is_symlink():
                    relocate(self.disabled, self.wrapper)
                else:
                    atomic_bytes(self.wrapper, self.source.read_bytes(), 0o755)
            elif self.wrapper.exists() or self.wrapper.is_symlink():
                self.disabled.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                relocate(self.wrapper, self.disabled)
        else:
            raise ConfigError('Recurso desconhecido.')

    def change(self, feature, enabled):
        if feature not in {row[0] for row in FEATURES}:
            raise ConfigError('Recurso desconhecido.')
        with self.lock():
            originals = self.load_state()
            before = self.capture(feature)
            added = feature not in originals
            if added:
                originals[feature] = before
                self.save_state(originals)
            try:
                self.apply(feature, enabled)
                item = self.feature_status(feature)
                if not item['available'] or item['enabled'] != enabled:
                    raise ConfigError(item.get('error') or 'O estado solicitado não foi confirmado.')
            except Exception as error:
                try:
                    self.restore_value(feature, before)
                except Exception:
                    raise ConfigError('A alteração falhou. O backup foi preservado para restauração.') from error
                if added:
                    originals.pop(feature)
                    self.save_state(originals)
                raise
            if self.capture(feature) == originals[feature]:
                originals.pop(feature)
                self.save_state(originals)

    def restore(self, feature=None):
        with self.lock():
            originals = self.load_state()
            if feature is not None and feature not in originals:
                raise ConfigError('Este recurso não tem alterações salvas pelo painel.')
            failures = []
            for name in [feature] if feature else list(originals):
                try:
                    self.restore_value(name, originals[name])
                    del originals[name]
                    self.save_state(originals)
                except Exception:
                    failures.append(name)
            if failures:
                raise ConfigError('Não foi possível restaurar: ' + ', '.join(failures) +
                                  '. Os respectivos backups foram preservados.')

    def feature_status(self, feature):
        item = {'id': feature, 'available': True, 'enabled': False, 'status': 'Desativado'}
        try:
            if feature in SERVICES:
                try:
                    values = self.native.service(SERVICES[feature])
                except ServiceMissing:
                    self.resources.available()
                    if self.user_services.existing(feature):
                        raise ConfigError('Existe uma unidade local não carregada. Preserve-a e confira o systemd do usuário.')
                    if hasattr(self.native, 'requirements'):
                        self.native.requirements(feature)
                    item.update(status='Pronto para ativar',
                                note=('Será criado um timer de uma hora ao ativar.' if feature == 'wallpaper' else
                                      'Os arquivos necessários serão preparados ao ativar este recurso.'))
                    return item
                item['enabled'] = values['active']
                automatic = values['enabled'].startswith('enabled')
                item['status'] = ('Ativo · Início automático' if automatic else 'Ativo nesta sessão') if values['active'] else (
                    'Parado · Início automático habilitado' if automatic else 'Desativado')
                if feature == 'clipboard' and values.get('dry_run') and values['active']:
                    item['status'] = 'Ativo em simulação · Não envia colagem'
                if feature == 'wallpaper' and self.native.native_slideshow():
                    item['note'] = 'A rotação de imagens do Deepin também está ativa e é independente deste download.'
            elif feature == 'calculator_decimal':
                values = self.calculator_decimal.status()
                item.update(values)
                item['status'] = 'Vírgula decimal habilitada' if values['enabled'] else 'Teclado padrão da calculadora'
            elif feature == 'dock_preview':
                values = self.dock_preview.status()
                item.update(values)
                item['status'] = 'Prévia ao clicar ativada' if values['enabled'] else 'Comportamento padrão do dock'
            elif feature in SHORTCUTS:
                action, key = SHORTCUTS[feature]
                item['enabled'] = key in self.native.shortcut(action)
                item['status'] = 'Atalho ativo' if item['enabled'] else 'Combinação desativada'
            elif feature == 'screenshot':
                values = self.native.screenshot()
                item['enabled'] = SCREENSHOT_KEY in values['active']
                item['status'] = 'Atalho ativo' if item['enabled'] else 'Combinação desativada'
                if item['enabled'] != (SCREENSHOT_KEY in values['saved']):
                    item['note'] = 'A configuração salva é diferente do atalho ativo nesta sessão.'
            elif feature == 'zclaude':
                item['enabled'] = self.wrapper.is_file() and os.access(self.wrapper, os.X_OK)
                item['status'] = 'Comando disponível' if item['enabled'] else 'Comando desativado'
                if (self.home / '.config/zai/api_key').is_file():
                    item['status'] += ' · Chave cadastrada'
            else:
                raise ConfigError('Recurso desconhecido.')
        except Exception as error:
            item.update(available=False, error=str(error), status='Indisponível')
        return item

    def status(self):
        features = []
        for feature, category, title, description in FEATURES:
            item = self.feature_status(feature)
            item.update(category=category, title=title, description=description)
            features.append(item)
        originals = self.load_state()
        try:
            claude = ClaudeVersions(home=self.home, state_dir=self.state_dir).status()
        except Exception as error:
            claude = {'error': str(error)}
        installation = {'version': self.resources.version, 'root': str(self.resources.root)}
        local_command = self.home / '.local/bin/deepwin'
        if str(self.resources.root).startswith('/usr/') and local_command.exists():
            installation['note'] = 'Uma instalação local também existe. Use /usr/bin/deepwin para abrir o pacote.'
        return {'features': features, 'installation': installation, 'restore_count': len(originals),
                'restore_titles': [row[2] for row in FEATURES if row[0] in originals],
                'claude': claude}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('migrate-state')
    sub.add_parser('claude-list')
    select = sub.add_parser('claude-select')
    select.add_argument('version')
    sub.add_parser('claude-restore')
    change = sub.add_parser('set')
    change.add_argument('feature', choices=[row[0] for row in FEATURES])
    change.add_argument('enabled', choices=('on', 'off'))
    restore = sub.add_parser('restore')
    restore.add_argument('feature', nargs='?', choices=[row[0] for row in FEATURES])
    args = parser.parse_args()
    try:
        if args.command == 'migrate-state':
            changed = migrate_legacy_state()
            print(json.dumps({'ok': True, 'changed': changed,
                              'message': 'Estado migrado para o DeepWin.' if changed else 'Nenhuma migração pendente.'},
                             ensure_ascii=False))
            return 0
        if args.command in ('set', 'restore', 'claude-select', 'claude-restore'):
            migrate_legacy_state()
        message = ''
        versions = ClaudeVersions()
        if args.command == 'claude-list':
            versions.catalog(refresh=True)
            message = 'Lista de versões atualizada.'
        elif args.command == 'claude-select':
            if os.environ.get('ZCLAUDE_CLAUDE_BIN'):
                raise ConfigError('Remova ZCLAUDE_CLAUDE_BIN do ambiente para usar o seletor.')
            versions.choose(args.version)
            message = 'Versão selecionada. A mudança vale para novas execuções do zclaude.'
        elif args.command == 'claude-restore':
            versions.restore()
            message = 'Seleção anterior do Claude restaurada.'
        manager = Manager()
        if args.command == 'set':
            manager.change(args.feature, args.enabled == 'on')
            message = 'Alteração aplicada.'
        elif args.command == 'restore':
            manager.restore(args.feature)
            message = 'Configurações anteriores restauradas.'
        result = manager.status()
        result.update(ok=True, message=message)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as error:
        print(json.dumps({'ok': False, 'message': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
