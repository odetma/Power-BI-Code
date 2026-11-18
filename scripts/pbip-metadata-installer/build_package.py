"""Build a deterministic, allowlisted standalone installer ZIP and checksum."""
import argparse
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = [
    'README.md', 'USAGE.md', 'LICENSE', 'VERSION', 'config.example.json',
    'install.ps1', 'install.py', 'build_package.py',
    'payload/scripts/generate_pbip_md.py', 'payload/scripts/tmdl_metadata.py',
    'payload/scripts/generate_report_links.py', 'payload/tests/test_metadata.py',
    'templates/pbip-metadata.yml', 'tests/test_installer.py',
]


def build(out):
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION must use major.minor.patch.')
    for name in FILES:
        if not (ROOT / name).is_file():
            raise ValueError('Missing package file: ' + name)
        text = (ROOT / name).read_text(encoding='utf-8')
        patterns = [r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b',
                    r'(?i)[a-z]:[\\/]Users[\\/]', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
        if any(re.search(pattern, text) for pattern in patterns):
            raise ValueError('Potential identifier, personal path or private key in package file: ' + name)
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f'pbip-metadata-installer-v{version}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(FILES):
            info = zipfile.ZipInfo('pbip-metadata-installer/' + name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            # Normalize text to LF so the same source has the same ZIP on Windows/Linux.
            target.writestr(info, (ROOT / name).read_text(encoding='utf-8').encode('utf-8'))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / 'SHA256SUMS').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    print(f'Built {archive.name}: {archive.stat().st_size} bytes')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
