# PBIP Metadata Documentation Installer

Turn a Power BI Project repository into automatically updated Markdown documentation.
This standalone installer includes the generator, regression tests and a GitHub
Actions workflow. Version: **1.0.0**.

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

## Requirements

- Python **3.11+** and Git on PATH. Python standard library only; no pip install.
- An existing Git repository with at least one `.Report` directory. Commit the
  initial repository before installing. Local models should be in TMDL format.
- PowerShell **5.1+** on Windows for the convenience wrapper. `install.py` also
  runs directly on Windows, Linux and macOS.
- GitHub Actions enabled in the destination repository for automation. Branch
  rules must allow `GITHUB_TOKEN` to write the separate documentation branch.

## Install from this repository

1. Download this repository using **Code > Download ZIP** and extract it, or clone it with Git.
2. Open a terminal in the downloaded **Power-BI-Code** folder. Keep the entire
   `scripts/pbip-metadata-installer` folder together; `install.ps1` needs the other files.
3. Replace `C:\Repos\MyPowerBI` below with the local root of **your Power BI Git
   repository**, where your `.Report` and `.SemanticModel` folders are stored.

Preview the installation:

```powershell
.\scripts\pbip-metadata-installer\install.ps1 -RepositoryPath "C:\Repos\MyPowerBI" -WhatIf
```

Install with local metadata only (no Microsoft credentials needed):

```powershell
.\scripts\pbip-metadata-installer\install.ps1 -RepositoryPath "C:\Repos\MyPowerBI"
```

After installation, review and commit the installed files in **your Power BI
repository**, then push and merge them into its default branch. Open **Actions >
PBIP Metadata Documentation** to follow the first run. When it succeeds, switch
to the **pbip-metadata** branch and open **metadata/README.md**.

### Optional settings

Source folders are discovered automatically. Use the following only if you want
to select specific folders or change the output branch:

```powershell
.\scripts\pbip-metadata-installer\install.ps1 `
  -RepositoryPath "C:\Repos\MyPowerBI" `
  -SourceDirectories "Finance", "Operations" `
  -DocumentationBranch "pbip-metadata"
```

| Option | Meaning |
| --- | --- |
| `-RepositoryPath` | Local path to your Power BI Git repository; required. |
| `-SourceDirectories` | Folders to document, relative to that repository. `Finance` and `Operations` are example folder names. Omit to discover them automatically. |
| `-DocumentationBranch` | Separate branch for generated documentation; defaults to `pbip-metadata`. |
| `-WithService` | Add published Power BI links and IDs. Complete the [service setup](USAGE.md#enable-optional-power-bi-service-enrichment) before the first workflow run. |
| `-WhatIf` | Preview the planned installation without writing files. |
| `-Upgrade` | Update an existing installation. |

The backtick at the end of a PowerShell line continues the same command.

If Python is not on PATH, add `-PythonExecutable "C:\Tools\Python\python.exe"`.
Use your normal execution-policy process if PowerShell blocks a downloaded script.

Cross-platform equivalent:

```sh
python scripts/pbip-metadata-installer/install.py \
  --repository /path/to/repository \
  --source Finance --source Operations
```

## Install from the ZIP

For a smaller download, open this repository's **Actions > Community Metadata
Installer Checks**, select a successful run on `main`, and download the
`pbip-metadata-installer-package` artifact. GitHub requires you to sign in for
artifact downloads. Extract the artifact, then extract the installer ZIP inside it.
Open a terminal in the extracted `pbip-metadata-installer` folder and run:

```powershell
.\install.ps1 -RepositoryPath "C:\Repos\MyPowerBI"
```

Artifacts expire after 90 days; use the repository download above if unavailable.
The ZIP is self-contained; no other repository files are needed. Its SHA-256
checksum is included in `SHA256SUMS`. Build the same ZIP locally with:

```sh
python scripts/pbip-metadata-installer/build_package.py --out /path/to/distribution
```

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
Your edits to `config.json` are preserved; explicit installer options override
only their corresponding settings. Other managed files modified locally are
**not overwritten**, even with upgrade.
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

This is a documentation extractor, not a full TMDL validator. Hidden pages are
excluded. Visual fields/filters are best-effort, and legacy report page filters
are not fully extracted. Remote-only model definitions are unavailable locally.
Review the generated documentation before sharing it: real model expressions,
roles and source queries can contain internal information.

## License

MIT; see [LICENSE](LICENSE).
