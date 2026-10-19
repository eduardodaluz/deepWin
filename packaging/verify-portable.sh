#!/bin/sh
# Executado somente na imagem descartável, sem diretórios pessoais do host.
set -eu
phase=$1
bundle=$2
export HOME=/home/portable-test
export XDG_DATA_HOME="$HOME/dados isolados"
export XDG_CONFIG_HOME="$HOME/config isolada"
export XDG_STATE_HOME="$HOME/estado isolado"
export XDG_CACHE_HOME="$HOME/cache isolado"
export XDG_RUNTIME_DIR="$HOME/runtime isolado"
export PYTHONDONTWRITEBYTECODE=1
export QT_QPA_PLATFORM=offscreen

if [ "$phase" = root ]; then
    for tool in cmake g++ ansible-playbook git; do
        if command -v "$tool" >/dev/null 2>&1; then
            printf 'FAIL ferramenta de desenvolvimento instalada: %s\n' "$tool"
            exit 1
        fi
    done
    if dpkg-query -W -f='${Status}' devedu.deepin-configs 2>/dev/null | grep -q 'install ok installed'; then
        printf 'FAIL pacote DeepWin instalado na imagem de teste\n'
        exit 1
    fi
    mkdir -p '/opt/extração portátil' "$XDG_RUNTIME_DIR"
    chown portable-test:portable-test "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
    tar -xJf /tmp/portable.tar.xz -C '/opt/extração portátil'
    source="/opt/extração portátil/$bundle"
    # O usuário de teste não pode escrever no aplicativo nem no seu diretório pai.
    chmod -R a-w "$source"
    runuser -u portable-test -- /bin/sh "$0" initial "$source"
    moved='/opt/extração portátil/aplicativo movido %f "quotes" $cash `ticks` \ barra'
    mv "$source" "$moved"
    runuser -u portable-test -- /bin/sh "$0" moved "$moved"
    rm -rf "$moved"
    runuser -u portable-test -- /bin/sh "$0" removed "$source"
    printf 'PASS execução portátil sem pacote instalado, SDK ou compilador\n'
    exit 0
fi

test "$(id -u)" != 0
cd /tmp
resource="$bundle/lib/deepwin"
runtime="$XDG_DATA_HOME/devedu.deepin-configs/runtime/current"

check_menu_launch() {
    /usr/bin/python3 - "$bundle" <<'PY'
import os
from pathlib import Path
import sys
import tempfile
from gi.repository import Gio, GLib

desktop = Path(os.environ['XDG_DATA_HOME']) / 'applications/devedu.deepin-configs-portable.desktop'
keyfile = GLib.KeyFile.new()
keyfile.load_from_file(str(desktop), GLib.KeyFileFlags.NONE)
# Acrescentar --version em memória evita abrir outra GUI e preserva o launcher
# registrado no disco. O próprio GLib decodifica os dois níveis de escaping.
command = keyfile.get_string('Desktop Entry', 'Exec')
keyfile.set_string('Desktop Entry', 'Exec', command + ' --version')
entry = Gio.DesktopAppInfo.new_from_keyfile(keyfile)
assert entry is not None
assert entry.get_executable() == '/usr/bin/env'
pids = []
def launched(app, pid, data):
    pids.append(pid)
with tempfile.TemporaryFile() as output:
    assert entry.launch_uris_as_manager_with_fds(
        [], None, GLib.SpawnFlags.DO_NOT_REAP_CHILD, None, None,
        launched, None, -1, output.fileno(), output.fileno())
    assert pids, 'GLib não iniciou o processo do menu'
    for pid in pids:
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0, status
        GLib.spawn_close_pid(pid)
    output.seek(0)
    result = output.read().decode()
version = (Path(sys.argv[1]) / 'lib/deepwin/VERSION').read_text().strip()
assert version in result, result
assert (desktop.parent / 'unrelated.desktop').read_text() == 'entrada de outro aplicativo\n'
print('PASS launcher do menu executado pelo GLib:', result.strip())
PY
}

if [ "$phase" = initial ]; then
    test ! -w "$bundle"
    "$bundle/register-menu" --help
    test ! -e "$XDG_DATA_HOME/devedu.deepin-configs/portable-menu.json"
    test ! -e "$XDG_DATA_HOME/applications/devedu.deepin-configs-portable.desktop"
    "$bundle/unregister-menu" --help
    test ! -e "$XDG_DATA_HOME/devedu.deepin-configs"
    "$bundle/deepwin" --version
    /usr/bin/python3 - "$resource" <<'PY'
import ctypes
from pathlib import Path
import sys
plugin = Path(sys.argv[1]) / 'qt6/plugins/generic/libdeepwin-calculator.so'
ctypes.CDLL(str(plugin))
print('PASS plugin decimal carrega com bibliotecas nativas do Deepin')
PY
    # Consulta real no backend, antes de qualquer criação de runtime ou backup.
    /usr/bin/python3 - "$resource" <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys

roots = [Path(os.environ[name]) for name in ('XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CONFIG_HOME')]
def snapshot():
    return [(str(root), root.exists(), sorted((str(p.relative_to(root)), p.read_bytes())
            for p in root.rglob('*') if p.is_file())) for root in roots]
before = snapshot()
result = subprocess.run(['dbus-run-session', '--', '/usr/bin/python3',
                         str(Path(sys.argv[1]) / 'gui/backend.py'), 'status'],
                        capture_output=True, text=True, check=False)
