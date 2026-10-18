#!/bin/sh
# Executado somente na imagem descartável de testes, sem dados do usuário host.
set -eu
# A imagem não tem display: o smoke test usa o plugin offscreen.
export QT_QPA_PLATFORM=offscreen
for tool in cmake g++ ansible-playbook git; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf 'FAIL ferramenta de desenvolvimento instalada: %s\n' "$tool"
        exit 1
    fi
done
printf 'PASS execução sem Git, SDK, compilador ou Ansible\n'
/usr/bin/deepwin --version
QT_QPA_PLATFORM=offscreen dbus-run-session -- /usr/bin/deepwin --smoke-test
printf 'PASS GUI abre sem integrações opcionais na imagem limpa\n'
if test -e /root/.local/state/devedu.deepin-configs/originals.json; then
    printf 'FAIL abrir a GUI alterou backups\n'
    exit 1
fi
/usr/bin/python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, '/usr/lib/deepwin/gui')
from resources import Resources
resource = Resources()
runtime = resource.ensure()
assert (runtime/'gui/backend.py').is_file()
state = Path.home()/'.local/state/devedu.deepin-configs'
state.mkdir(parents=True, mode=0o700)
(state/'originals.json').write_text('{"clipboard":{"active":false,"enabled":"disabled"}}')
PY
before=$(sha256sum /root/.local/state/devedu.deepin-configs/originals.json)
dpkg -i /tmp/deepwin-package.deb
test "$before" = "$(sha256sum /root/.local/state/devedu.deepin-configs/originals.json)"
printf 'PASS reinstalação preserva backup e runtime\n'
apt-get remove -y devedu.deepin-configs
test ! -e /usr/bin/deepwin
test "$before" = "$(sha256sum /root/.local/state/devedu.deepin-configs/originals.json)"
/root/.local/share/devedu.deepin-configs/runtime/current/bin/deepwin-restore --help
printf 'PASS remoção preserva backup e comando independente de restauração\n'
