import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gui'))
import dock_preview as dock


SOURCE = '''import QtQuick 2.15
Item {
    function onEntered() { previewTimer.start() }
    Timer {
        id: previewTimer
        onTriggered: {
            taskmanager.Applet.requestPreview(root.modelIndex, Panel.rootObject, xOffset, yOffset, Panel.position);
        }
    }
    function activate() {
                TaskManager.requestActivate(index);
    }
}
'''

TASKMANAGER = '''import QtQuick 2.15
import org.deepin.dtk 1.0 as D
ContainmentItem {
    id: taskmanager
    function blendColorAlpha(fallback) {
        return fallback
    }
    OverflowContainer {
        id: appContainer
        model: DelegateModel {
            id: visualModel
            model: taskmanager.Applet.dataModel
        }
        DropArea {
            onPositionChanged: function(drag) {
                let targetIndex = appContainer.indexAt(drag.x, drag.y)
            }
            onDropped: function(drop) {
                let targetIndex = appContainer.indexAt(drop.x, drop.y)
            }
        }
    }
}
'''


class DockPreviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.system = self.home / 'system-package'
        self.system.mkdir()
        (self.system / 'metadata.json').write_text(json.dumps({'Plugin': {
            'Id': dock.PLUGIN, 'Url': 'TaskManager.qml', 'Parent': 'org.deepin.ds.dock'}}))
        (self.system / 'AppItem.qml').write_text(SOURCE)
        (self.system / 'TaskManager.qml').write_text(TASKMANAGER)
        self.helper = self.home / 'installed-helper.py'
        self.helper.write_text('helper')
        self.manager = dock.DockPreview(home=self.home, data_home=self.home / 'data',
                                       system_dir=self.system, helper=self.helper, config_home=self.home / '.config',
                                       runtime_dir=self.home / 'run')

    def test_status_does_not_write_and_patch_reuses_native_preview(self):
        self.assertFalse(self.manager.status()['enabled'])
        self.assertFalse(self.manager.data_home.exists())
        patched = dock.patch_qml(SOURCE)
        self.assertIn('if (root.windows.length > 1)', patched)
        self.assertIn('previewTimer.triggered()', patched)
        self.assertEqual(patched.count('TaskManager.requestActivate(index);'), 1)

    def test_unknown_source_is_rejected_without_creating_override(self):
        (self.system / 'AppItem.qml').write_text('unknown implementation')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(True, reload=False)
        self.assertFalse(self.manager.local_dir.exists())

    def test_enable_and_rollback_preserve_system_package(self):
        before = dock.tree_hashes(self.system)
        self.manager.configure(True, reload=False)
        self.assertTrue(self.manager.capture()['enabled'])
        self.assertIn('previewTimer.triggered()', (self.manager.local_dir / 'AppItem.qml').read_text())
        self.assertIn('ExecStartPre=-/usr/bin/python3', self.manager.dropin.read_text())
        self.assertEqual(dock.tree_hashes(self.system), before)
        self.manager.configure(False, reload=False)
        self.assertFalse(self.manager.local_dir.exists())
        self.assertFalse(self.manager.dropin.exists())
        self.assertEqual(dock.tree_hashes(self.system), before)

    def test_existing_user_override_is_preserved(self):
        self.manager.local_dir.mkdir(parents=True)
        custom = self.manager.local_dir / 'custom.qml'
        custom.write_text('personalization')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(True, reload=False)
        self.assertEqual(custom.read_text(), 'personalization')

    def test_edited_generated_package_is_never_deleted(self):
        self.manager.configure(True, reload=False)
        extra = self.manager.local_dir / 'custom.qml'
        extra.write_text('personalization')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(False, reload=False)
        self.assertTrue(extra.exists())
        self.assertTrue(self.manager.dropin.exists())

    def test_edited_service_dropin_is_preserved(self):
        self.manager.configure(True, reload=False)
        self.manager.dropin.write_text('custom unit settings')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(False, reload=False)
        self.assertEqual(self.manager.dropin.read_text(), 'custom unit settings')

    def test_package_symlink_is_not_followed_or_removed(self):
        self.manager.local_dir.parent.mkdir(parents=True)
        self.manager.local_dir.symlink_to(self.system, target_is_directory=True)
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(False, reload=False)
        self.assertTrue((self.system / 'AppItem.qml').exists())

    def test_refresh_rebuilds_from_updated_system_without_losing_native_resources(self):
        self.manager.configure(True, reload=False)
        (self.system / 'TaskManager.qml').write_text('updated native component')
        self.manager.refresh()
        self.assertEqual((self.manager.local_dir / 'TaskManager.qml').read_text(), 'updated native component')
        self.assertTrue(self.manager.status()['enabled'])

    def test_incompatible_update_falls_back_to_original_package(self):
        self.manager.configure(True, reload=False)
        (self.system / 'AppItem.qml').write_text('incompatible update')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.refresh()
        self.assertFalse(self.manager.local_dir.exists())
        # O prefixo '-' permite ao shell continuar com o pacote original.
        self.assertIn('ExecStartPre=-', self.manager.dropin.read_text())

    def test_reload_failure_is_reported_for_controller_rollback(self):
        with patch('dock_preview.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['systemctl'])):
            with self.assertRaises(dock.DockPreviewError):
                self.manager.configure(True)
        self.manager.configure(False, reload=False)
        self.assertFalse(self.manager.capture()['enabled'])

    def test_reloads_only_the_user_shell_service(self):
        with patch('dock_preview.subprocess.run') as run:
            self.manager.configure(True)
        self.assertEqual(run.call_args_list[0].args[0], ['systemctl', '--user', 'daemon-reload'])
        self.assertEqual(run.call_args_list[1].args[0], ['systemctl', '--user', 'restart', dock.SERVICE])

    def test_workspace_patch_filters_view_and_maps_drag_indexes(self):
        patched = dock.patch_taskmanager(TASKMANAGER, self.manager.state)
        self.assertIn('filterOnGroup: "deepwinShown"', patched)
        self.assertIn(json.dumps(self.manager.state.as_uri()), patched)
        self.assertIn('taskmanager.deepwinItemsIndex(appContainer.indexAt(drag.x, drag.y))', patched)
        self.assertIn('taskmanager.deepwinItemsIndex(appContainer.indexAt(drop.x, drop.y))', patched)
        with self.assertRaises(dock.DockPreviewError):
            dock.patch_taskmanager(patched, self.manager.state)

    def test_workspace_and_preview_share_package_and_disable_independently(self):
        self.manager.configure(True, reload=False)
        self.manager.configure(True, 'workspace', reload=False)
        self.assertEqual(self.manager.features(), {'preview', 'workspace'})
        self.assertIn('previewTimer.triggered()', (self.manager.local_dir / 'AppItem.qml').read_text())
        self.assertIn('deepwinShown', (self.manager.local_dir / 'TaskManager.qml').read_text())
        dropin = self.manager.dropin.read_text()
        self.assertIn('Wants=' + dock.TRACKER, dropin)
        self.assertIn('Environment=QML_XHR_ALLOW_FILE_READ=1', dropin)
        self.assertIn(' track\n', self.manager.unit.read_text())
        self.manager.configure(False, reload=False)
        self.assertEqual(self.manager.features(), {'workspace'})
        self.assertEqual((self.manager.local_dir / 'AppItem.qml').read_text(), SOURCE)
        self.assertTrue(self.manager.capture('workspace')['enabled'])
        self.manager.configure(False, 'workspace', reload=False)
        self.assertFalse(self.manager.local_dir.exists())
        self.assertFalse(self.manager.dropin.exists())
        self.assertFalse(self.manager.unit.exists())

    def test_disabling_workspace_keeps_preview_dropin_compatible(self):
        self.manager.configure(True, 'workspace', reload=False)
        self.manager.configure(True, reload=False)
        self.manager.configure(False, 'workspace', reload=False)
        self.assertEqual(self.manager.dropin.read_text(), self.manager.dropin_text())
        self.assertFalse(self.manager.unit.exists())
        self.assertEqual((self.manager.local_dir / 'TaskManager.qml').read_text(), TASKMANAGER)

    def test_legacy_preview_package_is_still_recognized(self):
        self.manager.configure(True, reload=False)
        marker_path = self.manager.local_dir / dock.MARKER
        marker = json.loads(marker_path.read_text())
        marker['format'] = 1
        del marker['features']
        marker_path.write_text(json.dumps(marker))
        self.assertEqual(self.manager.features(), {'preview'})
        self.manager.configure(True, 'workspace', reload=False)
        self.assertEqual(self.manager.features(), {'preview', 'workspace'})

    def test_unknown_taskmanager_rejects_only_workspace(self):
        (self.system / 'TaskManager.qml').write_text('unknown implementation')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(True, 'workspace', reload=False)
        self.assertFalse(self.manager.local_dir.exists())
        self.manager.configure(True, reload=False)
        self.assertTrue(self.manager.status()['enabled'])

    def test_edited_tracker_unit_is_preserved(self):
        self.manager.configure(True, 'workspace', reload=False)
        self.manager.unit.write_text('custom unit')
        with self.assertRaises(dock.DockPreviewError):
            self.manager.configure(False, 'workspace', reload=False)
        self.assertEqual(self.manager.unit.read_text(), 'custom unit')

    def test_disabling_workspace_stops_tracker_before_reload(self):
        self.manager.configure(True, 'workspace', reload=False)
        with patch('dock_preview.subprocess.run') as run:
            self.manager.configure(False, 'workspace')
        self.assertEqual(run.call_args_list[0].args[0], ['systemctl', '--user', 'stop', dock.TRACKER])

    @unittest.skipUnless(shutil.which('node'), 'Node necessário para executar o filtro JavaScript do QML')
    def test_workspace_visibility_rules(self):
        patched = dock.patch_taskmanager(TASKMANAGER, self.manager.state)
        start = patched.index('    function deepwinVisible(model) {')
        end = patched.index('    function deepwinFilter()')
        script = '''const deepwinWorkspaces = {current: 1, windows: {"10": 0, "11": 1, "12": -1}};
const deepwinDockConfig = {dockedElements: ["desktop/pinned"]};
''' + patched[start:end] + '''
const cases = [
 {itemId:"app", attention:false, windows:["10"]},
 {itemId:"app", attention:false, windows:["10","11"]},
 {itemId:"pinned", attention:false, windows:["10"]},
 {itemId:"app", attention:true, windows:["10"]},
 {itemId:"app", attention:false, windows:["12"]},
 {itemId:"app", attention:false, windows:["99"]},
 {itemId:"app", attention:false, windows:[]},
];
process.stdout.write(JSON.stringify(cases.map(deepwinVisible)));'''
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [False, True, True, True, True, True, True])

    @unittest.skipUnless(shutil.which('node'), 'Node necessário para executar o callback JavaScript do QML')
    def test_installed_native_click_handler_keeps_single_window_and_right_click_behavior(self):
        path = Path('/usr/share/dde-shell') / dock.PLUGIN / 'AppItem.qml'
        if not path.is_file():
            self.skipTest('Pacote nativo do dde-shell ausente')
        try:
            source = dock.patch_qml(path.read_text())
        except dock.DockPreviewError:
            self.skipTest('Versão nativa do dock fora da integração suportada')
        start = source.index('        onClicked: function (mouse) {')
        start = source.index('{', start) + 1
        end = source.index('\n        }\n\n        PanelToolTip', start)
        body = source[start:end]
        script = '''const body = JSON.parse(process.argv[1]);
const results = [];
for (const [count, button, longPress] of [[0,1,false],[1,1,false],[2,1,false],[3,1,false],[2,2,false],[2,1,true]]) {
 global.isTouchLongPressed = longPress;
 const events = [];
 global.root = {windows:Array(count),modelIndex:7,onEntered:()=>events.push('prepare')};
 global.previewTimer = {stop:()=>events.push('stop-timer'),triggered:()=>events.push('native-preview')};
 global.TaskManager = {requestActivate:()=>events.push('activate'),requestNewInstance:()=>events.push('launch')};
 global.launchAnimation = {start:()=>{}};
 global.Qt = {LeftButton:1,RightButton:2};
 global.requestAppItemMenu = ()=>events.push('context-menu');
 new Function('mouse', body)({button});
 results.push(events);
}
process.stdout.write(JSON.stringify(results));'''
        result = subprocess.run(['node', '-e', script, json.dumps(body)], capture_output=True, text=True, check=True)
        events = json.loads(result.stdout)
        self.assertEqual(events[0], ['launch'])
        self.assertEqual(events[1], ['activate'])
        self.assertEqual(events[2], ['prepare', 'stop-timer', 'native-preview'])
        self.assertEqual(events[3], events[2])
        self.assertEqual(events[4], ['context-menu'])
        self.assertEqual(events[5], [])


if __name__ == '__main__':
    unittest.main()
