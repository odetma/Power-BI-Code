"""Offline integration tests using synthetic PBIP content only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='metadata-installer-test-')
        self.root = Path(self.temp.name) / 'Example Repository'
        self.root.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Installer Test')
        self.git('config', 'user.email', 'test@example.invalid')
        report = self.root / 'Finance/Sample.Report'
        model = self.root / 'Finance/Shared.SemanticModel'
        report.mkdir(parents=True)
        (model / 'definition/tables').mkdir(parents=True)
        (report / 'definition.pbir').write_text(json.dumps({'datasetReference': {'byPath': {'path': '../Shared.SemanticModel'}}}))
        (model / 'definition/tables/Sample.tmdl').write_text('table Sample\n\t/// Line one\n\t/// Line two\n\tmeasure Amount =\n\t\t\tVAR x = 1\n\t\t\tRETURN x\n', encoding='utf-8')
        (self.root / '.gitignore').write_text('# Existing rules\nlocal-data/\n')
        self.git('add', '.')
        self.git('commit', '-m', 'Synthetic test fixture')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, capture_output=True, text=True, check=True).stdout.strip()

    def invoke(self, *args, package=PACKAGE):
        return subprocess.run([sys.executable, '-B', str(package / 'install.py'), '--repository', str(self.root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace')

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.relative_to(self.root).parts}

    def test_dry_run_is_read_only(self):
        before = self.snapshot()
        result = self.invoke('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Sources: Finance', result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_install_repeat_and_upgrade(self):
        head = self.git('rev-parse', 'HEAD')
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        config = json.loads((self.root / '.pbip-metadata/config.json').read_text())
        self.assertEqual(config['source_directories'], ['Finance'])
        self.assertFalse(config['service_enrichment'])
        workflow = (self.root / '.github/workflows/pbip-metadata.yml').read_text()
        self.assertNotIn('__DEFAULT_BRANCH_JSON__', workflow)
        self.assertIn('branches: ["main"]', workflow)
        self.assertTrue((self.root / '.gitignore').read_text().startswith('# Existing rules\nlocal-data/\n'))
        before = self.snapshot()
        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn('Already installed', second.stdout)
        self.assertEqual(before, self.snapshot())
        upgraded = self.invoke('--upgrade', '--with-service')
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertTrue(json.loads((self.root / '.pbip-metadata/config.json').read_text())['service_enrichment'])
        backups = list((self.root / '.pbip-metadata/backups').rglob('config.json'))
        self.assertEqual(len(backups), 1)
        self.assertFalse(json.loads(backups[0].read_text())['service_enrichment'])

    def test_user_configuration_survives_upgrade(self):
        self.assertEqual(self.invoke().returncode, 0)
        path = self.root / '.pbip-metadata/config.json'
        config = json.loads(path.read_text())
        config.update(service_enrichment=True, documentation_branch='report-docs', custom_setting='keep')
        path.write_text(json.dumps(config, indent=4) + '\n', encoding='utf-8')
        original = path.read_bytes()
        result = self.invoke('--upgrade')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), original)
        result = self.invoke('--upgrade', '--without-service')
        self.assertEqual(result.returncode, 0, result.stderr)
        config['service_enrichment'] = False
        self.assertEqual(json.loads(path.read_text()), config)
        self.assertIn(original, [p.read_bytes() for p in (self.root / '.pbip-metadata/backups').rglob('config.json')])

    def test_string_boolean_is_rejected_without_changes(self):
        self.assertEqual(self.invoke().returncode, 0)
        path = self.root / '.pbip-metadata/config.json'
        config = json.loads(path.read_text())
        config['service_enrichment'] = 'false'
        path.write_text(json.dumps(config), encoding='utf-8')
        before = self.snapshot()
        result = self.invoke('--upgrade')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('JSON boolean', result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_conflicting_workflow_is_preserved(self):
        path = self.root / '.github/workflows/pbip-metadata.yml'
        path.parent.mkdir(parents=True)
        path.write_text('name: Existing unrelated workflow\n')
        before = self.snapshot()
        result = self.invoke('--upgrade')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_modified_managed_file_is_preserved(self):
        self.assertEqual(self.invoke().returncode, 0)
        path = self.root / '.pbip-metadata/scripts/tmdl_metadata.py'
        path.write_text(path.read_text(encoding='utf-8') + '\n# User customization\n', encoding='utf-8')
        before = self.snapshot()
        result = self.invoke('--upgrade', '--with-service')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Local or unmanaged changes', result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_bad_source_and_branch_are_rejected(self):
        before = self.snapshot()
        for args in (('--source', '../outside'), ('--documentation-branch', 'main'), ('--documentation-branch', 'bad\nbranch')):
            result = self.invoke(*args)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_root_reports_are_supported(self):
        # Move both fixture directories within the checked temporary repository.
        source = (self.root / 'Finance').resolve()
        self.assertEqual(source.parent, self.root.resolve())
        for item in source.iterdir():
            target = (self.root / item.name).resolve()
            self.assertEqual(target.parent, self.root.resolve())
            shutil.move(str(item), str(target))
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / '.pbip-metadata/config.json').read_text())['source_directories'], ['.'])
        preview = self.root / 'pbip-metadata-output'
        output = subprocess.run([sys.executable, '-B', str(self.root / '.pbip-metadata/scripts/generate_pbip_md.py'), '--repo-root', str(self.root), '--out', str(preview)], capture_output=True, text=True)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(json.loads((preview / 'manifest.json').read_text())[0]['workspace'], '_root')

    def test_standalone_zip_installs(self):
        dist = Path(self.temp.name) / 'dist'
        built = subprocess.run([sys.executable, '-B', str(PACKAGE / 'build_package.py'), '--out', str(dist)], capture_output=True, text=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        archive = next(dist.glob('*.zip'))
        original_bytes = archive.read_bytes()
        rebuilt = subprocess.run([sys.executable, '-B', str(PACKAGE / 'build_package.py'), '--out', str(dist)], capture_output=True, text=True)
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
        self.assertEqual(original_bytes, archive.read_bytes())
        self.assertIn(hashlib.sha256(archive.read_bytes()).hexdigest(), (dist / 'SHA256SUMS').read_text())
        extracted = Path(self.temp.name) / 'extracted'
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertFalse(any('__pycache__' in n or '.Report/' in n for n in names))
            z.extractall(extracted)
        result = self.invoke(package=extracted / 'pbip-metadata-installer')
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == 'nt', 'PowerShell wrapper tested on Windows')
    def test_powershell_whatif(self):
        executable = shutil.which('pwsh') or shutil.which('powershell')
        if not executable:
            self.skipTest('PowerShell unavailable')
        before = self.snapshot()
        result = subprocess.run([executable, '-NoProfile', '-File', str(PACKAGE / 'install.ps1'), '-RepositoryPath', str(self.root), '-PythonExecutable', sys.executable, '-WhatIf'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Dry run complete', result.stdout)
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
