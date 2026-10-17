# Desktop reload, native dialogs, and saved screenshot review

## Select the right report

Use the skill-local `powerbi-desktop.cmd status` to inspect the open path, PID, and unsaved state. Pass a PID when several Desktop instances are open. Do not reuse example PIDs or ports. Discover the modeling MCP port separately.

The helper resolves `definition.pbir`, `.Report` directories, and PBIP report artifact paths. PBIP is an optional launcher. Keep the existing report/model folders, `.platform` identities, schemas, resource registrations, and relative model binding. Do not create a launcher just to reload PBIR.

## Reload

`reload-and-screenshot.ps1 -ProcessId <pid> -Pages <pageIds> -OutDir <temporary folder>` imports the installed Microsoft Bridge library and calls `file.reload/v1`. The pinned CLI's normal reload command does not resolve `definition.pbir`; the bridge method itself reloads the open file without a path.

The wrapper waits up to 120 seconds per reload attempt, checks for an authorized warning while waiting, and retries once after a transient "Host is not ready" result. Native warning inspection has its own 20-second subprocess limit. A timeout or unknown invocation outcome requires manual inspection; do not repeatedly retry a potentially completed confirmation.

Reload defaults to report definition only. `-Model` also reloads model definitions and can replace unsaved MCP changes. Export/persist intended model changes first. Treat `hasUnsavedChanges = true` **or unknown** as a stop unless the user has authorized discarding that state; use `-AllowDiscardUnsavedChanges` only for that authorization. The low-level JS helper enforces the same check.

## The exact multiple-source warning

DirectQuery/composite models may show **Potential security risk** after reload. Identify storage modes through TMDL or the modeling MCP; the warning is not guaranteed and can occur in other multiple-source configurations too.

The default behavior is **manual confirmation**. A user's explicit authorization for this warning permits `-ConfirmMultipleSourceWarning` for that session/report. That authorization is not part of the distributed skill and does not carry to another user.

The Python helper requires all of:

- Target process is `PBIDesktop.exe` and the report window belongs to the selected PID.
- One visible window titled **Potential security risk**, in that PID, with automation ID **MessageDetailsDialog**.
- Body begins **This file uses multiple data sources.**
- Question **Do you want to open this file?**
- Exactly one enabled **OK** button and one **Cancel** button, with an available InvokePattern.

It calls native `CUIAutomation8` / `IUIAutomationInvokePattern.Invoke()`, checks that the dialog closed, and compares nonempty Win32 window bounds before/after. It does not move/resize/activate the report or send mouse/keyboard events. The native COM interface is necessary: the managed .NET UIA client exposed only unnamed panes for the embedded `Internet Explorer_Server` warning during testing. Power BI can create this as an unowned top-level window, so match PID and content rather than assuming an owner HWND.

Localized warnings, other dialogs, inaccessible content, ambiguous buttons, changed bounds, or unsupported patterns stop for manual handling. Never use blind Enter, screen takeover, or disable privacy/security warnings as a fallback. Direct Python invocation is inspect-only unless `--confirm` is explicitly supplied. `--check-dependencies` checks native COM availability without touching a report.

## Capture and review

After reload and any dialog handling, run the helper again with **`-NoReload`** if a separate capture is needed. Supply the affected page IDs; use all page IDs for report-wide edits. Page selection uses UI Automation and does not change `pages.json`. Names must match a unique page tab, including Desktop's `Hidden` / `Report landing page` prefixes.

Captures use Windows **PrintWindow**, not the Bridge snapshot renderer. Do not use `powerbi-desktop screenshot`: it has caused layout corruption on mixed-DPI displays. The distributed capture helper does not send Alt or request foreground activation. Restoring a minimized window is opt-in via `-RestoreMinimized`; otherwise restore it manually.

Open every saved PNG with the image viewer. Verify the final text/formatting, full affected visual bounds, labels, binding errors, data, active filters, and absence of the external-changes banner. Fix clipped/blank/still-loading captures and recapture. Do not claim success from a bridge response, accessibility text, or an unsaved transient snapshot. A main-window capture can omit an owned dialog: check Desktop/handler status too.

Keep screenshots outside the report repository; they may contain business data. Link the reviewed screenshot and report structural and visual results separately. Ask the developer to save only after the last edit has actually loaded and visual review passes.

## Live acceptance checklist

Use a report the developer owns, with explicit authorization for reload and warning confirmation:

1. Check PID, open report path, current branch/diff, data availability, and unsaved state.
2. Record window bounds; make one reversible title-formatting change.
3. Validate files and formatting/schema metadata.
4. Reload, confirm only the exact authorized dialog, capture affected pages, and inspect the saved PNGs.
5. Verify dismissal and unchanged bounds; do not treat zero rectangles as proof of unchanged size.
6. Restore the original edit if it was a reversible pilot, then repeat validation/reload/review.
7. For drillthrough, exercise each supported source context menu and compare the passed filters and line-level totals with a read-only query. In Desktop, authored buttons generally require Ctrl+click; a UIA Invoke can merely select them in edit mode. Native UIA `ShowContextMenu`, ExpandCollapse, and Invoke on menu items can test the context-menu route without screen takeover.

The originating workflow was tested on Desktop 2.159.883.0, Bridge 1.0.0, authoring CLI 0.5.0, Python 3.12.14, and Node 24.13.0. It verified reload, native confirmation without changed bounds, saved-image review, product drillthrough, and selected-year month drillthrough. These are a tested configuration, not a guarantee for every Desktop version or language.
