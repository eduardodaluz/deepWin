#!/usr/bin/python3
"""Ajustes nativos do dock do dde-shell, usando pacote por usuário.

- preview: prévia ao clicar em grupos de janelas;
- workspace: aplicativos não fixados aparecem só na área de trabalho atual.

O QML é derivado localmente dos arquivos GPL-3.0-or-later do dde-shell.
Nenhum arquivo do sistema é modificado ou redistribuído por este módulo.
"""
import argparse
import ctypes
import hashlib
import itertools
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import sys

APP_ID = 'devedu.deepin-configs'
PLUGIN = 'org.deepin.ds.dock.taskmanager'
MARKER = '.deepwin-preview.json'
SERVICE = 'dde-shell@DDE.service'
TRACKER = 'deepwin-dock-workspaces.service'
FEATURES = ('preview', 'workspace')
ORIGINAL = '                TaskManager.requestActivate(index);'
REPLACEMENT = '''                // DeepWin: reutilizar a prévia nativa em grupos de janelas.
                if (root.windows.length > 1) {
                    root.onEntered();
                    previewTimer.stop();
                    previewTimer.triggered();
                    return;
                }
                TaskManager.requestActivate(index);'''

WORKSPACE_MODEL = '''        model: DelegateModel {
            id: visualModel
            model: taskmanager.Applet.dataModel
'''
WORKSPACE_GROUP = '''            // DeepWin: exibir somente os itens da área de trabalho atual.
            groups: [DelegateModelGroup { id: deepwinShown; name: "deepwinShown"; includeByDefault: true }]
            filterOnGroup: "deepwinShown"
'''
WORKSPACE_ANCHOR = '    function blendColorAlpha(fallback) {\n'
WORKSPACE_LOGIC = '''    // DeepWin: aplicativos não fixados aparecem apenas na área de trabalho em
    // que têm janelas. Sem dados do rastreador, o dock mostra todos os itens.
    property var deepwinWorkspaces: null
    property string deepwinWorkspaceText: ""
    function deepwinVisible(model) {
        const data = deepwinWorkspaces
        if (!data || model.attention || model.windows.length === 0)
            return true
        for (const win of model.windows) {
            const desktop = data.windows[win]
            if (desktop === undefined || desktop === -1 || desktop === data.current)
                return true
        }
        // O papel "docked" do modelo global não reflete a fixação; consultar a lista do dock.
        return (deepwinDockConfig.dockedElements || []).indexOf("desktop/" + model.itemId) !== -1
    }
    function deepwinFilter() {
        for (let i = 0; i < visualModel.items.count; i++) {
            const item = visualModel.items.get(i)
            const shown = deepwinVisible(item.model)
            if (item.inDeepwinShown !== shown)
                item.inDeepwinShown = shown
        }
    }
    // indexAt() devolve posições do grupo filtrado; as movimentações usam o grupo completo.
    function deepwinItemsIndex(index) {
        return index < 0 || index >= deepwinShown.count ? index : deepwinShown.get(index).itemsIndex
    }
    Timer {
        interval: 250
        running: true
        repeat: true
        onTriggered: {
            const request = new XMLHttpRequest()
            request.onreadystatechange = function() {
                if (request.readyState !== XMLHttpRequest.DONE)
                    return
                const text = request.responseText || ""
                if (text === taskmanager.deepwinWorkspaceText)
                    return
                taskmanager.deepwinWorkspaceText = text
                try {
                    taskmanager.deepwinWorkspaces = text ? JSON.parse(text) : null
                } catch (error) {
                    taskmanager.deepwinWorkspaces = null
                }
                taskmanager.deepwinFilter()
            }
            request.open("GET", @STATE@)
            request.send()
        }
    }
    D.Config {
        id: deepwinDockConfig
        name: "org.deepin.ds.dock.taskmanager"
        subpath: ""
        property var dockedElements: []
        onDockedElementsChanged: taskmanager.deepwinFilter()
    }
    Connections {
        target: visualModel.items
        function onChanged() { taskmanager.deepwinFilter() }
    }
    Connections {
        target: taskmanager.Applet.dataModel
        function onDataChanged() { taskmanager.deepwinFilter() }
    }

'''
WORKSPACE_TARGETS = ('appContainer.indexAt(drag.x, drag.y)', 'appContainer.indexAt(drop.x, drop.y)')


class DockPreviewError(RuntimeError):
    pass


