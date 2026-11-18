# PBIP Metadata Documentation Installer

Turn a Power BI Project repository into automatically updated Markdown documentation.
This standalone installer includes the generator, regression tests and a GitHub
Actions workflow. Version: **1.0.0**.

The package contains no tenant, application, workspace or report identifiers,
credentials, private reports or generated customer documentation. All fixtures
are synthetic. Operational identifiers are supplied by each installation.
The MIT copyright notice is retained in `LICENSE`.

## What you get

- One Markdown document per report, including tables, columns, calculated
  columns, DAX measures, relationships, partitions, functions, roles and report
  pages/visual fields.
- Multiline DAX/M and descriptions, including triple-backtick expressions,
  blank lines, relative indentation and literal HTML/SVG content.
- Unicode field names and actual semantic model bindings from `definition.pbir`.
- Optional Power BI workspace links, report/dataset IDs and page links.
- PR preview artifacts and a dedicated documentation branch after merge.
- Automatic updates on source changes, manual runs and daily at 05:00 UTC.
- No Workato dependency and no model data queries.

## Requirements

- Python **3.11+** and Git on PATH. Python standard library only; no pip install.
- An existing Git repository with at least one `.Report` directory. Commit the
  initial repository before installing. Local models should be in TMDL format.
- PowerShell **5.1+** on Windows for the convenience wrapper. `install.py` also
  runs directly on Windows, Linux and macOS.
- GitHub Actions enabled in the destination repository for automation. Branch
  rules must allow `GITHUB_TOKEN` to write the separate documentation branch.

## Install from this repository

Clone/download the repository and open a terminal in its root. Preview first:

```powershell
.\scripts\pbip-metadata-installer\install.ps1 -RepositoryPath "C:\Repos\MyPowerBI" -WhatIf
```

Install with local metadata only (no Microsoft credentials needed):

```powershell
.\scripts\pbip-metadata-installer\install.ps1 -RepositoryPath "C:\Repos\MyPowerBI"
```

Source folders are discovered automatically. To choose them explicitly:

```powershell
.\scripts\pbip-metadata-installer\install.ps1 `
  -RepositoryPath "C:\Repos\MyPowerBI" `
  -SourceDirectories "Finance", "Operations" `
  -DocumentationBranch "pbip-metadata" `
  -WithService
```

If Python is not on PATH, add `-PythonExecutable "C:\Tools\Python\python.exe"`.
All paths in these commands are examples, not paths to an existing account.
Use your normal execution-policy process if PowerShell blocks a downloaded script.

Cross-platform equivalent:

```sh
python scripts/pbip-metadata-installer/install.py \
  --repository /path/to/repository \
  --source Finance --source Operations \
  --with-service
```

## Install from the ZIP

Download `pbip-metadata-installer-v1.0.0.zip` from the **Community Metadata
Installer Checks** workflow artifact named `pbip-metadata-installer-package`.
Extract it, then run `install.ps1` or `install.py` from the extracted folder.
The ZIP is self-contained; no other repository files are needed. Its SHA-256
checksum is included in `SHA256SUMS`. Build the same ZIP locally with:

```sh
python scripts/pbip-metadata-installer/build_package.py --out /path/to/distribution
```

Only an explicit list of installer/payload/test files is packaged. Local output,
credentials, caches and reports are never recursively swept into the ZIP.

## What installation does

1. Checks the repository, source directories and default branch.
2. Prints every planned file creation/update (`-WhatIf` / `--dry-run` stops here).
3. Runs the bundled regression tests and generates a temporary preview.
4. Backs up any replaced files under `.pbip-metadata/backups/<timestamp>/`.
5. Installs the files below and records hashes for future upgrades.

```text
your-repository/
  .pbip-metadata/
    config.json
    install-manifest.json
    scripts/
    tests/
  .github/workflows/pbip-metadata.yml
  docs/pbip-metadata.md
  .gitignore                              # appends generated-output exclusions
```

It never creates commits, pushes, changes Power BI reports/models or configures
cloud permissions. Review `git diff`, commit the installed files and merge to
your repository's default branch. Publication starts after that merge.

If `origin/HEAD` is unavailable, the installer recognizes local `main` or
`master`. For other default-branch names, first run `git remote set-head origin -a`.

## Configuration and upgrades

The installed `.pbip-metadata/config.json` contains only:

```json
{
  "source_directories": ["Finance", "Operations"],
  "documentation_branch": "pbip-metadata",
  "service_enrichment": false
}
```

For a repository with reports directly at its root, use `"."` as the source.
The corresponding service mapping key is `_root`; otherwise the key is the
report's top-level repository folder. Do not use a source-code branch as the
documentation branch.

Re-running an unchanged installation is a no-op. Use `-Upgrade` / `--upgrade`
for a newer version or to switch `-WithService` / `-WithoutService`.
Managed files modified locally are **not overwritten**, even with upgrade.
Resolve those differences yourself before updating. `.gitignore` additions are
merged without replacing existing content. Existing unrelated workflows and
unmanaged files with conflicting names are left untouched and stop installation.

To remove the integration, remove the installed workflow and `.pbip-metadata`
directory, then remove its `.gitignore` entries and documentation file. Keep any
backups or published documentation you still need. The installer performs no
automatic deletion of your documentation branch.

## Optional service setup

See [USAGE.md](USAGE.md) for step-by-step Entra, Power BI and GitHub settings,
matching rules, output locations and troubleshooting. Start without service
enrichment if you only need repository-based documentation.

## Tests and scope

```sh
python -m unittest discover -s scripts/pbip-metadata-installer/tests -v
python -m unittest discover -s scripts/pbip-metadata-installer/payload/tests -v
```

Installer integration tests use a temporary Git repository and synthetic PBIP
files. No cloud credentials or network access are required. CI tests on Windows
and Linux, including the PowerShell wrapper on Windows, and builds the ZIP.

This is a documentation extractor, not a full TMDL validator. Hidden pages are
excluded. Visual fields/filters are best-effort, and legacy report page filters
are not fully extracted. Remote-only model definitions are unavailable locally.
Review the generated documentation before sharing it: real model expressions,
roles and source queries can contain internal information.

## License

MIT; see [LICENSE](LICENSE).
