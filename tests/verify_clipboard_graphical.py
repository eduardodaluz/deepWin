#!/usr/bin/python3
"""Teste manual automatizado na sessão Deepin; abre duas janelas descartáveis.

Executar com o serviço de autopaste parado. Nunca imprime o conteúdo colado.
"""

import argparse
from pathlib import Path
import subprocess
import tempfile

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import dbus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    executable = Path(__file__).resolve().parents[1] / 'bin' / 'deepin-clipboard-autopaste'
    log = tempfile.TemporaryFile(mode='w+')
    command = ['/usr/bin/python3', str(executable), '--diagnose']
    if args.dry_run:
        command.append('--dry-run')
    observer = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    windows, editors = [], []
    for title in ('Origem', 'Destino alternativo'):
        window = Gtk.Window(title='Teste de colagem Deepin — ' + title)
        window.set_default_size(500, 220)
        editor = Gtk.TextView()
        window.add(editor)
        window.show_all()
        windows.append(window)
        editors.append(editor)
    bus = dbus.SessionBus()
    clip = dbus.Interface(bus.get_object('org.deepin.dde.Clipboard1',
        '/org/deepin/dde/Clipboard1'), 'org.deepin.dde.Clipboard1')
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    sentinel = 'Teste Deepin: ação\nsegunda linha'
    results = []
    expected = '' if args.dry_run else sentinel

    def xdo(*arguments):
        subprocess.run(['xdotool', *arguments], check=True, timeout=3)

    def activate(index):
        xdo('windowactivate', '--sync', str(windows[index].get_window().get_xid()))
        editors[index].grab_focus()

    def text(index=0):
        buffer = editors[index].get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

    def check(name, condition):
        results.append(bool(condition))
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)

    def schedule(delay, callback):
        def wrapped():
            try:
                if observer.poll() is not None:
                    raise RuntimeError('O observador encerrou antes do fim do teste')
                callback()
            except Exception as error:
                check(type(error).__name__, False)
                finish()
            return False
        GLib.timeout_add(delay, wrapped)

    def reset():
        editors[0].get_buffer().set_text('')
        editors[1].get_buffer().set_text('')
        activate(0)

    def first():
        reset()
        clipboard.set_text(sentinel, -1)
        schedule(700, lambda: open_and_confirm('Return', after_first))

    def open_and_confirm(key, after):
        clip.Show()
        schedule(700, lambda: press(key, after))

    def press(key, after):
        xdo('key', key)
        schedule(1500, after)

    def after_first():
        check('Enter: texto com acentos e várias linhas', text() == expected)
        reset()
        schedule(250, lambda: open_and_confirm('KP_Enter', after_second))

    def after_second():
        check('Enter numérico: selecionar o mesmo item novamente', text() == expected)
        reset()
        # Criar um item mais novo e selecionar o anterior pelas setas.
        clipboard.set_text('Outro item temporário do teste Deepin', -1)
        schedule(700, older)

    def older():
        clip.Show()
        schedule(700, lambda: press('Down', older_confirm))

    def older_confirm():
        # Down sozinho não deve colar nem fechar o histórico.
        check('Seta não cola', not text())
        xdo('key', 'Return')
        schedule(1500, after_older)

    def after_older():
        check('Selecionar item antigo', text() == expected)
        reset()
        schedule(250, lambda: open_and_confirm('Escape', after_escape))

    def after_escape():
        clip.Hide()
        check('Escape não cola', not text())
        reset()
        schedule(250, switch_open)

    def switch_open():
        clip.Show()
        schedule(700, switch_confirm)

    def switch_confirm():
        xdo('key', 'Return')
        schedule(100, lambda: activate(1))
        schedule(1500, after_switch)

    def after_switch():
        check('Trocar janela durante a espera cancela', not text(0) and not text(1))
        reset()
        xdo('key', 'Return')
        schedule(300, after_regular_enter)

    def after_regular_enter():
        check('Enter fora do histórico continua normal', text() == '\n')
        reset()
        schedule(250, hold_open)

    def hold_open():
        clip.Show()
        schedule(700, hold_confirm)

    def hold_confirm():
        xdo('keydown', 'Return')
        schedule(900, lambda: xdo('keyup', 'Return'))
        schedule(2200, after_hold)

    def after_hold():
        check('Enter segurado não duplica a colagem',
              text().count(sentinel) == (0 if args.dry_run else 1))
        finish()

    def finish():
        try:
            clip.Hide()
        finally:
            observer.terminate()
            observer.wait(timeout=5)
            log.seek(0)
            diagnostics = log.read()
            confirmations = diagnostics.count('SIMULAÇÃO: colaria') if args.dry_run else diagnostics.count('Ctrl+V enviado')
            check('Quatro colagens autorizadas no total', confirmations == 4)
            print(diagnostics, end='')
            for window in windows:
                window.destroy()
            Gtk.main_quit()

    schedule(700, first)
    try:
        Gtk.main()
    finally:
        if observer.poll() is None:
            observer.terminate()
            observer.wait(timeout=5)
        log.close()
    return 0 if results and all(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
