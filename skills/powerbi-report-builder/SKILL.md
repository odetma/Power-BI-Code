---
name: powerbi-report-builder
description: Build and change local Power BI PBIR report pages, visuals, and drillthrough with model-aware checks, Desktop reload, saved screenshots, and business-number reconciliation. Use for report authoring and layout work in .Report folders; model changes use the user's connected Power BI modeling MCP. Desktop preview requires Windows.
---

# Power BI Report Builder

Work with the developer from business question to a verified local report. Installation and commands are in [README.md](README.md). Do not publish, refresh external data, commit, or push unless the task authorizes it.

## Before editing

1. Run `scripts/check.ps1`. Desktop helpers require Windows, an interactive desktop, Power BI Desktop 2.159+, Node 20+, Python 3.10+, and the dependencies installed by `scripts/setup.ps1`.
2. Confirm the user's modeling MCP tools are available. Discover current instances and connect to the intended report; never reuse a previous port. Do not install/configure an MCP server yourself. A planning-only request remains read-only.
3. Check the actual checkout, branch, open report path, Git diff, and Desktop state. Preserve existing changes. Work on a feature branch according to repository instructions.
4. Inspect PBIR pages, theme, TMDL, relationships, data grain, and existing measure definitions. PBIR files are the source of truth; `definition.pbir` works without creating a PBIP launcher. Stop for developer conversion if the report is legacy `report.json`/`sections` format.
5. For substantive design, agree the page question and decisions. Use the approved plan when the user asks to implement it. Read [references/design-standard.md](references/design-standard.md) and [references/definition-of-done.md](references/definition-of-done.md). Preserve the existing theme unless changing it is authorized.

## Author and verify

1. Inspect and record read-only queries in the session scratchpad. Validate grain, period coverage, nulls, relationship coverage, units, currency basis, and cost definitions before displaying KPIs. Do not treat units as orders or a refresh timestamp as the latest transaction date.
2. Make authorized model changes through the modeling MCP. Read before updating. Persist/export only the intended model changes; preserve identities, bindings, source queries, and existing metadata. Do not reload a stale model over unsaved MCP changes.
3. Consult current visual/formatting metadata before editing PBIR. The optional skill-local Microsoft authoring CLI provides `catalog`, `formatting`, and schema `validate` commands; see the README. Prefer existing native visual templates.
4. Edit UTF-8 without BOM, preserving file line endings and schema versions. Use Python or an editor; PowerShell 5 `Set-Content -Encoding UTF8` introduces a BOM. Keep temporary generators and screenshots outside the report repository.
5. Validate every logical batch with `scripts/validate.ps1`; also run available schema/formatting validation. Report inherited failures separately; file-integrity validation alone does not prove a visual renders.
6. Check unsaved state before opening/reloading. `true` or unknown is not permission to discard edits. Resolve manually or use `-AllowDiscardUnsavedChanges` only when the user has authorized discarding that state. Existing explicit session authorization need not be requested again.
7. Follow [references/desktop-bridge.md](references/desktop-bridge.md). Reload with `scripts/reload-and-screenshot.ps1`, using explicit report selection when multiple Desktop instances are open. The native warning handler is **off by default**; `-ConfirmMultipleSourceWarning` is permitted only after this user authorizes this exact multiple-data-source warning. Do not use screen takeover, mouse clicks, blind Enter, or changes to security/privacy settings for this routine.
8. After the final edit loads, capture affected pages with the supplied helper and open **every saved PNG**. If reload completed separately, use `-NoReload` to capture in a separate command. Capture all pages for report-wide changes. Check complete text, clipping, layout, binding errors, filter context, intended formatting, and the external-changes banner. An API success or accessibility text is insufficient. Block visual verification if data or Desktop is unavailable.
9. Reconcile KPIs to an independent expected value when source access exists; otherwise compare against separately calculated loaded rows and disclose the cached-data limitation. Do not refresh data merely for a formatting change. For drillthrough, test the actual source context menu, destination, carried filters, row-grain totals, and Back action when possible. Verify every supported source visual and document any untested interaction.
10. Review the changed page against the Definition of Done. Review the Git diff. Only after the last file write has loaded and screenshot review passes, ask the developer to save in Desktop. After saving, inspect the diff and confirm intended MCP changes reached TMDL; do not revert someone else's changes.

## References

- [references/workflow.md](references/workflow.md): business question through delivery.
- [references/gotchas.md](references/gotchas.md): operational and DAX pitfalls; read before first file edit.
- [references/desktop-bridge.md](references/desktop-bridge.md): PBIR reload, native warning confirmation, screenshots, troubleshooting.
- [references/design-standard.md](references/design-standard.md): optional team configuration and storytelling.
- [references/definition-of-done.md](references/definition-of-done.md): chart choice and deterministic PBIR review.

Data sources remain read-only. Ask before deleting/renaming model objects, changing an existing theme, or sharing/publishing unless the user already authorized that action. Report structural validation and visual verification separately, link the reviewed screenshot, and state practical limitations.
