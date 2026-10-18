"""Preparação e restauração de unidades por usuário, com ownership dos arquivos."""
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

SERVICE_FILES = {
    'clipboard': ('deepin-clipboard-autopaste.service',),
    'wallpaper': ('deepin-wallpaper.service', 'deepin-wallpaper.timer'),
}


class ServiceError(RuntimeError):
    pass


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def command_path(path):
    return json.dumps(str(path).replace('%', '%%').replace('$', '$$'), ensure_ascii=False)


class UserServices:
    def __init__(self, native, resources, config_home=None):
        self.native = native
        self.resources = resources
        config = Path(config_home or os.environ.get('XDG_CONFIG_HOME', resources.home / '.config'))
        self.units = config / 'systemd/user'

    def marker(self, feature):
        return self.resources.data / ('service-' + feature + '.json')

    def existing(self, feature):
        return any((self.units / name).exists() or (self.units / name).is_symlink()
                   for name in SERVICE_FILES[feature])

    def managed(self, feature):
        path = self.marker(feature)
        if not path.exists():
            return None
        if path.is_symlink():
            raise ServiceError('O registro do serviço foi personalizado.')
        try:
            value = json.loads(path.read_text())
            if value.get('format') != 1 or value.get('owner') != 'devedu.deepin-configs':
                raise ValueError()
            expected = value['files']
            if set(expected) != set(SERVICE_FILES[feature]):
                raise ValueError()
            for name, digest in expected.items():
                unit = self.units / name
                if unit.is_symlink() or hashlib.sha256(unit.read_bytes()).hexdigest() != digest:
                    raise ValueError()
            return value
        except (ValueError, OSError, KeyError, AttributeError) as error:
            raise ServiceError('A unidade contém personalizações. Nenhum arquivo foi sobrescrito.') from error

    def snapshot(self, feature):
        result = {}
        for path in [self.units / name for name in SERVICE_FILES[feature]] + [self.marker(feature)]:
            if path.is_symlink():
                item = {'symlink': os.readlink(path)}
            elif path.exists():
                item = {'data': base64.b64encode(path.read_bytes()).decode(), 'mode': path.stat().st_mode & 0o777}
            else:
                item = {'absent': True}
            result[path.name] = item
        return result

    def restore_files(self, feature, files):
        paths = [self.units / name for name in SERVICE_FILES[feature]] + [self.marker(feature)]
        # Apenas arquivos previamente criados ou capturados por esta integração.
        for path in paths:
            item = files[path.name]
            if item.get('absent'):
                if path.exists() or path.is_symlink():
                    path.unlink()
            elif 'symlink' in item:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.unlink(missing_ok=True)
                path.symlink_to(item['symlink'])
            else:
                atomic(path, base64.b64decode(item['data']), item['mode'])
        self.native.call(['systemctl', '--user', 'daemon-reload'])

    def prepare(self, feature):
        owned = self.managed(feature)
        if self.existing(feature) and not owned:
            return False  # Uma unidade anterior continua sob controle de seu proprietário.
        runtime = self.resources.ensure()
        values = {}
        for name in SERVICE_FILES[feature]:
            text = self.resources.file('systemd/' + name).read_text()
            text = text.replace('@CLIPBOARD_EXEC@', command_path(runtime / 'bin/deepin-clipboard-autopaste'))
            text = text.replace('@WALLPAPER_EXEC@', command_path(runtime / 'bin/refresh-deepin-wallpaper'))
            values[name] = text.encode()
        before = self.snapshot(feature)
        try:
            for name, data in values.items():
                atomic(self.units / name, data)
            marker = {'owner': 'devedu.deepin-configs', 'format': 1,
                      'files': {name: hashlib.sha256(data).hexdigest() for name, data in values.items()}}
            atomic(self.marker(feature), json.dumps(marker, indent=2).encode(), 0o600)
            self.native.call(['systemctl', '--user', 'daemon-reload'])
        except Exception:
            self.restore_files(feature, before)
            raise
        return True
