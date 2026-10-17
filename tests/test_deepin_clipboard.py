"""Testes das condições que autorizam ou cancelam uma colagem."""

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch


path = Path(__file__).resolve().parents[1] / 'bin' / 'deepin-clipboard-autopaste'
loader = importlib.machinery.SourceFileLoader('clipboard_autopaste', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)


class ShortcutTests(unittest.TestCase):
    def test_installed_terminals_use_shift(self):
        for classes in (b'deepin-terminal\0deepin-terminal\0',
                        b'Alacritty\0Alacritty\0', b'kitty\0kitty\0'):
            with self.subTest(classes=classes):
                self.assertEqual(module.paste_shortcut(classes), 'ctrl+shift+v')

    def test_terminal_class_still_works_with_custom_instance_name(self):
        self.assertEqual(module.paste_shortcut(b'minha-sessao\0Deepin-Terminal\0'),
                         'ctrl+shift+v')

    def test_everyday_apps_and_missing_class_keep_ctrl_v(self):
        for classes in (None, b'', b'brave-browser\0Brave-browser\0',
                        b'code\0Code\0', b'editor\0Editor\0'):
            with self.subTest(classes=classes):
                self.assertEqual(module.paste_shortcut(classes), 'ctrl+v')

    def test_terminal_word_inside_another_class_is_not_a_match(self):
        self.assertEqual(module.paste_shortcut(b'deepin-terminal-settings\0Editor\0'),
                         'ctrl+v')


class AttemptTests(unittest.TestCase):
    def attempt(self):
        return module.Attempt(target=42, deadline=2, selected=True, hidden=True)

    def test_requires_selection_and_history_closed_in_either_order(self):
        for missing in ('selected', 'hidden'):
            attempt = self.attempt()
            setattr(attempt, missing, False)
            self.assertEqual(attempt.ready(1, 42, True, True), 'wait')

    def test_requires_stable_focus_then_authorizes_paste(self):
        attempt = self.attempt()
        self.assertEqual(attempt.ready(1, 42, True, True), 'wait')
        self.assertEqual(attempt.ready(1.02, 42, True, True), 'wait')
        self.assertEqual(attempt.ready(1.05, 42, True, True), 'paste')

    def test_another_window_cancels_even_after_selection(self):
        self.assertEqual(self.attempt().ready(1, 99, True, True), 'cancel')

    def test_temporary_no_focus_waits(self):
        self.assertEqual(self.attempt().ready(1, 0, False, True), 'wait')

    def test_focus_must_be_inside_destination(self):
        self.assertEqual(self.attempt().ready(1, 42, False, True), 'wait')

    def test_held_enter_or_modifier_resets_stability(self):
        attempt = self.attempt()
        attempt.ready(1, 42, True, True)
        self.assertEqual(attempt.ready(1.05, 42, True, False), 'wait')
        self.assertIsNone(attempt.stable_since)
        self.assertEqual(attempt.ready(1.1, 42, True, True), 'wait')
        self.assertEqual(attempt.ready(1.15, 42, True, True), 'paste')

    def test_expiration_cancels_even_if_conditions_are_ready(self):
        attempt = self.attempt()
        attempt.ready(1, 42, True, True)
        self.assertEqual(attempt.ready(2, 42, True, True), 'cancel')


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.app = module.Application.__new__(module.Application)
        self.app.attempt = module.Attempt(42, deadline=2)
        self.app.target = 42

    def test_other_key_cancels_pending_paste(self):
        self.app.key_press('Escape', 0, 0, '')
        self.assertIsNone(self.app.attempt)

    def test_repeated_enter_keeps_single_attempt(self):
        attempt = self.app.attempt
        self.app.key_press('Return', 0, 0, '')
        self.app.key_press('KP_Enter', 0, 0, '')
        self.assertIs(self.app.attempt, attempt)

    def test_click_cancels(self):
        self.app.button_press(1, 0, 0, '')
        self.assertIsNone(self.app.attempt)

    def test_closing_without_confirmation_does_not_arm(self):
        self.app.attempt = None
        self.app.refresh_active = Mock()
        self.app.args = Mock(diagnose=False)
        self.app.visibility(False)
        self.assertIsNone(self.app.attempt)
        self.assertEqual(self.app.target, 0)

    def test_paste_runs_once_and_never_forces_window_activation(self):
        self.app.attempt.selected = self.app.attempt.hidden = True
        self.app.attempt.stable_since = 1
        self.app.timer = 1
        self.app.clip_window = 100
        self.app.x = Mock()
        self.app.x.active.return_value = 42
        self.app.x.focused_on.return_value = True
        self.app.x.keys_up.return_value = True
        self.app.args = Mock(dry_run=False)
        self.app.drain_events = Mock()
        self.app.refresh_active = Mock(return_value=42)
        for classes, shortcut in ((b'editor\0Editor\0', 'ctrl+v'),
                                  (b'deepin-terminal\0deepin-terminal\0', 'ctrl+shift+v')):
            with self.subTest(shortcut=shortcut):
                self.app.attempt = module.Attempt(42, 2, True, True, 1)
                self.app.x.prop.return_value = classes
                with patch.object(module.time, 'monotonic', return_value=1.5), \
                        patch.object(module.subprocess, 'run') as run:
                    run.return_value.returncode = 0
                    self.assertFalse(self.app.tick())
                    self.assertFalse(self.app.tick())
                    run.assert_called_once()
                    self.assertEqual(run.call_args.args[0],
                                     ['xdotool', 'key', '--delay', '12', shortcut])

    def test_last_moment_focus_change_prevents_sending(self):
        self.app.attempt.selected = self.app.attempt.hidden = True
        self.app.attempt.stable_since = 1
        self.app.timer = 1
        self.app.clip_window = 100
        self.app.x = Mock()
        self.app.x.active.return_value = 99
        self.app.args = Mock(dry_run=False)
        self.app.drain_events = Mock()
        self.app.refresh_active = Mock(return_value=42)
        with patch.object(module.time, 'monotonic', return_value=1.5), \
                patch.object(module.subprocess, 'run') as run:
            self.assertFalse(self.app.tick())
            run.assert_not_called()

    def test_send_failure_releases_attempt_and_timer(self):
        self.app.attempt.selected = self.app.attempt.hidden = True
        self.app.attempt.stable_since = 1
        self.app.timer = 1
        self.app.clip_window = 100
        self.app.x = Mock()
        self.app.x.active.return_value = 42
        self.app.x.focused_on.return_value = True
        self.app.x.keys_up.return_value = True
        self.app.args = Mock(dry_run=False)
        self.app.drain_events = Mock()
        self.app.refresh_active = Mock(return_value=42)
        with patch.object(module.time, 'monotonic', return_value=1.5), \
                patch.object(module.subprocess, 'run', side_effect=OSError('teste')):
            with self.assertLogs(module.LOG, level='ERROR'):
                self.assertFalse(self.app.tick())
            self.assertIsNone(self.app.attempt)
            self.assertEqual(self.app.timer, 0)


if __name__ == '__main__':
    unittest.main()