def patch_qml(source):
    required = ('function onEntered()', 'id: previewTimer', 'previewTimer.start()',
                'taskmanager.Applet.requestPreview(root.modelIndex, Panel.rootObject, xOffset, yOffset, Panel.position);')
    if source.count(ORIGINAL) != 1 or any(value not in source for value in required):
        raise DockPreviewError('Esta versão do dock não corresponde à integração de prévias suportada.')
    return source.replace(ORIGINAL, REPLACEMENT, 1)


def patch_taskmanager(source, state):
    targets = ['let targetIndex = ' + call for call in WORKSPACE_TARGETS]
    anchors = [WORKSPACE_MODEL, WORKSPACE_ANCHOR] + targets
    if (any(source.count(value) != 1 for value in anchors) or 'filterOnGroup' in source
            or 'import org.deepin.dtk 1.0 as D' not in source):
        raise DockPreviewError('Esta versão do dock não corresponde à integração por área de trabalho suportada.')
    logic = WORKSPACE_LOGIC.replace('@STATE@', json.dumps(Path(state).as_uri()))
    source = source.replace(WORKSPACE_MODEL, WORKSPACE_MODEL + WORKSPACE_GROUP, 1)
    source = source.replace(WORKSPACE_ANCHOR, logic + WORKSPACE_ANCHOR, 1)
    for target, call in zip(targets, WORKSPACE_TARGETS):
        source = source.replace(target, 'let targetIndex = taskmanager.deepwinItemsIndex(' + call + ')', 1)
    return source


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
                 config_home=None, host_root=None, runtime_dir=None):
        self.home = Path(home or Path.home())
        self.data_home = Path(data_home or os.environ.get('XDG_DATA_HOME', self.home / '.local/share'))
        self.system_dir = resolve_system_dir(system_dir, host_root)
        self.local_dir = self.data_home / 'dde-shell' / PLUGIN
        config = Path(config_home or os.environ.get('XDG_CONFIG_HOME', self.home / '.config'))
        self.dropin = config / 'systemd/user' / (SERVICE + '.d') / '50-deepwin-preview.conf'
        self.unit = config / 'systemd/user' / TRACKER
        self.helper = Path(helper or self.data_home / APP_ID / 'gui/dock_preview.py')
        runtime = Path(runtime_dir or os.environ.get('XDG_RUNTIME_DIR', '/run/user/%d' % os.getuid()))
        self.state = runtime / APP_ID / 'dock-workspaces.json'

    def source(self, features=('preview',)):
        try:
            sources = {name: (self.system_dir / name).read_text()
                       for name in ('AppItem.qml', 'TaskManager.qml')}
            metadata = json.loads((self.system_dir / 'metadata.json').read_text())
            if metadata['Plugin']['Id'] != PLUGIN or metadata['Plugin']['Url'] != 'TaskManager.qml':
                raise ValueError()
            self.patched(sources, features)
            return sources
        except (OSError, ValueError, KeyError) as error:
            raise DockPreviewError('Dock dde-shell compatível não encontrado.') from error

    def patched(self, sources, features):
        result = {}
        if 'preview' in features:
            result['AppItem.qml'] = patch_qml(sources['AppItem.qml'])
        if 'workspace' in features:
            result['TaskManager.qml'] = patch_taskmanager(sources['TaskManager.qml'], self.state)
        return result

    def owned(self):
        if not self.local_dir.exists() and not self.local_dir.is_symlink():
            return None
        if self.local_dir.is_symlink():
            raise DockPreviewError('Já existe uma personalização do dock. Preserve-a antes de ativar este recurso.')
        try:
            marker = json.loads((self.local_dir / MARKER).read_text())
            if marker.get('owner') != APP_ID or marker.get('format') not in (1, 2):
                raise ValueError()
            # O formato 1 antecede o filtro por área de trabalho e só aplicava a prévia.
            features = marker.get('features', ['preview']) if marker['format'] == 2 else ['preview']
            if not features or set(features) - set(FEATURES):
                raise ValueError()
            if marker['files'] != tree_hashes(self.local_dir):
                raise ValueError()
            marker['features'] = features
            return marker
        except (OSError, ValueError, KeyError) as error:
            raise DockPreviewError('O pacote local do dock contém personalizações. Nenhum arquivo foi removido.') from error

    def features(self):
        marker = self.owned()
        return set(marker['features']) if marker else set()

    def dropin_text(self, features=('preview',), helper=None):
        path = str(helper or self.helper).replace('%', '%%')
        lines = ['# Gerenciado pelo DeepWin']
        if 'workspace' in features:
            lines += ['[Unit]', 'Wants=' + TRACKER, '[Service]',
                      # O QML lê o estado das áreas por XMLHttpRequest em file://.
                      'Environment=QML_XHR_ALLOW_FILE_READ=1']
        else:
            lines.append('[Service]')
        lines.append('ExecStartPre=-/usr/bin/python3 ' + json.dumps(path, ensure_ascii=False) + ' refresh')
        return '\n'.join(lines) + '\n'

    def unit_text(self, helper=None):
        path = str(helper or self.helper).replace('%', '%%')
        return ('# Gerenciado pelo DeepWin\n[Unit]\nDescription=DeepWin: áreas de trabalho para o dock\n'
                'PartOf=' + SERVICE + '\n\n[Service]\nExecStart=/usr/bin/python3 ' +
                json.dumps(path, ensure_ascii=False) + ' track\nRestart=on-failure\nRestartSec=2\n')

    def helpers(self):
        return (self.helper, self.data_home / APP_ID / 'gui/dock_preview.py')

    def check_dropin(self):
        accepted = {self.dropin_text(combo, helper) for helper in self.helpers()
                    for size in (1, 2) for combo in itertools.combinations(FEATURES, size)}
        if self.dropin.is_symlink() or (self.dropin.exists() and self.dropin.read_text() not in accepted):
            raise DockPreviewError('O ajuste de inicialização do dock foi personalizado. Preserve-o antes de continuar.')

    def check_unit(self):
        accepted = {self.unit_text(helper) for helper in self.helpers()}
        if self.unit.is_symlink() or (self.unit.exists() and self.unit.read_text() not in accepted):
            raise DockPreviewError('O serviço de áreas de trabalho do dock foi personalizado. Preserve-o antes de continuar.')

    def build(self, features):
        sources = self.source(features)
        self.data_home.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.deepwin-preview-', dir=self.data_home) as temporary:
            stage = Path(temporary) / PLUGIN
            shutil.copytree(self.system_dir, stage)
            for name, text in self.patched(sources, features).items():
                (stage / name).write_text(text)
            marker = {'owner': APP_ID, 'format': 2, 'features': sorted(features),
                      'source_files': tree_hashes(self.system_dir), 'files': tree_hashes(stage)}
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

    def configure(self, enabled, feature='preview', reload=True):
        if feature not in FEATURES:
            raise DockPreviewError('Ajuste do dock desconhecido.')
        current = self.features()
        self.check_dropin()
        self.check_unit()
        wanted = current | {feature} if enabled else current - {feature}
        if wanted:
            if not self.helper.is_file():
                raise DockPreviewError('Instale o DeepWin antes de ativar a integração com o dock.')
            self.build(wanted)
            self.dropin.parent.mkdir(parents=True, exist_ok=True)
            self.dropin.write_text(self.dropin_text(wanted))
        else:
            if self.local_dir.exists():
                shutil.rmtree(self.local_dir)
            self.dropin.unlink(missing_ok=True)
        if 'workspace' in wanted:
            self.unit.write_text(self.unit_text())
        elif self.unit.exists():
            if reload:
                subprocess.run(['systemctl', '--user', 'stop', TRACKER],
                               capture_output=True, text=True, timeout=10)
            self.unit.unlink()
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
            self.source(marker['features'])
            if tree_hashes(self.system_dir) != marker['source_files']:
                self.build(marker['features'])
        except (DockPreviewError, OSError, ValueError):
            # Em atualizações incompatíveis, carregar o pacote original do sistema.
            self.owned()
            shutil.rmtree(self.local_dir)
            raise DockPreviewError('O dock foi atualizado e os ajustes do DeepWin foram suspensos por compatibilidade.')

    def capture(self, feature='preview'):
        return {'enabled': feature in self.features()}

    def status(self, feature='preview'):
        marker = self.owned()
        self.check_dropin()
        self.check_unit()
        self.source((feature,))
        result = {'enabled': bool(marker) and feature in marker['features'], 'available': True}
        if marker and marker['source_files'] != tree_hashes(self.system_dir):
            result['note'] = 'O ajuste será atualizado ao recarregar a barra de tarefas.'
        elif feature == 'workspace' and os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            result['note'] = 'O filtro por área de trabalho funciona apenas em sessões X11.'
        return result


