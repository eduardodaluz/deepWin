#!/usr/bin/python3
"""Testa um switch e o diálogo de restauração da GUI instalada na sessão real.

Executar com a sessão desbloqueada, a janela fechada e sem alterações pendentes no painel.
O estado da colagem é restaurado no finally mesmo se a interação falhar.
"""
import importlib.util
from pathlib import Path
import subprocess
import time


def main():
    lock = subprocess.run(
        ['xdotool', 'search', '--onlyvisible', '--class', r'^org\.deepin\.dde\.lock$'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if lock.returncode == 0:
        raise RuntimeError('Desbloqueie a sessão do Deepin antes deste teste de interação.')
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('native_config_backend', root / 'gui/backend.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager = module.Manager()
    if manager.load_state():
        raise RuntimeError('Há alterações pendentes no painel; restaure-as antes deste teste.')
    original = manager.capture('clipboard')
    if not original['active']:
        raise RuntimeError('Este teste requer o serviço de colagem inicialmente ativo.')

    def xdo(*arguments):
        return subprocess.check_output(['xdotool', *map(str, arguments)], text=True, timeout=6).strip()

    def wait_for(condition):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.1)
        raise RuntimeError('A interação não atingiu o estado esperado.')

    pointer = dict(line.split('=', 1) for line in xdo('getmouselocation', '--shell').splitlines())
    process = subprocess.Popen([str(Path.home() / '.local/bin/deepwin')],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    window = None
    try:
        time.sleep(0.6)
        if process.poll() is not None:
            raise RuntimeError('Feche a GUI existente antes deste teste.')
        window = xdo('search', '--sync', '--onlyvisible', '--pid', process.pid).splitlines()[-1]
        xdo('windowactivate', '--sync', window)
        geometry = dict(line.split('=', 1) for line in xdo('getwindowgeometry', '--shell', window).splitlines())
        width, height = int(geometry['WIDTH']), int(geometry['HEIGHT'])
        time.sleep(0.6)
        xdo('mousemove', '--window', window, width - 75, 255, 'click', 1)
        wait_for(lambda: not manager.feature_status('clipboard')['enabled'])
        assert 'clipboard' in manager.load_state()
        print('PASS switch DTK desativa a colagem e preserva o estado original', flush=True)
        # O serviço muda antes de o controlador devolver os oito estados à GUI.
        # Aguardar a reabilitação dos botões antes de clicar em Restaurar.
        time.sleep(0.7)
        xdo('mousemove', '--window', window, width - 130, height - 32, 'click', 1)
        time.sleep(0.7)
        xdo('key', 'Return')
        wait_for(lambda: manager.capture('clipboard') == original and not manager.load_state())
        print('PASS diálogo DTK restaura a colagem e limpa a alteração pendente', flush=True)
        return 0
    finally:
        manager.restore_value('clipboard', original)
        if 'clipboard' in manager.load_state():
            manager.restore('clipboard')
        if window is not None and process.poll() is None:
            xdo('windowclose', window)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
        xdo('mousemove', pointer['X'], pointer['Y'])


if __name__ == '__main__':
    raise SystemExit(main())
