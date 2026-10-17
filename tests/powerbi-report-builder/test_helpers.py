"""Synthetic tests: python -m unittest discover -s tests/powerbi-report-builder -v"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'skills/powerbi-report-builder/scripts'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load('pbir_validator', SCRIPTS / 'validate.py')
warning = load('warning_handler', SCRIPTS / 'confirm-source-warning.py')


class ValidatorTests(unittest.TestCase):
    def test_json_and_hidden_platform(self):
        with tempfile.TemporaryDirectory(prefix='PBIR files ') as folder:
            path = Path(folder) / '.platform'
            path.write_text('{"a": 1, "a": 2}', encoding='utf-8')
            self.assertTrue(any('duplicate' in e for e in validator.validate_file(path)))
            path.write_text('{broken}', encoding='utf-8')
            self.assertTrue(any('invalid JSON' in e for e in validator.validate_file(path)))

    def test_bom_conflict_and_valid_unicode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'visual.json'
            path.write_bytes(b'\xef\xbb\xbf{}')
            self.assertTrue(any('BOM' in e for e in validator.validate_file(path)))
            path.write_text('{"title":"Sales \u2013 Worldwide"}', encoding='utf-8')
            self.assertEqual([], validator.validate_file(path))
            path = Path(folder) / 'model.tmdl'
            path.write_text('<<<<<<< branch\ntable Sales', encoding='utf-8')
            self.assertTrue(any('conflict' in e for e in validator.validate_file(path)))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_changed_files_preserve_unicode_spaces_and_whitespace(self):
        with tempfile.TemporaryDirectory(prefix='PBIR git ') as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, capture_output=True, check=True)
            git('init', '-b', 'main')
            (root / 'initial.json').write_text('{}', encoding='utf-8')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
            path = root / 'report \u00e9 data.json'
            path.write_text('{}', encoding='utf-8')
            self.assertIn(path, validator.changed_files('HEAD', root))


class WarningMatcherTests(unittest.TestCase):
    names = ['This file uses multiple data sources. Information may be shared.', 'Do you want to open this file?']

    def test_exact_supported_body_and_controls(self):
        warning.validate_warning(self.names, [('OK', True), ('Cancel', True)])

    def test_other_dialog_or_inaccessible_body_is_rejected(self):
        for names in [[], ['Are you sure?'], ['This file uses multiple data sources.']]:
            with self.assertRaises(RuntimeError):
                warning.validate_warning(names, [('OK', True), ('Cancel', True)])

    def test_ambiguous_missing_or_disabled_buttons_rejected(self):
        for buttons in [[('OK', True)], [('OK', False), ('Cancel', True)], [('OK', True), ('OK', True), ('Cancel', True)]]:
            with self.assertRaises(RuntimeError):
                warning.validate_warning(self.names, buttons)


@unittest.skipUnless(shutil.which('node'), 'Node required')
class ReloadGuardTests(unittest.TestCase):
    def run_fixture(self, unsaved, *flags):
        with tempfile.TemporaryDirectory(prefix='PBIR reload ') as folder:
            root = Path(folder)
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(SCRIPTS / 'pbir-reload.mjs', scripts / 'pbir-reload.mjs')
            package = root / '.runtime/node/node_modules/@microsoft/powerbi-desktop-bridge-cli'
            (package / 'dist').mkdir(parents=True)
            (package / 'package.json').write_text('{"type":"module"}', encoding='utf-8')
            marker = root / 'reload-called.json'
            stub = '''import fs from 'node:fs';
export const METHODS = {reload:'fixture.reload'};
export const isDesktopBridgeError = () => false;
export const openSession = async () => ({
 getApplicationState: async () => (STATE),
 connection:{client:{sendBridgeMethod:async (method,args) => {fs.writeFileSync(MARKER, JSON.stringify(args));return {success:true};}}},
 dispose: () => {}
});'''
            state = {'currentFilePath': 'fixture.Report/definition.pbir'}
            if unsaved != 'unknown':
                state['hasUnsavedChanges'] = unsaved
            stub = stub.replace('STATE', json.dumps(state)).replace('MARKER', json.dumps(str(marker)))
            (package / 'dist/index.js').write_text(stub, encoding='utf-8')
            result = subprocess.run(['node', str(scripts / 'pbir-reload.mjs'), '123', *flags], capture_output=True, text=True)
            return result, json.loads(marker.read_text()) if marker.exists() else None

    def test_unsaved_and_unknown_state_block_bridge_call(self):
        for state in [True, 'unknown']:
            result, called = self.run_fixture(state)
            self.assertNotEqual(0, result.returncode)
            self.assertIsNone(called)
            self.assertIn('unsaved', result.stderr)

    def test_clean_state_calls_report_only_reload(self):
        result, called = self.run_fixture(False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({'reloadModelDefinition': False}, called)

    def test_explicit_override_and_model_flag(self):
        result, called = self.run_fixture(True, '--allow-unsaved', '--model')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({'reloadModelDefinition': True}, called)


if __name__ == '__main__':
    unittest.main()
