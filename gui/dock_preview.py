#!/usr/bin/python3
"""Prévia nativa ao clicar em grupos do dde-shell, usando pacote por usuário.

O QML é derivado localmente dos arquivos GPL-3.0-or-later do dde-shell.
Nenhum arquivo do sistema é modificado ou redistribuído por este módulo.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

APP_ID = 'devedu.deepin-configs'
PLUGIN = 'org.deepin.ds.dock.taskmanager'
MARKER = '.deepwin-preview.json'
SERVICE = 'dde-shell@DDE.service'
ORIGINAL = '                TaskManager.requestActivate(index);'
REPLACEMENT = '''                // DeepWin: reutilizar a prévia nativa em grupos de janelas.
                if (root.windows.length > 1) {
                    root.onEntered();
                    previewTimer.stop();
                    previewTimer.triggered();
                    return;
                }
                TaskManager.requestActivate(index);'''


class DockPreviewError(RuntimeError):
    pass


def patch_qml(source):
    required = ('function onEntered()', 'id: previewTimer', 'previewTimer.start()',
                'taskmanager.Applet.requestPreview(root.modelIndex, Panel.rootObject, xOffset, yOffset, Panel.position);')
    if source.count(ORIGINAL) != 1 or any(value not in source for value in required):
        raise DockPreviewError('Esta versão do dock não corresponde à integração de prévias suportada.')
    return source.replace(ORIGINAL, REPLACEMENT, 1)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root):
    result = {}
    for path in root.rglob('*'):
        if path.is_symlink():
            raise DockPreviewError('Links simbólicos inesperados no pacote de prévias. Preserve a personalização.')
        if path.is_file() and path != root / MARKER:
            result[str(path.relative_to(root))] = digest(path)
    return result


SYSTEM_PLUGIN_DIR = '/usr/share/dde-shell/' + PLUGIN
HOST_ROOT = '/run/host/rootfs'


def resolve_system_dir(system_dir=None, host_root=None):
    """Localizar o QML original do dock; explicito vence, hospedeiro em seguida.

    Dentro de um container Linyaps o dock do hospedeiro é lido pela raiz
    exposta em /run/host/rootfs; fora dele só o caminho do sistema existe.
    """
    if system_dir is not None:
        return Path(system_dir)
    candidates = [Path(SYSTEM_PLUGIN_DIR),
                  Path(host_root or HOST_ROOT) / 'usr/share/dde-shell' / PLUGIN]
    return next((path for path in candidates
                 if (path / 'AppItem.qml').is_file()), candidates[0])


class DockPreview:
    def __init__(self, home=None, data_home=None, system_dir=None, helper=None,
                 config_home=None, host_root=None):
        self.home = Path(home or Path.home())
        self.data_home = Path(data_home or os.environ.get('XDG_DATA_HOME', self.home / '.local/share'))
        self.system_dir = resolve_system_dir(system_dir, host_root)
        self.local_dir = self.data_home / 'dde-shell' / PLUGIN
        config = Path(config_home or os.environ.get('XDG_CONFIG_HOME', self.home / '.config'))
        self.dropin = config / 'systemd/user' / (SERVICE + '.d') / '50-deepwin-preview.conf'
        self.helper = Path(helper or self.data_home / APP_ID / 'gui/dock_preview.py')

    def source(self):
        try:
            source = (self.system_dir / 'AppItem.qml').read_text()
            metadata = json.loads((self.system_dir / 'metadata.json').read_text())
            if metadata['Plugin']['Id'] != PLUGIN or metadata['Plugin']['Url'] != 'TaskManager.qml':
                raise ValueError()
            patch_qml(source)
            return source
        except (OSError, ValueError, KeyError) as error:
            raise DockPreviewError('Dock dde-shell compatível não encontrado.') from error

    def owned(self):
        if not self.local_dir.exists() and not self.local_dir.is_symlink():
            return None
        if self.local_dir.is_symlink():
            raise DockPreviewError('Já existe uma personalização do dock. Preserve-a antes de ativar este recurso.')
        try:
            marker = json.loads((self.local_dir / MARKER).read_text())
            if marker.get('owner') != APP_ID or marker.get('format') != 1:
                raise ValueError()
            if marker['files'] != tree_hashes(self.local_dir):
                raise ValueError()
            return marker
        except (OSError, ValueError, KeyError) as error:
            raise DockPreviewError('O pacote local do dock contém personalizações. Nenhum arquivo foi removido.') from error

    def dropin_text(self):
        path = str(self.helper).replace('%', '%%')
        return '# Gerenciado pelo DeepWin\n[Service]\nExecStartPre=-/usr/bin/python3 ' + json.dumps(path, ensure_ascii=False) + ' refresh\n'

    def check_dropin(self):
        legacy_helper = self.data_home / APP_ID / 'gui/dock_preview.py'
        legacy_text = '# Gerenciado pelo DeepWin\n[Service]\nExecStartPre=-/usr/bin/python3 ' + json.dumps(str(legacy_helper).replace('%', '%%'), ensure_ascii=False) + ' refresh\n'
        if self.dropin.is_symlink() or (self.dropin.exists() and self.dropin.read_text() not in (self.dropin_text(), legacy_text)):
            raise DockPreviewError('O ajuste de inicialização do dock foi personalizado. Preserve-o antes de continuar.')

    def build(self):
        source = self.source()
        self.data_home.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.deepwin-preview-', dir=self.data_home) as temporary:
            stage = Path(temporary) / PLUGIN
            shutil.copytree(self.system_dir, stage)
            (stage / 'AppItem.qml').write_text(patch_qml(source))
            marker = {'owner': APP_ID, 'format': 1, 'source_files': tree_hashes(self.system_dir),
                      'files': tree_hashes(stage)}
            (stage / MARKER).write_text(json.dumps(marker, ensure_ascii=False, indent=2))
            self.local_dir.parent.mkdir(parents=True, exist_ok=True)
            previous = Path(temporary) / 'previous'
            if self.local_dir.exists():
                self.owned()
                self.local_dir.rename(previous)
            try:
                stage.rename(self.local_dir)
            except Exception:
                if previous.exists():
                    previous.rename(self.local_dir)
                raise

    def configure(self, enabled, reload=True):
        self.owned()
        self.check_dropin()
        if enabled:
            if not self.helper.is_file():
                raise DockPreviewError('Instale o DeepWin antes de ativar a integração com o dock.')
            self.build()
            self.dropin.parent.mkdir(parents=True, exist_ok=True)
            self.dropin.write_text(self.dropin_text())
        else:
            if self.local_dir.exists():
                shutil.rmtree(self.local_dir)
            self.dropin.unlink(missing_ok=True)
        if reload:
            try:
                subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True,
                               capture_output=True, text=True, timeout=10)
                subprocess.run(['systemctl', '--user', 'restart', SERVICE], check=True,
                               capture_output=True, text=True, timeout=20)
            except (OSError, subprocess.SubprocessError) as error:
                raise DockPreviewError('Não foi possível recarregar a barra de tarefas. Confira o serviço dde-shell.') from error

    def refresh(self):
        marker = self.owned()
        if not marker:
            return
        try:
            self.source()
            if tree_hashes(self.system_dir) != marker['source_files']:
                self.build()
        except (DockPreviewError, OSError, ValueError):
            # Em atualizações incompatíveis, carregar o pacote original do sistema.
            self.owned()
            shutil.rmtree(self.local_dir)
            raise DockPreviewError('O dock foi atualizado e o ajuste de prévias foi suspenso por compatibilidade.')

    def capture(self):
        return {'enabled': self.owned() is not None}

    def status(self):
        marker = self.owned()
        self.check_dropin()
        self.source()
        result = {'enabled': marker is not None, 'available': True}
        if marker and marker['source_files'] != tree_hashes(self.system_dir):
            result['note'] = 'O ajuste será atualizado ao recarregar a barra de tarefas.'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('refresh', 'status'))
    args = parser.parse_args()
    try:
        manager = DockPreview()
        if args.command == 'refresh':
            manager.refresh()
        else:
            print(json.dumps(manager.status(), ensure_ascii=False))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
