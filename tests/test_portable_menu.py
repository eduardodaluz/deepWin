"""Safety of optional portable menu integration, without a desktop session."""

import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portable_menu", ROOT / "packaging/portable/menu.py")
menu = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(menu)


class PortableMenuTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.data = self.home / "xdg data"
        self.environ = {"HOME": str(self.home), "XDG_DATA_HOME": str(self.data)}
        self.bundle = self.make_bundle("portable directory")
        self.desktop = self.data / "applications" / menu.DESKTOP_NAME
        self.marker = self.data / menu.APPLICATION / menu.MARKER_NAME

    def make_bundle(self, name):
        root = self.home / name
        root.mkdir()
        launcher = root / "deepwin"
        launcher.write_text("#!/bin/sh\nexit 0\n")
        launcher.chmod(0o755)
        return root

    def manage(self, action="register", root=None):
        return menu.manage(action, root or self.bundle, environ=self.environ)

    def test_no_import_side_effects_and_clean_unregister(self):
        self.assertFalse(self.data.exists())
        self.manage("unregister")
        self.assertFalse(self.data.exists())

    def test_registration_is_explicit_idempotent_and_points_at_extraction(self):
        self.manage()
        first = self.desktop.read_bytes()
        self.manage()
        self.assertEqual(self.desktop.read_bytes(), first)
        self.assertIn(f'Exec=/usr/bin/env "{self.bundle}/deepwin"', first.decode())
        record = json.loads(self.marker.read_text())
        self.assertEqual(record["root"], str(self.bundle))
        self.assertEqual(record["sha256"], menu._digest(first))
        self.assertEqual(self.desktop.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)
        self.manage("unregister")
        self.manage("unregister")
        self.assertFalse(self.desktop.exists())
        self.assertFalse(self.marker.exists())

    def test_unrelated_launchers_backups_and_runtime_are_preserved(self):
        self.desktop.parent.mkdir(parents=True)
        other = self.desktop.parent / "devedu.deepin-configs.desktop"
        other.write_text("custom system-package launcher")
        runtime = self.data / menu.APPLICATION / "runtime/current/bin"
        runtime.mkdir(parents=True)
        helper = runtime / "deepwin-restore"
        helper.write_bytes(b"persisted helper")
        backup = self.data / menu.APPLICATION / "originals.json"
        backup.write_text('{"original": true}')
        self.manage()
        self.manage("unregister")
        self.assertEqual(other.read_text(), "custom system-package launcher")
        self.assertEqual(helper.read_bytes(), b"persisted helper")
        self.assertEqual(backup.read_text(), '{"original": true}')

    def test_unowned_collision_is_preserved_on_register_and_unregister(self):
        self.desktop.parent.mkdir(parents=True)
        self.desktop.write_text("custom launcher")
        for action in ("register", "unregister"):
            with self.subTest(action=action), self.assertRaises(menu.MenuError):
                self.manage(action)
            self.assertEqual(self.desktop.read_text(), "custom launcher")
            self.assertFalse(self.marker.exists())

    def test_modified_owned_launcher_is_preserved(self):
        self.manage()
        custom = self.desktop.read_bytes() + b"X-Custom=true\n"
        self.desktop.write_bytes(custom)
        before = self.marker.read_bytes()
        for action in ("register", "unregister"):
            with self.subTest(action=action), self.assertRaises(menu.MenuError):
                self.manage(action)
            self.assertEqual(self.desktop.read_bytes(), custom)
            self.assertEqual(self.marker.read_bytes(), before)

    def test_move_and_explicit_reregistration(self):
        self.manage()
        moved = self.bundle.with_name("moved with spaces")
        self.bundle.rename(moved)
        with self.assertRaises(menu.MenuError):
            self.manage("unregister", moved)
        self.manage(root=moved)
        self.assertIn(f'Exec=/usr/bin/env "{moved}/deepwin"', self.desktop.read_text())
        with self.assertRaises(menu.MenuError):
            self.manage("unregister", self.bundle)
        self.manage("unregister", moved)
        self.assertFalse(self.desktop.exists())

    def test_readonly_bundle_and_home_default(self):
        self.environ.pop("XDG_DATA_HOME")
        self.bundle.chmod(0o555)
        self.addCleanup(self.bundle.chmod, 0o755)
        self.manage()
        desktop = self.home / ".local/share/applications" / menu.DESKTOP_NAME
        self.assertTrue(desktop.is_file())
        self.assertEqual(sorted(path.name for path in self.bundle.iterdir()), ["deepwin"])
        self.manage("unregister")

    def test_relative_xdg_directory_is_rejected(self):
        self.environ["XDG_DATA_HOME"] = "relative-path"
        with self.assertRaises(menu.MenuError):
            self.manage()

    def test_symlink_directory_is_rejected_without_following_it(self):
        actual = self.home / "actual"
        actual.mkdir()
        self.data.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(menu.MenuError):
            self.manage()
        self.assertEqual(list(actual.iterdir()), [])

    def test_symlink_desktop_and_marker_are_preserved(self):
        for subject in (self.desktop, self.marker):
            with self.subTest(subject=subject):
                self.desktop.parent.mkdir(parents=True, exist_ok=True)
                self.marker.parent.mkdir(parents=True, exist_ok=True)
                actual = self.home / "custom-file"
                actual.write_text("custom user data")
                subject.symlink_to(actual)
                with self.assertRaises(menu.MenuError):
                    self.manage()
                self.assertTrue(subject.is_symlink())
                self.assertEqual(actual.read_text(), "custom user data")
                subject.unlink()

    def test_invalid_marker_is_preserved(self):
        self.manage()
        content = self.desktop.read_bytes()
        self.marker.write_text("not JSON")
        for action in ("register", "unregister"):
            with self.subTest(action=action), self.assertRaises(menu.MenuError):
                self.manage(action)
            self.assertEqual(self.desktop.read_bytes(), content)
            self.assertEqual(self.marker.read_text(), "not JSON")

    def test_missing_owned_entry_can_be_registered_again_or_removed(self):
        self.manage()
        self.desktop.unlink()
        self.manage()
        self.assertTrue(self.desktop.exists())
        self.desktop.unlink()
        self.manage("unregister")
        self.assertFalse(self.marker.exists())

    def test_marker_write_failure_restores_previous_launcher(self):
        self.manage()
        old = self.desktop.read_bytes()
        marker = self.marker.read_bytes()
        another = self.make_bundle("another directory")
        real_write = menu._write

        def fail_marker(path, data, mode):
            if path == self.marker:
                raise OSError("simulated marker failure")
            return real_write(path, data, mode)

        with patch.object(menu, "_write", side_effect=fail_marker):
            with self.assertRaises(OSError):
                self.manage(root=another)
        self.assertEqual(self.desktop.read_bytes(), old)
        self.assertEqual(self.marker.read_bytes(), marker)

    def test_exec_roundtrip_for_spaces_and_reserved_characters(self):
        root = self.make_bundle('spaces "quotes" \\ slash $cash `ticks` %f é')
        self.manage(root=root)
        text = self.desktop.read_text()
        command = next(line[5:] for line in text.splitlines() if line.startswith("Exec="))
        self.assertTrue(command.startswith("/usr/bin/env "))
        value = command[len("/usr/bin/env "):]
        # First decode Desktop Entry escapes, then Exec quoting, then the %%
        # literal field-code escape. No shell is involved when launching a menu.
        escapes = {"s": " ", "n": "\n", "t": "\t", "r": "\r", "\\": "\\"}
        decoded = re.sub(r"\\([sntr\\])", lambda match: escapes[match[1]], value)
        self.assertTrue(decoded.startswith('"') and decoded.endswith('"'))
        argument = re.sub(r'\\(["`$\\])', lambda match: match[1], decoded[1:-1])
        self.assertEqual(argument.replace("%%", "%"), str(root / "deepwin"))
        self.assertNotIn("\nPath=", text)

    def test_control_characters_in_root_are_rejected(self):
        root = self.make_bundle("newline\nin path")
        with self.assertRaises(menu.MenuError):
            self.manage(root=root)
        self.assertFalse(self.data.exists())

    def test_missing_launcher_does_not_create_xdg_data(self):
        (self.bundle / "deepwin").unlink()
        with self.assertRaises(menu.MenuError):
            self.manage()
        self.assertFalse(self.data.exists())


if __name__ == "__main__":
    unittest.main()