assert result.returncode == 0, result.stdout + result.stderr
assert json.loads(result.stdout)['ok'], result.stdout
assert before == snapshot(), 'Consultar status alterou dados, configuração ou backups'
print('PASS consultar status não altera estado')
PY
    dbus-run-session -- "$bundle/deepwin" --smoke-test
    test ! -e "$XDG_STATE_HOME/devedu.deepin-configs/originals.json"
    test ! -e "$XDG_DATA_HOME/devedu.deepin-configs/runtime/current"
    test ! -e "$XDG_DATA_HOME/applications/devedu.deepin-configs-portable.desktop"
    printf 'PASS GUI offscreen sem criar backup ou runtime\n'
    # Registrar o menu é uma ação explícita; abrir o aplicativo não registra.
    mkdir -p "$XDG_DATA_HOME/applications"
    printf 'entrada de outro aplicativo\n' > "$XDG_DATA_HOME/applications/unrelated.desktop"
    "$bundle/register-menu"
    "$bundle/register-menu"
    check_menu_launch
    /usr/bin/python3 - "$resource" <<'PY'
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'gui'))
from resources import Resources
resources = Resources()
runtime = resources.ensure()
assert (runtime / 'gui/backend.py').is_file()
resources.validate_release(runtime.resolve())
state = Path(os.environ['XDG_STATE_HOME']) / 'devedu.deepin-configs'
state.mkdir(parents=True, mode=0o700, exist_ok=True)
(state / 'originals.json').write_text('{"clipboard":{"active":false,"enabled":"disabled"}}')
schema = state / 'schema.json'
schema.write_text('{"format":1,"app_id":"devedu.deepin-configs"}')
prior_schema = schema.read_bytes()
schema.write_text('{"format":999,"app_id":"devedu.deepin-configs"}')
protected = {path: path.read_bytes() for path in (state / 'originals.json', schema)}
try:
    result = subprocess.run(['dbus-run-session', '--', '/usr/bin/python3',
                             str(Path(sys.argv[1]) / 'gui/backend.py'), 'status'],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0, 'O backend aceitou formato de estado futuro'
    assert 'Formato de estado incompatível' in result.stdout, result.stdout + result.stderr
    assert all(path.read_bytes() == contents for path, contents in protected.items()), \
        'A recusa de formato futuro alterou backup ou schema'
finally:
    schema.write_bytes(prior_schema)
print('PASS schema futuro recusado com mensagem e backups preservados')
PY
    sha256sum "$XDG_STATE_HOME/devedu.deepin-configs/originals.json" \
        "$XDG_STATE_HOME/devedu.deepin-configs/schema.json" > "$HOME/backup-checksums"
fi

if [ "$phase" = moved ]; then
    "$bundle/deepwin" --version
    dbus-run-session -- "$bundle/deepwin" --smoke-test
    /usr/bin/python3 - "$resource" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(sys.argv[1]) / 'gui'))
from resources import Resources
resources = Resources()
before = resources.current.resolve()
assert resources.ensure().resolve() == before, 'Mover o portátil mudou o runtime persistente'
PY
    printf 'PASS GUI e runtime preservados depois de mover o portátil\n'
    "$bundle/register-menu"
    check_menu_launch
    "$bundle/unregister-menu"
    "$bundle/unregister-menu"
    test ! -e "$XDG_DATA_HOME/applications/devedu.deepin-configs-portable.desktop"
    test ! -e "$XDG_DATA_HOME/devedu.deepin-configs/portable-menu.json"
    # Um launcher alheio no mesmo nome precisa sobreviver a registro e remoção.
    desktop="$XDG_DATA_HOME/applications/devedu.deepin-configs-portable.desktop"
    printf 'launcher personalizado\n' > "$desktop"
    if "$bundle/register-menu"; then
        printf 'FAIL registro sobrescreveu launcher personalizado\n'
        exit 1
    fi
    if "$bundle/unregister-menu"; then
        printf 'FAIL remoção aceitou launcher personalizado\n'
        exit 1
    fi
    test "$(cat "$desktop")" = 'launcher personalizado'
    test "$(cat "$XDG_DATA_HOME/applications/unrelated.desktop")" = 'entrada de outro aplicativo'
    rm "$desktop"
    printf 'PASS menu explícito, idempotente e preserva launchers de terceiros\n'
fi

if [ "$phase" = removed ]; then
    test ! -e "$bundle"
    /usr/bin/python3 - "$runtime" <<'PY'
import importlib.util
from pathlib import Path
import sys
runtime = Path(sys.argv[1])
sys.path.insert(0, str(runtime / 'gui'))
import backend, calculator_decimal, claude_versions, dock_preview, user_services
import dbus
from gi.repository import Gio, GLib
from resources import Resources
Resources(root=runtime).validate_release(runtime.resolve())
# Importa o helper sem iniciar monitoramento ou tocar no clipboard.
from importlib.machinery import SourceFileLoader
loader = SourceFileLoader('portable_clipboard', str(runtime / 'bin/deepin-clipboard-autopaste'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)
assert module.paste_shortcut(b'deepin-terminal') == 'ctrl+shift+v'
PY
    "$runtime/bin/deepwin-restore" --help
    "$runtime/bin/deepin-clipboard-autopaste" --help
    sha256sum --check "$HOME/backup-checksums"
    printf 'PASS helpers e restauração independentes da pasta portátil removida\n'
fi
