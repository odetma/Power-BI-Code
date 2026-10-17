# From business question to delivery

## Understand and inspect

Agree the audience, the page's single business question, and the action its reader can take. Review current pages, native visual templates, theme, relationships, fields, and measure definitions. An implementation request following an approved plan is authorization to implement that scope; do not restart the planning approval loop.

Confirm the actual Desktop file and repository checkout match. Use a feature branch according to repository guidance, preserve existing changes, and discover the current MCP instance/port. Do not silently convert legacy reports or create a PBIP launcher for an existing PBIR report.

## Data and definitions

Use read-only queries and record them in the scratchpad. Check unique keys, transaction grain, period coverage, missing values, and relationship coverage. A quota table connected to an unmatched date bucket is not a valid target comparison. A row count, distinct order count, and sum of quantities answer different questions.

Agree KPI definitions, period/comparison rules, currency basis, cost inclusions, and owner. Show latest transaction date separately from refresh time. Label a derived metric by its rule; do not imply it is an existing source field. Do not imply net profit when only sales and product cost are known.

## Model and PBIR

Use MCP for authorized model changes; read existing expressions before updating. A model change in Desktop memory is not yet a persisted TMDL change. Export/persist only intended changes and verify after the developer saves. Do not reload a stale disk model over unsaved MCP edits.

Use supported metadata for visual roles and formatting. Preserve schema versions, IDs, model references, registrations, and unaffected files. Native visuals provide filtering, drillthrough, and accessibility; prefer them when they meet the design. Use UTF-8 without BOM and preserve line endings. Keep generators and screenshots outside the report repository.

## Drillthrough

Bind the exact source column in the target page's `filterConfig` and `pageBinding.parameters`, with `acceptsFilterContext: Default` when source filters should flow. A product chart and a month chart need their respective source fields bound. Verify availability from **each** source visual; inspect actual carried year/month/product filters rather than assuming configuration proves behavior.

Use a hidden destination, Back action, readable context header, and an intentional transaction grain. Include the unique order/line keys to prevent unwanted aggregation. Show counts and totals that reconcile to the loaded rows. Allow horizontal scrolling for supporting fields; make the primary identifying fields visible first.

A prior-year measure on a selected-year axis can still pass the selected-year filter. Label selected-year transaction details explicitly; never imply they are the rows underlying the prior-year reference line without a tested period-aware route.

## Verification and save

Validate logical edit batches, then follow [desktop-bridge.md](desktop-bridge.md) for unsaved-state handling, opt-in dialogs, reload, saved PNGs, and visual review. Check interactions as well as appearance. Do not refresh external data without task authorization; distinguish source reconciliation from checks of the existing Desktop cache.

Run the Definition of Done for affected pages. Review the diff. After the last edit has loaded and screenshot review passes, ask the developer to save. Inspect the resulting diff and confirm intended measures reached disk. Deliver scope, validation, visual evidence, untested items, and limitations. Commit, push, publish, and create PRs only when authorized by the task.