class _PropertyEvent(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                ('display', ctypes.c_void_p), ('window', ctypes.c_ulong), ('atom', ctypes.c_ulong),
                ('time', ctypes.c_ulong), ('state', ctypes.c_int)]


class _Event(ctypes.Union):
    _fields_ = [('type', ctypes.c_int), ('xproperty', _PropertyEvent), ('pad', ctypes.c_long * 24)]


class WorkspaceTracker:
    """Publica a área atual e a área de cada janela para o QML do dock (X11/EWMH)."""
    PROPERTY_NOTIFY = 28
    PROPERTY_CHANGE_MASK = 1 << 22
    ALL_DESKTOPS = 0xFFFFFFFF

    def __init__(self, path):
        self.path = Path(path)
        self.text = None
        self.watched = set()
        x = self.x = ctypes.CDLL('libX11.so.6')
        x.XOpenDisplay.restype = ctypes.c_void_p
        x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x.XDefaultRootWindow.restype = ctypes.c_ulong
        x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x.XInternAtom.restype = ctypes.c_ulong
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XSelectInput.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long]
        x.XGetWindowProperty.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long, ctypes.c_int,
            ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong))]
        x.XFree.argtypes = [ctypes.c_void_p]
        x.XPending.argtypes = [ctypes.c_void_p]
        x.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        x.XConnectionNumber.argtypes = [ctypes.c_void_p]
        x.XFlush.argtypes = [ctypes.c_void_p]
        self.display = x.XOpenDisplay(None)
        if not self.display:
            raise DockPreviewError('Sessão X11 indisponível para acompanhar as áreas de trabalho.')
        # Janelas podem desaparecer entre a lista de clientes e a leitura (BadWindow).
        self.on_error = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)(lambda display, event: 0)
        x.XSetErrorHandler(self.on_error)
        self.root = x.XDefaultRootWindow(self.display)
        self.current_atom, self.clients_atom, self.desktop_atom = (
            x.XInternAtom(self.display, name, 0)
            for name in (b'_NET_CURRENT_DESKTOP', b'_NET_CLIENT_LIST', b'_NET_WM_DESKTOP'))
        x.XSelectInput(self.display, self.root, self.PROPERTY_CHANGE_MASK)

    def cardinals(self, window, atom):
        kind, size, count, remaining = ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong()
        data = ctypes.POINTER(ctypes.c_ulong)()
        status = self.x.XGetWindowProperty(self.display, window, atom, 0, 65536, 0, 0, ctypes.byref(kind),
                                           ctypes.byref(size), ctypes.byref(count), ctypes.byref(remaining),
                                           ctypes.byref(data))
        if status != 0 or not data:
            return []
        try:
            # Propriedades de 32 bits chegam como long; descartar a extensão de sinal.
            return [data[index] & 0xFFFFFFFF for index in range(count.value)] if size.value == 32 else []
        finally:
            self.x.XFree(data)

    def snapshot(self):
        clients = self.cardinals(self.root, self.clients_atom)
        windows = {}
        for window in clients:
            if window not in self.watched:
                self.x.XSelectInput(self.display, window, self.PROPERTY_CHANGE_MASK)
            desktop = self.cardinals(window, self.desktop_atom)
            if desktop:
                windows[str(window)] = -1 if desktop[0] == self.ALL_DESKTOPS else desktop[0]
        self.watched = set(clients)
        current = self.cardinals(self.root, self.current_atom)
        return {'current': current[0] if current else 0, 'windows': windows}

    def publish(self, values):
        text = json.dumps(values, sort_keys=True, separators=(',', ':'))
        if text == self.text:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.path.with_name('.' + self.path.name + '.tmp')
        temporary.write_text(text)
        os.replace(temporary, self.path)
        self.text = text

    def run(self):
        relevant = {self.current_atom, self.clients_atom, self.desktop_atom}
        event = _Event()
        descriptor = self.x.XConnectionNumber(self.display)
        changed = True
        try:
            while True:
                while self.x.XPending(self.display):
                    self.x.XNextEvent(self.display, ctypes.byref(event))
                    if event.type == self.PROPERTY_NOTIFY and event.xproperty.atom in relevant:
                        changed = True
                if changed:
                    self.publish(self.snapshot())
                    changed = False
                self.x.XFlush(self.display)
                select.select([descriptor], [], [])
        finally:
            # Sem estado publicado, o dock volta a exibir todos os aplicativos.
            self.path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('refresh', 'status', 'track'))
    parser.add_argument('--feature', choices=FEATURES, default='preview')
    args = parser.parse_args()
    try:
        manager = DockPreview()
        if args.command == 'refresh':
            manager.refresh()
        elif args.command == 'track':
            signal.signal(signal.SIGTERM, lambda number, frame: sys.exit(0))
            WorkspaceTracker(manager.state).run()
        else:
            print(json.dumps(manager.status(args.feature), ensure_ascii=False))
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
