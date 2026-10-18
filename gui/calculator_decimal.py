#!/usr/bin/python3
"""Integração reversível do filtro Qt decimal com o launcher da calculadora."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

APP_ID = 'devedu.deepin-configs'
DESKTOP = 'deepin-calculator.desktop'


class CalculatorError(RuntimeError):
    pass


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def desktop_quote(path):
    # Quoting do Desktop Entry Exec é diferente do quoting de shell.
    escaped = str(path).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
    return '"' + escaped.replace('%', '%%') + '"'


def refresh_applications():
    # O Deepin mantém um catálogo próprio; outros desktops usam o launcher XDG.
    import dbus
    bus = dbus.SessionBus()
    name = 'org.desktopspec.ApplicationManager1'
    if bus.name_has_owner(name):
        api = dbus.Interface(bus.get_object(name, '/org/desktopspec/ApplicationManager1'), name)
        api.ReloadApplications(timeout=5)


class CalculatorDecimal:
    def __init__(self, home=None, data_home=None, sources=None, refresh=None, bundle=None):
        home = Path(home or Path.home())
        self.data_home = Path(data_home or os.environ.get('XDG_DATA_HOME', home / '.local/share'))
        self.resource = self.data_home / APP_ID
        self.refresh = refresh or refresh_applications
        self.desktop = self.data_home / 'applications' / DESKTOP
        self.flag = self.resource / 'calculator-enabled.json'
        self.bundle = Path(bundle or self.resource)
        self.launcher = self.bundle / 'bin/deepwin-calculator'
        self.plugin = self.bundle / 'qt6/plugins/generic/libdeepwin-calculator.so'
        data_dirs = os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
        self.sources = [Path(p) for p in sources] if sources is not None else [
            Path('/var/lib/linglong/entries/share/applications') / DESKTOP,
            *[Path(p) / 'applications' / DESKTOP for p in data_dirs if p]]

    def source(self):
        for path in self.sources:
            if path.is_file() and path != self.desktop:
                text = path.read_text()
                # Suportar os launchers oficiais, sem executar comandos de terceiros.
                command = re.search(r'^Exec=(.+)$', text, re.M)
                if command and command[1] in (
                    '/usr/bin/ll-cli run org.deepin.calculator -- deepin-calculator',
                    'deepin-calculator', '/usr/bin/deepin-calculator'):
                    return text
        raise CalculatorError('Launcher compatível da calculadora Deepin não encontrado.')

    def owned(self):
        if self.desktop.is_symlink() or self.flag.is_symlink():
            raise CalculatorError('Existe uma personalização da calculadora. Nenhum link foi alterado.')
        if not self.desktop.exists() and not self.flag.exists():
            return False
        try:
            state = json.loads(self.flag.read_text())
            if (state.get('owner') != APP_ID or state.get('format') != 1 or
                state.get('desktop_sha256') != hashlib.sha256(self.desktop.read_bytes()).hexdigest()):
                raise ValueError()
        except (OSError, ValueError, TypeError, AttributeError) as error:
            raise CalculatorError('O launcher local da calculadora contém personalizações. Nenhum arquivo foi sobrescrito.') from error
        return True

    def capture(self):
        return {'enabled': self.owned()}

    def status(self):
        enabled = self.owned()
        self.source()
        if not self.plugin.is_file() or not self.launcher.is_file():
            raise CalculatorError('Instale o DeepWin para disponibilizar o filtro decimal Qt 6.')
        return {'available': True, 'enabled': enabled,
                'note': 'Feche a calculadora e reabra pelo menu para carregar o ajuste.' if enabled else ''}

    def configure(self, enabled):
        active = self.owned()
        if enabled:
            self.status()
            text = self.source()
            text = re.sub(r'^Exec=.+$', lambda _match: 'Exec=' + desktop_quote(self.launcher) + ' --deepwin-flag ' + desktop_quote(self.flag), text, count=1, flags=re.M)
            text = re.sub(r'^DBusActivatable=.+$', 'DBusActivatable=false', text, flags=re.M)
            text += '\n# Launcher decimal gerenciado pelo DeepWin\n'
            data = text.encode()
            marker = json.dumps({'owner': APP_ID, 'format': 1,
                                 'desktop_sha256': hashlib.sha256(data).hexdigest()}).encode()
            old_desktop = self.desktop.read_bytes() if active else None
            atomic(self.desktop, data)
            try:
                atomic(self.flag, marker, 0o600)
            except Exception:
                if old_desktop is None:
                    self.desktop.unlink()
                else:
                    atomic(self.desktop, old_desktop)
                raise
        elif active:
            # O plugin consulta a flag a cada evento; desativar vale também na janela aberta.
            marker = self.flag.read_bytes()
            self.flag.unlink()
            try:
                self.desktop.unlink()
            except Exception:
                atomic(self.flag, marker, 0o600)
                raise

        self.refresh()
