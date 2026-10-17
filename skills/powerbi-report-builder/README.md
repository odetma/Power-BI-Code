# Power BI Report Builder

A reusable local authoring skill for Power BI PBIR reports. It helps an AI assistant inspect a model, plan a business story, edit pages and visuals, add drillthrough, validate files, reload Desktop, and inspect saved screenshots.

**Windows is required for Desktop reload, native UI Automation, and screenshots.** It works with reports opened directly from `<report>.Report/definition.pbir`; no generated PBIP launcher is required. Existing PBIP projects are also supported.

## Requirements

| Requirement | Notes |
| --- | --- |
| Windows 10/11, interactive signed-in desktop | Headless Linux/cloud sessions cannot run the Desktop preview loop. |
| Power BI Desktop 2.159+ | Tested with 2.159.883.0. New versions must expose a compatible Desktop Bridge. |
| Node.js 20+ including npm | Tested with Node 24.13.0. Install from [nodejs.org](https://nodejs.org/). |
| Python 3.10+ | Tested with Python 3.12.14. Install from [python.org](https://www.python.org/downloads/windows/) or use the Python launcher. |
| Git | For source control and changed-file validation. |
| An AI client supporting local skills and tools | For example, Codex or Claude Code. The scripts can also be run directly. |
| Power BI modeling MCP connected in that client | Follow [Microsoft's modeling MCP instructions](https://github.com/microsoft/powerbi-modeling-mcp) and [Power BI MCP documentation](https://learn.microsoft.com/power-bi/developer/mcp/). The installer does not edit your client's MCP configuration or authentication. |

Data-source access is a separate prerequisite. A fresh report checkout has no data cache: open it and refresh manually when appropriate. Never assume an installation check proves that the report has data.

## Install from this repository

In PowerShell:

```powershell
git clone https://github.com/odetma/Power-BI-Code.git
Set-Location Power-BI-Code

# Defaults to CODEX_HOME/skills, or your user profile's .codex/skills.
.\scripts\install-powerbi-report-builder.ps1
$skillHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$skill = Join-Path $skillHome 'skills\powerbi-report-builder'
& "$skill\scripts\setup.ps1"
```

If your PowerShell policy blocks reviewed local scripts, follow your organization's policy; this package does not change execution policy. Setup creates a private `.venv` and `.runtime` **inside the installed skill**, installs pinned dependencies, and runs the checks. It does not install Desktop, Python, Node, Git, or an MCP server, and does not change the user's global PATH.

For another client or a workspace-specific skill directory, choose its supported skill location explicitly:

```powershell
.\scripts\install-powerbi-report-builder.ps1 -Destination "$env:USERPROFILE\.claude\skills\powerbi-report-builder"
# Or a Codex workspace-specific location:
.\scripts\install-powerbi-report-builder.ps1 -Destination 'D:\My Project\.agents\skills\powerbi-report-builder'
```

The installer refuses to overwrite an existing skill. For an update, back up your installed copy (including custom team guidance), install to a new empty folder, rerun setup, and move to the new version using your client's normal skill-management process. Restart the client or reload its skills.

If Python or Node is not on PATH, set **process-local** overrides before setup:

```powershell
$env:PBI_BUILDER_PYTHON = 'D:\Tools\Python\python.exe'
$env:PBI_BUILDER_NODE = 'D:\Tools\Node\node.exe'
```

## First report

1. Open the intended `.Report\definition.pbir` in Desktop and wait for data to render. Use a feature branch and inspect any existing changes.
2. Confirm your modeling MCP exposes instance discovery and connection tools. Discover the current instance; ports change when Desktop restarts.
3. In your AI client, ask:

   > Use $powerbi-report-builder on the report at D:\Reports\Sales.Report. Inspect the model and current page first. Add a monthly sales comparison, validate the PBIR, reload Desktop, and review a saved screenshot. Preserve existing model bindings and unrelated changes.

4. The assistant should check dependencies, use read-only data inspection, edit only authorized objects, validate, reload, capture, and inspect the result. Save in Desktop **after the latest file write has loaded**.

## Useful commands

Commands below assume `$skill` points to the installed skill. Replace example paths, PID, and page IDs with values discovered in your own report.

```powershell
& "$skill\scripts\check.ps1"
& "$skill\.runtime\node\node_modules\.bin\powerbi-desktop.cmd" status

# File integrity: no Desktop needed.
& "$skill\scripts\validate.ps1" -All 'D:\Reports\Sales.Report'

# Formatting metadata and schema diagnostics; not the preview workflow.
$author = Join-Path $skill '.runtime\node\node_modules\.bin\powerbi-report-author.cmd'
& $author catalog describe lineChart
& $author formatting describe-object actionButton text
& $author validate 'D:\Reports\Sales.Report' --format text

# Reload and capture a page. Requires a clean Desktop state by default.
& "$skill\scripts\reload-and-screenshot.ps1" -ProcessId 12345 `
    -Pages 'your-page-id' -OutDir "$env:TEMP\pbi-review"

# Capture separately after loading/dialog handling; does not reload.
& "$skill\scripts\reload-and-screenshot.ps1" -ProcessId 12345 `
    -Pages 'your-page-id' -NoReload -OutDir "$env:TEMP\pbi-review"
```

Find page IDs in `definition/pages/pages.json`; display names are in each `page.json`. For all-page review pass every ID. Multiple Desktop windows require an explicit PID. PBIP projects resolve their report artifact path from the project JSON, including when it differs from the launcher name.

### Unsaved state and warnings

Reloads can discard in-memory edits. If Desktop reports unsaved or unknown state, the helper stops. Resolve it manually, or pass `-AllowDiscardUnsavedChanges` **only after the user authorizes discarding that state**. This is also enforced by the low-level helper (`--allow-unsaved`). Do not infer authorization from a warning's text.

Some DirectQuery/composite reports show **Potential security risk** after reload. By default the script leaves it for the user. After explicit authorization for that exact multiple-data-source warning, add:

```powershell
& "$skill\scripts\reload-and-screenshot.ps1" -ProcessId 12345 `
    -Pages 'your-page-id' -OutDir "$env:TEMP\pbi-review" `
    -ConfirmMultipleSourceWarning
```

The handler matches the target process, dialog title, automation ID, body/question, and OK/Cancel buttons. It uses native `CUIAutomation8` / `InvokePattern`, checks dismissal and window bounds, and sends no mouse or keyboard input. It does not change privacy/security settings. Other dialogs, ambiguous controls, unsupported providers, and localized/non-English warning text require manual handling. There is no screen-takeover fallback. A minimized window requires manual restoration or explicit `-RestoreMinimized`.

## Included tools and lessons

| File | Purpose |
| --- | --- |
| `SKILL.md`, `references/` | Business questions, model checks, DAX/PBIR pitfalls, chart choice, and review criteria. |
| `scripts/setup.ps1`, `check.ps1`, `runtime.ps1` | Local dependency setup and discovery. |
| `scripts/pbir-reload.mjs` | PBIR-compatible call through the installed Microsoft Bridge library. |
| `scripts/reload-and-screenshot.ps1` | Bounded reload, optional warning confirmation, page selection, PNG capture. |
| `scripts/capture-window.ps1` | Windows `PrintWindow`; no Bridge screenshot, Alt tap, or foreground activation. |
| `scripts/confirm-source-warning.ps1`, `.py` | Opt-in native UIA confirmation for the exact warning. |
| `scripts/validate.ps1`, `.py` | UTF-8/BOM, duplicate JSON keys, parse errors, and conflict-marker checks. |

The package includes lessons tested while building an overview and raw-data drillthrough: native UIA is required for the embedded legacy warning; button toggles/styles need separate entries; drillthrough must bind the exact source fields; source filters and row-grain totals need live verification; orders differ from units; and prior-year comparisons must account for leap years. No sample report, customer rows, personal paths, screenshots, credentials, or installed dependencies are distributed.

## Verification and limitations

File validation is not schema validation, and schema validation is not proof of rendering. The workflow requires opening saved screenshots after the final reload, checking clipping and errors, and testing actual interactions. A main-window PNG can omit an owned modal; require a clean window state and the handler log when applicable.

The Bridge helper imports the pinned package's library API. Future Desktop/CLI changes may require an update; test dependency upgrades together. The optional authoring CLI can be skipped with `setup.ps1 -SkipAuthoringCli`; a formatting/schema metadata tool is still needed for authoring. Source refresh, deployment, publishing, GitHub CI, and automatic installation of MCP/authentication are outside setup.

Developer tests are under [`tests/powerbi-report-builder`](https://github.com/odetma/Power-BI-Code/tree/main/tests/powerbi-report-builder). They use synthetic fixtures, not customer data. See [references/desktop-bridge.md](references/desktop-bridge.md) for the live verification checklist.

## License and provenance

MIT, copyright Odet Maimoni; [LICENSE](LICENSE) travels with an installed copy. Adapted from the repository owner's supplied generic report-builder skill with permission, including the tested PBIR and native UIA updates. This is a community skill, not an official Microsoft product. Microsoft CLIs and `comtypes` are downloaded separately by setup and retain their own licenses.
