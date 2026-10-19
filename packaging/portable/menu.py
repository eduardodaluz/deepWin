#!/usr/bin/env python3
"""Explicit per-user menu integration for an extracted DeepWin directory.

Usage: python3 portable-menu.py {register,unregister} /absolute/extracted/root
No module import or application launch registers a menu entry.
"""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


DESKTOP_NAME = "devedu.deepin-configs-portable.desktop"
APPLICATION = "devedu.deepin-configs"
MARKER_NAME = "portable-menu.json"


class MenuError(Exception):
    """A conflict or unsafe path which requires the user's intervention."""


def _directory(path, create=False):
    """Reject symlinks, including ancestors, before touching user data."""
    if not path.is_absolute():
        raise MenuError("O diretório XDG deve ser um caminho absoluto.")
    for component in reversed((path, *path.parents)):
        if not component.exists() and not component.is_symlink():
            if create:
                component.mkdir(mode=0o700)
            else:
                return False
        info = component.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise MenuError(f"Diretório inseguro (link ou arquivo): {component}")
    return True


def _read(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MenuError(f"Não foi possível ler com segurança: {path}") from exc
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise MenuError(f"Arquivo inseguro ou de outro usuário: {path}")
        if info.st_size > 65536:
            raise MenuError(f"Arquivo existente inesperado: {path}")
        return stream.read()


def _write(path, data, mode):
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _exec_argument(value):
    # Exec has two escaping layers: Desktop Entry strings, then Exec arguments.
    # Percent is an Exec field-code introducer even inside quoted arguments.
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise MenuError("O caminho do portátil contém caracteres de controle.")
    escaped = "".join("\\" + char if char in '\\"`$' else
                      "%%" if char == "%" else char for char in value)
    return '"' + escaped.replace("\\", "\\\\") + '"'


def desktop_entry(root):
    executable = _exec_argument(str(root / "deepwin"))
    return ("[Desktop Entry]\n"
            "Type=Application\n"
            "Name=DeepWin (portátil)\n"
            "Comment=Configure Deepin desktop features\n"
            "Comment[pt_BR]=Configure os recursos do desktop Deepin\n"
            # GLib checks the first executable before expanding %% field codes;
            # env keeps paths with literal percent signs launchable as well.
            f"Exec=/usr/bin/env {executable}\n"
            "Icon=preferences-system\n"
            "Terminal=false\n"
            "Categories=Settings;DesktopSettings;\n"
            "StartupNotify=true\n"
            "StartupWMClass=deepwin\n"
            "X-DeepWin-Portable=true\n").encode("utf-8")


def _owned(marker_data, desktop_data):
    if marker_data is None:
        if desktop_data is not None:
            raise MenuError("A entrada de menu já existe sem registro de propriedade; preservada.")
        return None
    try:
        marker = json.loads(marker_data)
        if (marker["schema"] != 1 or marker["application"] != APPLICATION
                or marker["desktop"] != DESKTOP_NAME
                or not isinstance(marker["root"], str)
                or not Path(marker["root"]).is_absolute()
                or not isinstance(marker["sha256"], str)
                or len(marker["sha256"]) != 64
                or any(char not in "0123456789abcdef" for char in marker["sha256"])):
            raise ValueError("invalid marker")
    except (ValueError, KeyError, TypeError) as exc:
        raise MenuError("O registro de propriedade do menu é inválido; arquivos preservados.") from exc
    if desktop_data is not None and _digest(desktop_data) != marker["sha256"]:
        raise MenuError("A entrada de menu foi personalizada; arquivos preservados.")
    return marker


def manage(action, root, environ=None):
    """Register/update or remove only the marker-backed portable menu entry."""
    if action not in ("register", "unregister"):
        raise ValueError(action)
    environ = os.environ if environ is None else environ
    root = Path(root).resolve()
    if action == "register":
        launcher = root / "deepwin"
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            raise MenuError(f"Launcher portátil ausente ou sem permissão de execução: {launcher}")
        contents = desktop_entry(root)
    home = Path(environ.get("HOME") or Path.home())
    data_home = Path(environ.get("XDG_DATA_HOME") or home / ".local/share")
    applications = data_home / "applications"
    metadata = data_home / APPLICATION
    # Unregister on a clean account must not create directories or lock files.
    if action == "unregister":
        if not _directory(metadata) or not _directory(applications):
            return "Nenhuma entrada de menu portátil registrada."
    else:
        _directory(metadata, create=True)
        _directory(applications, create=True)

    lock_path = metadata / "portable-menu.lock"
    try:
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise MenuError(f"Não foi possível bloquear o registro: {lock_path}") from exc
    with os.fdopen(lock_fd, "r+") as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise MenuError(f"Arquivo de bloqueio inseguro: {lock_path}")
        fcntl.flock(lock, fcntl.LOCK_EX)
        desktop = applications / DESKTOP_NAME
        marker_path = metadata / MARKER_NAME
        previous = _read(desktop)
        marker = _owned(_read(marker_path), previous)
        if action == "unregister":
            if marker is None:
                return "Nenhuma entrada de menu portátil registrada."
            if marker["root"] != str(root):
                raise MenuError("O menu pertence a outra pasta portátil; execute a remoção nessa pasta.")
            if previous is not None:
                desktop.unlink()
            marker_path.unlink()
            return "Entrada de menu portátil removida; preferências e backups preservados."

        record = {"schema": 1, "application": APPLICATION, "desktop": DESKTOP_NAME,
                  "root": str(root), "sha256": _digest(contents)}
        _write(desktop, contents, 0o644)
        try:
            _write(marker_path, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode(), 0o600)
        except OSError:
            if previous is None:
                desktop.unlink()
            else:
                _write(desktop, previous, 0o644)
            raise
    # The .desktop file is sufficient; avoid triggering desktop session services.
    return ("Entrada de menu portátil registrada. Após mover a pasta, execute ./register-menu novamente. "
            "Se o menu não atualizar imediatamente, encerre e inicie a sessão.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "unregister"))
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args(argv)
    try:
        print(manage(arguments.action, arguments.root))
    except (MenuError, OSError) as exc:
        print(f"DeepWin: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
