"""Bootstrap de módulos Python, ferramentas do host e extração de pydeps."""
import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gui'))
import backend
import dock_preview
from dock_preview import DockPreview, PLUGIN

_loader = SourceFileLoader('extract_pydeps', str(ROOT / 'packaging' / 'extract-pydeps'))
_spec = importlib.util.spec_from_loader('extract_pydeps', _loader)
extract_pydeps = importlib.util.module_from_spec(_spec)
_loader.exec_module(extract_pydeps)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)

    def test_missing_pydeps_directory_makes_no_changes(self):
        path_snapshot = list(sys.path)
        env_snapshot = os.environ.get('GI_TYPELIB_PATH')
        dirs_snapshot = os.environ.get('XDG_DATA_DIRS')
        host = self.home / 'hostroot'
        with patch.object(backend, 'HOST_ROOT', str(host)):
            backend.bootstrap_runtime_python(root=str(self.home / 'absente'))
        self.assertEqual(sys.path, path_snapshot)
        self.assertEqual(os.environ.get('GI_TYPELIB_PATH'), env_snapshot)
        self.assertEqual(os.environ.get('XDG_DATA_DIRS'), dirs_snapshot)

    def test_host_root_share_dirs_are_prepended_inside_sandbox(self):
        host = self.home / 'rootfs'
        (host / 'usr/share').mkdir(parents=True)
        (host / 'var/lib/linglong/entries/share').mkdir(parents=True)
        before = os.environ.get('XDG_DATA_DIRS')
        try:
            with patch.object(backend, 'HOST_ROOT', str(host)):
                backend.bootstrap_runtime_python(root=str(self.home / 'absente'))
            expected = ':'.join([str(host / 'usr/share'),
                                 str(host / 'var/lib/linglong/entries/apps/share'),
                                 str(host / 'var/lib/linglong/entries/share'),
                                 before or '/usr/local/share:/usr/share'])
            self.assertEqual(os.environ.get('XDG_DATA_DIRS'), expected)
        finally:
            if before is None:
                os.environ.pop('XDG_DATA_DIRS', None)
            else:
                os.environ['XDG_DATA_DIRS'] = before

    def test_pydeps_tree_is_registered_for_imports(self):
        base = self.home / 'pydeps'
        (base / 'dist-packages').mkdir(parents=True)
        (base / 'lib').mkdir(parents=True)
        (base / 'lib' / 'libdeepwin-fake.so.9').write_bytes(b'not an elf file')
        (base / 'girepository-1.0').mkdir(parents=True)
        env_before = os.environ.get('GI_TYPELIB_PATH')
        dirs_before = os.environ.get('XDG_DATA_DIRS')
        try:
            with patch.object(backend, 'HOST_ROOT', str(self.home / 'hostroot')):
                backend.bootstrap_runtime_python(root=str(self.home))
            self.assertEqual(sys.path[0], str(base / 'dist-packages'))
            expected = str(base / 'girepository-1.0')
            if env_before:
                expected = expected + os.pathsep + env_before
            self.assertEqual(os.environ.get('GI_TYPELIB_PATH'), expected)
            self.assertEqual(os.environ.get('XDG_DATA_DIRS'), dirs_before)
        finally:
            sys.path.remove(str(base / 'dist-packages'))
            if env_before is None:
                os.environ.pop('GI_TYPELIB_PATH', None)
            else:
                os.environ['GI_TYPELIB_PATH'] = env_before
            if dirs_before is None:
                os.environ.pop('XDG_DATA_DIRS', None)
            else:
                os.environ['XDG_DATA_DIRS'] = dirs_before

    def test_host_tool_prefers_host_root_and_falls_back_to_path(self):
        host = self.home / 'hostroot'
        (host / 'usr' / 'bin').mkdir(parents=True)
        (host / 'usr' / 'bin' / 'deepwin-tool').write_bytes(b'#!/bin/sh\n')
        class _Stub:
            pass
        found = backend.Native.host_tool(_Stub(), 'deepwin-tool', host_root=str(host))
        self.assertEqual(found, str(host / 'usr' / 'bin' / 'deepwin-tool'))
        missing = backend.Native.host_tool(_Stub(), 'deepwin-absent', host_root=str(host))
        self.assertEqual(missing, __import__('shutil').which('deepwin-absent'))


class DockHostRootTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        # O caminho primário é absoluto e existe na máquina de desenvolvimento;
        # o teste o redireciona para o temporário para exercitar a ordem.
        self.original = dock_preview.SYSTEM_PLUGIN_DIR
        self.system = self.home / 'sys' / PLUGIN
        dock_preview.SYSTEM_PLUGIN_DIR = str(self.system)
        self.addCleanup(setattr, dock_preview, 'SYSTEM_PLUGIN_DIR', self.original)

    def test_host_root_source_is_preferred_when_system_path_is_absent(self):
        host = self.home / 'rootfs'
        plugin = host / 'usr/share/dde-shell' / PLUGIN
        plugin.mkdir(parents=True)
        (plugin / 'AppItem.qml').write_text('import QtQuick\n')
        self.assertEqual(dock_preview.resolve_system_dir(host_root=str(host)), plugin)
        preview = DockPreview(home=self.home, data_home=self.home / 'data',
                              config_home=self.home / 'config', host_root=str(host))
        self.assertEqual(preview.system_dir, plugin)

    def test_default_system_path_is_kept_when_nothing_exists(self):
        # Nada existe: vale o primeiro candidato (o caminho primário pacheado).
        self.assertEqual(dock_preview.resolve_system_dir(host_root=str(self.home / 'vazio')),
                         self.system)
        self.assertEqual(dock_preview.resolve_system_dir(), self.system)
        # Sem patch, o primário volta a ser o caminho padrão do sistema.
        self.assertEqual(dock_preview.resolve_system_dir(system_dir=str(self.original)),
                         Path(self.original))

    def test_explicit_system_dir_wins_over_host_root(self):
        explicit = self.home / 'custom'
        explicit.mkdir()
        self.assertEqual(dock_preview.resolve_system_dir(str(explicit), host_root=str(self.home)),
                         explicit)


class ExtractPydepsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)

    def test_source_mapping_rejects_unknown_prefixes(self):
        self.assertEqual(extract_pydeps.source_for('pydeps/lib/x.so.1.0'),
                         'usr/lib/x86_64-linux-gnu/x.so.1.0')
        with self.assertRaises(SystemExit):
            extract_pydeps.source_for('pydeps/outro/x')

    def test_entries_are_installed_dereferencing_symlinks(self):
        # install_entries espera a raiz que contém usr/ (como o temporary do main).
        packages = self.home / 'usr/lib/python3/dist-packages/dbus'
        packages.mkdir(parents=True)
        (packages / '__init__.py').write_text('# dbus\n')
        typelib = self.home / 'usr/lib/x86_64-linux-gnu/girepository-1.0'
        typelib.mkdir(parents=True)
        (typelib / 'GLib-2.0.typelib').write_bytes(b'typelib')
        lib = self.home / 'usr/lib/x86_64-linux-gnu'
        (lib / 'libgirepository-1.0.so.1.0.0').write_bytes(b'elf')
        (lib / 'libgirepository-1.0.so.1').symlink_to('libgirepository-1.0.so.1.0.0')
        entries = ['pydeps/dist-packages/dbus/__init__.py',
                   'pydeps/girepository-1.0/GLib-2.0.typelib',
                   'pydeps/lib/libgirepository-1.0.so.1.0.0']
        destination = self.home / 'pydeps'
        count = extract_pydeps.install_entries(entries, self.home, destination)
        self.assertEqual(count, 3)
        self.assertEqual((destination / 'dist-packages' / 'dbus' / '__init__.py').read_text(), '# dbus\n')
        self.assertEqual((destination / 'girepository-1.0' / 'GLib-2.0.typelib').read_bytes(), b'typelib')
        self.assertEqual((destination / 'lib' / 'libgirepository-1.0.so.1.0.0').read_bytes(), b'elf')

    def test_missing_entry_fails_listing_all_names(self):
        (self.home / 'usr/lib/python3/dist-packages').mkdir(parents=True)
        entries = ['pydeps/dist-packages/ausente.py',
                   'pydeps/dist-packages/tambem-ausente.py']
        with self.assertRaises(SystemExit) as failure:
            extract_pydeps.install_entries(entries, self.home, self.home / 'pydeps')
        self.assertIn('ausente.py', str(failure.exception))
        self.assertIn('tambem-ausente.py', str(failure.exception))


if __name__ == '__main__':
    unittest.main()
