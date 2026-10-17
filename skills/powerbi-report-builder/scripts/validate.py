"""Validate PBIP/PBIR text files before Desktop or CI sees them. Stdlib only.

Catches:
  - leftover conflict markers ("<<<<<<<", "=======", ">>>>>>>") at the start of a line
  - JSON files that don't parse
  - JSON objects with duplicate keys at the same level (Power BI rejects these)
  - a UTF-8 BOM on JSON/TMDL files (Desktop rejects "UTF8 with BOM")
  - files that aren't valid UTF-8

Usage:
  python validate.py [--base origin/main] [--root .]   changed files vs base (committed, staged, unstaged, untracked)
  python validate.py --all <folder>                      every PBIP text file under a folder
  python validate.py <file> [<file> ...]                 specific files
Exits 0 when clean, 1 otherwise.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

TEXT_SUFFIXES = {".json", ".tmdl", ".m", ".pqm", ".pbir", ".pbism", ".pbip", ".platform"}
JSON_SUFFIXES = {".json", ".pbir", ".pbism", ".pbip", ".platform"}
BOM = b"\xef\xbb\xbf"
CONFLICT = re.compile(r"^(<{7}|={7}|>{7})(\s|$)", re.MULTILINE)


def _no_duplicates(pairs):
    dupes = sorted(k for k, n in Counter(k for k, _ in pairs).items() if n > 1)
    if dupes:
        raise ValueError("duplicate keys at same level: " + ", ".join(dupes))
    return dict(pairs)


def validate_file(path: Path) -> list:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"cannot read file: {exc}"]
    errors = []
    if raw.startswith(BOM):
        errors.append("starts with a UTF-8 BOM (Desktop rejects it); rewrite as UTF-8 without BOM")
        raw = raw[len(BOM):]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return errors + [f"not valid UTF-8: {exc}"]
    for line_no, line in enumerate(text.splitlines(), start=1):
        if CONFLICT.match(line):
            errors.append(f"conflict marker at line {line_no}: {line.rstrip()[:60]}")
    if (path.name.lower() if path.name == '.platform' else path.suffix.lower()) in JSON_SUFFIXES:
        try:
            json.loads(text, object_pairs_hook=_no_duplicates)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON at line {exc.lineno}, col {exc.colno}: {exc.msg}")
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def changed_files(base: str, root: Path) -> list:
    def git(*args):
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True)
        return [name for name in out.stdout.split("\0") if name]

    names = git("diff", "--name-only", "-z", base) + git("ls-files", "--others", "--exclude-standard", "-z")
    return sorted({root / n for n in names})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="specific files to check")
    parser.add_argument("--base", default="origin/main", help="git ref to diff against (default origin/main)")
    parser.add_argument("--root", default=".", help="repo root for --base mode (default cwd)")
    parser.add_argument("--all", metavar="FOLDER", help="check every PBIP text file under FOLDER")
    args = parser.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    elif args.all:
        paths = sorted(p for p in Path(args.all).rglob("*") if p.is_file() and not set(p.parts).intersection({'.git', '.pbi', '.venv', '.runtime', 'node_modules', '__pycache__'}))
    else:
        root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=args.root,
                                   capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip())
        paths = changed_files(args.base, root)

    paths = [p for p in paths if p.is_file() and (p.name.lower() if p.name == '.platform' else p.suffix.lower()) in TEXT_SUFFIXES]
    if not paths:
        print("No PBIP text files to check.")
        return 0

    failures = [(p, e) for p in paths for e in [validate_file(p)] if e]
    if not failures:
        print(f"OK: {len(paths)} file(s) checked, no problems.")
        return 0
    print(f"FAILED: {len(failures)} of {len(paths)} file(s) have problems.")
    for path, errors in failures:
        print(f"\n{path}")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  - ... and {len(errors) - 10} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
