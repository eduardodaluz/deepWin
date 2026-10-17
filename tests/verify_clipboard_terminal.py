#!/usr/bin/python3
"""Valida Win+V e Enter num terminal temporário, com o serviço ativo.

O terminal executa apenas um leitor de bytes, sem shell ou execução da colagem.
"""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import textwrap
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal', choices=('deepin-terminal', 'kitty', 'alacritty'),
                        default='deepin-terminal')
    args = parser.parse_args()
    expected = 'Colagem no terminal: ação áé 2026'.encode()
    result = [1]

    def windows():
        found = subprocess.run(['xdotool', 'search', '--onlyvisible', '--class',
                                '^' + args.terminal + '$'], capture_output=True, text=True)
        return set(found.stdout.split())

    with tempfile.TemporaryDirectory(prefix='deepin-clipboard-terminal-') as directory:
        work = Path(directory)
        receiver = work / 'receive'
        receiver.write_text('#!/usr/bin/python3\n' + textwrap.dedent(f'''
            import os, select, termios, time, tty
            from pathlib import Path
            work = Path({str(work)!r})
            work.joinpath('pid').write_text(str(os.getpid()))
            fd = 0
            saved = termios.tcgetattr(fd)
            received = b''
            try:
                tty.setraw(fd)
                work.joinpath('ready').touch()
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    if select.select([fd], [], [], 0.2)[0]:
                        received += os.read(fd, 4096)
                        if {expected!r} in received:
                            break
                work.joinpath('received').write_bytes(received)
            finally:
                termios.tcsetattr(fd, termios.TCSANOW, saved)
        '''))
        receiver.chmod(0o755)
        previous = windows()
        command = [args.terminal, str(receiver)]
        if args.terminal != 'kitty':
            command.insert(1, '-e')
        output = tempfile.TemporaryFile()
        process = subprocess.Popen(command, stdout=output, stderr=output)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        started = time.monotonic()

        def finish():
            print(('PASS ' if result[0] == 0 else 'FAIL ') + args.terminal +
                  ': Win+V e Enter colam uma única vez usando o serviço', flush=True)
            Gtk.main_quit()
            return False

        def xdo(*arguments):
            subprocess.run(['xdotool', *arguments], check=True, timeout=3)

        def confirm():
            xdo('key', 'Return')
            GLib.timeout_add(100, check)
            return False

        def open_history():
            xdo('key', 'Super_L+v')
            GLib.timeout_add(700, confirm)
            return False

        def check():
            received = work / 'received'
            if received.exists():
                result[0] = 0 if received.read_bytes() == expected else 1
                return finish()
            if time.monotonic() - started > 14:
                return finish()
            return True

        def prepare():
            new_windows = windows() - previous
            if new_windows and (work / 'ready').exists():
                xdo('windowactivate', '--sync', sorted(new_windows)[0])
                clipboard.set_text(expected.decode(), -1)
                GLib.timeout_add(700, open_history)
                return False
            if time.monotonic() - started > 8:
                return finish()
            return True

        GLib.timeout_add(100, prepare)
        try:
            Gtk.main()
        finally:
            pid_file = work / 'pid'
            if pid_file.exists():
                try:
                    os.kill(int(pid_file.read_text()), signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Um terminal pode compartilhar seu processo com outras janelas.
                # Encerrar apenas o leitor é suficiente para fechar a aba de teste.
                pass
            output.close()
    return result[0]


if __name__ == '__main__':
    raise SystemExit(main())
