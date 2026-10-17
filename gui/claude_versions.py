#!/usr/bin/python3
"""Versões isoladas do Claude para zclaude; não lê credenciais ou settings.json."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

APP_ID = 'devedu.deepin-configs'
PACKAGE = '@anthropic-ai/claude-code'
REGISTRY = 'https://registry.npmjs.org/'
VERSION = re.compile(r'\d+\.\d+\.\d+\Z')
CHECK_INTERVAL = 24 * 60 * 60


class VersionError(RuntimeError):
    pass


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def clean_env():
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in ('TOKEN', 'SECRET', 'PASSWORD', 'API_KEY'))}
    env.update(DISABLE_AUTOUPDATER='1', DISABLE_UPDATES='1',
               npm_config_update_notifier='false', npm_config_audit='false', npm_config_fund='false')
    return env


class ClaudeVersions:
    def __init__(self, home=None, state_dir=None, data_dir=None, cache_dir=None):
        self.home = Path(home or Path.home())
        self.state_dir = Path(state_dir or Path(os.environ.get(
            'XDG_STATE_HOME', self.home / '.local/state')) / APP_ID)
        self.data_dir = Path(data_dir or Path(os.environ.get(
            'XDG_DATA_HOME', self.home / '.local/share')) / APP_ID / 'claude')
        self.cache_dir = Path(cache_dir or Path(os.environ.get(
            'XDG_CACHE_HOME', self.home / '.cache')) / APP_ID)
        self.selection_file = self.state_dir / 'claude-selection.json'
        self.catalog_file = self.cache_dir / 'claude-versions.json'

    @contextmanager
    def lock(self, blocking=True):
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.state_dir / 'claude-versions.lock').open('a') as stream:
            os.chmod(stream.name, 0o600)
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            except BlockingIOError:
                yield False
                return
            yield True

    def selection(self):
        if not self.selection_file.exists():
            return None
        try:
            value = json.loads(self.selection_file.read_text())
            if not isinstance(value, dict) or value.get('mode') not in ('stable', 'pinned', 'system'):
                raise ValueError()
            if value['mode'] != 'system' and not VERSION.fullmatch(str(value.get('version', ''))):
                raise ValueError()
            return value
        except (ValueError, OSError) as error:
            raise VersionError('Seleção de versão inválida. Preserve claude-selection.json.') from error

    def binary(self, version):
        if not VERSION.fullmatch(version):
            raise VersionError('Número de versão inválido.')
        return self.data_dir / 'versions' / version / 'bin/claude'

    def catalog(self, refresh=False):
        if not refresh and self.catalog_file.exists():
            try:
                cached = json.loads(self.catalog_file.read_text())
                if time.time() - cached['fetched_at'] < CHECK_INTERVAL:
                    return cached
            except (ValueError, KeyError, OSError):
                pass
        try:
            request = urllib.request.Request(REGISTRY + PACKAGE,
                headers={'Accept': 'application/vnd.npm.install-v1+json', 'User-Agent': 'DeepWin/1.0'})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.load(response)
            versions = sorted((v for v in data['versions'] if VERSION.fullmatch(v)),
                              key=lambda v: tuple(map(int, v.split('.'))), reverse=True)
            stable = data['dist-tags']['stable']
            if stable not in versions:
                raise ValueError()
            catalog = {'versions': versions, 'stable': stable, 'fetched_at': time.time()}
            write_json(self.catalog_file, catalog)
            return catalog
        except Exception as error:
            raise VersionError('Não foi possível consultar as versões no registro npm. Confira sua conexão.') from error

    def install(self, version):
        target = self.binary(version)
        if target.is_file() and os.access(target, os.X_OK):
            self.verify(target, version)
            return target
        prefix = target.parent.parent
        if prefix.exists():
            raise VersionError('O diretório dessa versão está incompleto. A versão atual foi preservada.')
        npm = shutil.which('npm')
        if not npm:
            raise VersionError('Instale Node.js e npm para baixar versões do Claude.')
        prefix.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=prefix.parent) as temporary:
            staging = Path(temporary) / 'prefix'
            try:
                subprocess.run([npm, 'install', '--global', '--prefix', str(staging),
                    '--registry=' + REGISTRY, '--no-audit', '--no-fund', PACKAGE + '@' + version],
                    cwd=temporary, env=clean_env(), capture_output=True, text=True, timeout=240, check=True)
                self.verify(staging / 'bin/claude', version)
                staging.rename(prefix)
            except (subprocess.SubprocessError, OSError) as error:
                raise VersionError('Falha ao instalar o Claude. A versão atual foi preservada; confira Node.js, npm, conexão e espaço em disco.') from error
        return target

    def verify(self, executable, version):
        try:
            result = subprocess.run([str(executable), '--version'], env=clean_env(),
                                    capture_output=True, text=True, timeout=15, check=True)
            if result.stdout.split()[0] != version:
                raise ValueError()
        except (subprocess.SubprocessError, OSError, ValueError, IndexError) as error:
            raise VersionError('O executável baixado não confirmou a versão solicitada. A seleção anterior foi preservada.') from error

    def choose(self, choice):
        if choice not in ('stable', 'system') and not VERSION.fullmatch(choice):
            raise VersionError('Escolha Stable, Claude do sistema ou um número de versão publicado.')
        with self.lock():
            previous = self.selection()
            if choice == 'system':
                if not shutil.which('claude'):
                    raise VersionError('O comando claude não está disponível no PATH.')
                value = {'mode': 'system'}
            else:
                catalog = self.catalog(refresh=choice == 'stable')
                version = catalog['stable'] if choice == 'stable' else choice
                if version not in catalog['versions']:
                    raise VersionError('Essa versão não está publicada no registro npm.')
                self.install(version)
                value = {'mode': 'stable' if choice == 'stable' else 'pinned',
                         'version': version, 'checked_at': time.time()}
            if previous and all(value.get(k) == previous.get(k) for k in ('mode', 'version')):
                value['previous'] = previous.get('previous')
                if 'previous' not in previous:
                    value.pop('previous')
            else:
                value['previous'] = ({k: v for k, v in previous.items() if k != 'previous'}
                                     if previous else None)
            write_json(self.selection_file, value)

    def restore(self):
        with self.lock():
            current = self.selection()
            if not current or 'previous' not in current:
                raise VersionError('Não há troca de versão para desfazer.')
            previous = current['previous']
            if previous and previous['mode'] != 'system':
                self.verify(self.binary(previous['version']), previous['version'])
            if previous is None:
                self.selection_file.unlink()
            else:
                write_json(self.selection_file, previous)

    def refresh_stable(self):
        with self.lock(blocking=False) as acquired:
            if not acquired:
                return
            current = self.selection()
            if not current or current['mode'] != 'stable':
                return
            if time.time() - current.get('checked_at', 0) < CHECK_INTERVAL:
                return
            try:
                version = self.catalog(refresh=True)['stable']
                self.install(version)
                current.update(version=version)
                current.pop('update_error', None)
            except VersionError as error:
                current['update_error'] = str(error)
            current['checked_at'] = time.time()
            write_json(self.selection_file, current)

    def resolve(self, background=True):
        override = os.environ.get('ZCLAUDE_CLAUDE_BIN')
        if override:
            if not Path(override).is_file() or not os.access(override, os.X_OK):
                raise VersionError('ZCLAUDE_CLAUDE_BIN não aponta para um executável válido.')
            return str(Path(override).resolve()), False
        current = self.selection()
        if not current:
            legacy = self.home / '.local/share/claude-glm/bin/claude'
            return (str(legacy), False) if os.access(legacy, os.X_OK) else ('claude', False)
        if current['mode'] == 'system':
            return 'claude', False
        binary = self.binary(current['version'])
        if not os.access(binary, os.X_OK):
            raise VersionError('A versão selecionada não está disponível. Selecione novamente pela GUI.')
        if (background and current['mode'] == 'stable'
                and time.time() - current.get('checked_at', 0) >= CHECK_INTERVAL):
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'refresh-stable'],
                             env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        return str(binary), True

    def status(self):
        value = self.selection()
        mode = value['mode'] if value else 'legacy'
        version = value.get('version', '') if value else ''
        if not value:
            package = self.home / '.local/share/claude-glm/lib/node_modules' / PACKAGE / 'package.json'
            try:
                version = json.loads(package.read_text()).get('version', '')
            except (OSError, ValueError):
                pass
        versions = []
        stable = ''
        if self.catalog_file.exists():
            try:
                catalog = json.loads(self.catalog_file.read_text())
                versions, stable = catalog['versions'], catalog['stable']
            except (ValueError, KeyError, OSError):
                pass
        return {'mode': mode, 'version': version, 'versions': versions, 'stable': stable,
                'can_restore': bool(value and 'previous' in value),
                'override': bool(os.environ.get('ZCLAUDE_CLAUDE_BIN')),
                'update_error': value.get('update_error', '') if value else ''}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('resolve', 'refresh-stable', 'status'))
    args = parser.parse_args()
    try:
        manager = ClaudeVersions()
        if args.command == 'resolve':
            binary, managed = manager.resolve()
            print(binary)
            print('managed' if managed else 'external')
        elif args.command == 'refresh-stable':
            manager.refresh_stable()
        else:
            print(json.dumps(manager.status(), ensure_ascii=False))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
