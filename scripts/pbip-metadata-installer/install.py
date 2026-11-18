"""Install a portable PBIP documentation pipeline into an existing Git repository."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parent
MANIFEST = '.pbip-metadata/install-manifest.json'
CONFIG = '.pbip-metadata/config.json'
IGNORE_BLOCK = '\n# PBIP metadata documentation\n/pbip-metadata-output/\n/pbip-metadata-repeat/\n/.pbip-metadata/backups/\n'


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, encoding='utf-8', errors='replace', capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Command failed: ' + str(args[0]))
    return result.stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_target(root, relative):
    target = root / relative
    resolved = target.resolve()
    resolved.relative_to(root)
    # Do not traverse links/junctions, even when their targets happen to be inside.
    current = target
    while current != root:
        if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
            raise ValueError(f'Refusing linked install path: {relative}')
        current = current.parent
    return target


def discover_sources(root):
    skipped = {'.git', '.pbip-metadata', 'node_modules', '.venv', 'venv', '.claude'}
    found = set()
    for parent, dirs, _ in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skipped and not (Path(parent) / d).is_symlink()]
        for name in dirs[:]:
            if name.endswith('.Report'):
                relative = (Path(parent) / name).relative_to(root)
                found.add(relative.parts[0] if len(relative.parts) > 1 else '.')
                dirs.remove(name)
    return ['.'] if '.' in found else sorted(found)


def make_plan(root, sources, branch, service, default_branch):
    files = {}
    files['.pbip-metadata/LICENSE'] = (PACKAGE / 'LICENSE').read_bytes()
    for path in sorted((PACKAGE / 'payload').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files['.pbip-metadata/' + path.relative_to(PACKAGE / 'payload').as_posix()] = path.read_bytes()
    files[CONFIG] = (json.dumps(dict(source_directories=sources, documentation_branch=branch,
                                   service_enrichment=service), indent=2) + '\n').encode()
    workflow = (PACKAGE / 'templates/pbip-metadata.yml').read_text(encoding='utf-8')
    files['.github/workflows/pbip-metadata.yml'] = workflow.replace('__DEFAULT_BRANCH_JSON__', json.dumps(default_branch)).encode()
    files['docs/pbip-metadata.md'] = (PACKAGE / 'USAGE.md').read_bytes()
    existing_ignore = safe_target(root, '.gitignore')
    old = existing_ignore.read_bytes() if existing_ignore.exists() else b''
    extra = [line for line in IGNORE_BLOCK.splitlines() if line and line not in old.decode('utf-8-sig').splitlines()]
    files['.gitignore'] = old + (('\n' + '\n'.join(extra) + '\n').encode() if extra else b'')
    return files


def install(args):
    root = Path(args.repository).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Repository directory does not exist.')
    actual = Path(run(['git', 'rev-parse', '--show-toplevel'], root)).resolve()
    if actual != root:
        raise ValueError('Pass the repository root, not a subdirectory.')
    manifest_path = safe_target(root, MANIFEST)
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    prior_config_path = safe_target(root, CONFIG)
    prior_config = json.loads(prior_config_path.read_text(encoding='utf-8')) if prior_config_path.exists() else {}
    sources = args.source or prior_config.get('source_directories') or discover_sources(root)
    if not sources:
        raise ValueError('No .Report directories found. Save reports as PBIP first, or specify --source.')
    normalized_sources = []
    for source in sources:
        if Path(source).is_absolute() or '..' in Path(source).parts or source.startswith('-'):
            raise ValueError('Source directories must be relative paths inside the repository.')
        resolved = (root / source).resolve()
        resolved.relative_to(root)
        if not resolved.is_dir():
            raise ValueError('Source directory does not exist: ' + source)
        normalized_sources.append(resolved.relative_to(root).as_posix())
    sources = sorted(set(normalized_sources))
    branch = args.documentation_branch or prior_config.get('documentation_branch', 'pbip-metadata')
    run(['git', 'check-ref-format', '--branch', branch], root)
    # Use the remote default branch; a feature branch is not a publishing target.
    remote = subprocess.run(['git', 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], cwd=root, capture_output=True, text=True)
    default_branch = remote.stdout.strip().removeprefix('origin/') if remote.returncode == 0 else ''
    if not default_branch:
        branches = run(['git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads'], root).splitlines()
        default_branch = next((b for b in ('main', 'master') if b in branches), '')
    if not default_branch:
        raise ValueError('Cannot identify the default branch. Set origin/HEAD with git remote set-head origin -a.')
    if branch == default_branch or branch in ('HEAD', 'main', 'master'):
        raise ValueError('Use a separate documentation branch, not the source branch.')
    service = args.service if args.service is not None else prior_config.get('service_enrichment', False)
    if not isinstance(service, bool):
        raise ValueError('service_enrichment must be a JSON boolean: true or false.')
    files = make_plan(root, sources, branch, service, default_branch)
    # Configuration belongs to the user. Preserve extra settings and formatting
    # unless a supplied option actually changes the effective configuration.
    if prior_config_path.exists() and CONFIG in previous.get('files', {}):
        updated_config = dict(prior_config)
        updated_config.update(json.loads(files[CONFIG]))
        files[CONFIG] = (prior_config_path.read_bytes() if updated_config == prior_config else
                         (json.dumps(updated_config, indent=2) + '\n').encode())
    changed = {}
    for relative, content in files.items():
        target = safe_target(root, relative)
        if target.exists() and not target.is_file():
            raise ValueError('Install destination is not a regular file: ' + relative)
        if target.exists() and target.read_bytes() == content:
            continue
        if target.exists() and relative != '.gitignore':
            if not args.upgrade:
                raise ValueError(f'Existing file differs: {relative}. Use --upgrade for a managed installation.')
            known = previous.get('files', {}).get(relative)
            if known is None or (relative != CONFIG and digest(target.read_bytes()) != known):
                raise ValueError(f'Local or unmanaged changes detected: {relative}. Preserve/resolve them before upgrading.')
        changed[relative] = content
    # Preflight the entire plan before any target writes.
    print('Sources: ' + ', '.join(sources))
    print('Default source branch: ' + default_branch)
    print('Documentation branch: ' + branch)
    print('Power BI Service enrichment: ' + ('enabled' if service else 'disabled'))
    for relative in changed:
        print(('Update: ' if (root / relative).exists() else 'Create: ') + relative)
    if args.dry_run:
        print('Dry run complete. No files were written and no credentials were accessed.')
        return
    if not changed:
        print('Already installed; all managed files are unchanged.')
        return
    print('Running packaged regression tests...')
    # Stage the payload outside the target before tests and generation.
    with tempfile.TemporaryDirectory(prefix='pbip-metadata-') as temporary:
        staging = Path(temporary)
        shutil.copytree(PACKAGE / 'payload', staging / 'payload', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(staging / 'payload/tests'), '-p', 'test_metadata.py', '-v'])
        command = [sys.executable, '-B', str(staging / 'payload/scripts/generate_pbip_md.py'), '--repo-root', str(root), '--out', str(staging / 'preview')]
        for source in sources:
            command += ['--source', source]
        print(run(command))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_root = safe_target(root, '.pbip-metadata/backups/' + stamp)
    old_contents = {relative: (root / relative).read_bytes() if (root / relative).exists() else None for relative in changed}
    # Back up exact pre-install bytes, including .gitignore, before replacing files.
    for relative, old in old_contents.items():
        if old is not None:
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(old)
    applied = []
    try:
        for relative, content in changed.items():
            target = safe_target(root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            applied.append(relative)
            target.write_bytes(content)
        state = dict(version=(PACKAGE / 'VERSION').read_text().strip(), files={k: digest(v) for k, v in files.items() if k != '.gitignore'})
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    except Exception:
        for relative in reversed(applied):
            target = safe_target(root, relative)
            old = old_contents[relative]
            if old is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(old)
        raise
    print('Installation complete. No commit, push, or cloud changes were made.')
    print('Review git diff, then commit the installed files and merge to ' + default_branch + '.')
    print('Read docs/pbip-metadata.md for configuration and output locations.')
    if service:
        print('Configure repository variables AZURE_CLIENT_ID, AZURE_TENANT_ID, WORKSPACE_MAPPING and secret AZURE_CLIENT_SECRET in GitHub Actions.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--source', action='append')
    parser.add_argument('--documentation-branch')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--with-service', dest='service', action='store_true')
    group.add_argument('--without-service', dest='service', action='store_false')
    parser.set_defaults(service=None)
    parser.add_argument('--upgrade', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 or newer is required.')
    try:
        install(args)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, 'Installation stopped: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
