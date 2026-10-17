# Gotchas: mistakes already made

Read this before your first file edit in a session. Add new entries when you hit one.

## Desktop and files (the costliest)
1. **Order: write files -> reload Desktop -> developer saves.** A Ctrl+S before the reload overwrites your files with Desktop's in-memory report. A reload also discards unsaved Desktop edits, so ask before reloading if the developer may have edited in Desktop.
2. **`hasUnsavedChanges` is not universally always true.** Tested Desktop sessions returned both true and false. Treat true or unknown as a stop unless the developer authorizes discarding in-memory state; do not bypass it based on an assumed Desktop quirk.
3. **A save after MCP model edits can write a stale model.** After every save, grep the TMDL for your change.
   - Fix: `database_operations` ExportToTmdlFolder -> copy over `definition/` -> close Desktop without saving -> reopen.
4. **Desktop rewrites files nobody touched** on save. Check `git diff` before every commit for:
   - connector options re-added to data sources (e.g. an `Implementation="..."` option). Some of these change how the published report behaves, so revert what you didn't intend.
   - `cultures/*.tmdl`
   - `pages.json` activePageName
   - `$schema` bumps, z-order/tabOrder
   - empty `filterConfig`
5. **The Desktop port changes on every restart.** Reconnect the MCP with ListLocalInstances. `HOST_UNAVAILABLE` / timeouts right after MCP changes mean Desktop is busy; wait and retry.
6. **Hidden leftover `PBIDesktop` / Mashup processes** block installers and confuse tools. Check with `Get-Process PBIDesktop`, and close them only when the developer confirms nothing is open.
7. **Never write report/model files with PowerShell 5 `Set-Content -Encoding UTF8`.** It adds a BOM, and Desktop rejects the file: "Only text with UTF8 encoding without BOM is supported". Use Python, the Edit tool, or `[IO.File]::WriteAllText(path, text, [Text.UTF8Encoding]::new($false))`. Keep the file's line endings.
8. **An open Desktop dialog can block bridge calls.** The exact multiple-source warning can use the opt-in native handler after explicit user authorization (see `desktop-bridge.md`); other dialogs require manual handling.
9. **Screenshot right after a reload = blank page.** Wait about 10 s (the script does).
10. **Never use the bridge's screenshot (`powerbi-desktop screenshot`).** See `desktop-bridge.md`.
11. **The first bridge reload right after a file change often fails** with "Host is not ready to accept operations". Wait a few seconds and retry (the script retries once). If it still fails, check for an open dialog or a field in edit mode.
12. **A bridge reload keeps Desktop's in-memory UI state:** the current page, and slicer and button selections. A new default selection in the file shows only after the file is reopened.
13. **A broken visual stays in Desktop's memory.** Invalid formatting can render a visual blank without an error. After you fix the file, the next reload can still throw "An error occurred while rendering the report" from the old copy. Close the dialog, reload again, and don't save in between.
14. **To see the lower part of a tall page in one screenshot,** set the page's `displayOption` to `FitToPage` temporarily, reload, capture, then restore it.

## MCP and model
15. **Renaming a table via MCP** fixes DAX and NAMEOF, but NOT these, so patch them yourself: report JSON references, M queries that reference another query by name, field-parameter slicer literals (`''Table''[Col]`). Desktop may also drop field-parameter projections on save.
16. **Field parameters:** changing their partition while visuals use them can crash Desktop; after any calculated-table partition change, Refresh `Calculate`; the first save after adding one is slow.
17. **New calc column or table:** Refresh `Calculate` before querying it ("needs to be recalculated"). A brand-new table's first refresh may fail with PackageSession, so retry.
18. **One failing item rolls back the whole batch** (transactions). Resend items separately.
19. **Measure Update requires the full expression.** Get -> edit -> Update. Keep repeated text in its own measure.
20. **Sort-by column computed from the column it sorts** -> circular dependency. Make a display copy of the column, sort the copy by an order column computed from the source column, and use the copy in visuals. Better: put the order column in the source table.
21. **A failed MCP transaction can poison the connection:** later operations fail with "The base version must not be negative" or "Server object is not connected". Disconnect, Connect again.
22. **Creating a field parameter via MCP:**
    1. table_operations Create with `daxExpression` = `{ ("Label", NAMEOF('T'[Col]), 0), ... }`
    2. rename the columns `Value1`-`Value3`
    3. column Update: the fields column gets `extendedProperties` `ParameterMetadata` = `{"version":3,"kind":2}` and is hidden, the label column gets `groupByColumns` = the fields column, and both sort by the order column

    In a chart, keep a normal projection of the default column and add `fieldParameters: [{parameterExpr, index: 0, length: 1}]` next to `projections`. When the views need different values, use one measure that checks `ISINSCOPE(<view column>)`.

## DAX
23. **KEEPFILTERS:** a CALCULATE filter on the same column as the axis or legend overrides it, so every bar shows the same number. Wrap it in KEEPFILTERS.
24. **In a matrix, the sort-by column is grouped too.** Use ALLSELECTED over both columns (e.g. month name + month number).
25. **A calc column that CALCULATEs over its own table** is slow or circular. Use a small mapping table and a relationship.
26. **`RELATED` doesn't work inside CALCULATE filter arguments.** Use `COUNTROWS(FILTER(table, ... RELATED(...)))`.
27. **Cross-filter honesty:** a bar's value must equal the rows the details table shows when it's clicked. Put the scope into the axis column (blank outside the scope).

## PBIR JSON (validation and rendering)
28. **Formatting that breaks or misbehaves:**
    - visual tooltips: `visualTooltip.type` must be `'Canvas'`, plus `section` = the tooltip page name. A tooltip page has `"type":"Tooltip"`, `"visibility":"HiddenInViewMode"`, 320x240.
    - invalid: `items.outline`, `columnTotal/rowTotal show`
    - `secShow` is valid only on combo charts
    - combo column color needs `dataPoint.defaultColor`
    - data-label `backgroundColor`: `{solid:{color}}` fails validation, and as a Literal it renders dark. Don't use label backgrounds.
    - subtitles ignore line breaks
    - in the HTML Content visual, vertical centering doesn't work; use fixed padding
29. **Relative "Calendar weeks" slicer** throws InvalidBinaryFilterConditionExpression. Use Relative "Last N weeks" on a week-end date column with `includeToday` false.
30. **Hierarchy slicers open expanded** unless `expansionStates` lists every level with `isCollapsed: true` and `root: {}`.
31. **A table visual with only columns** builds its rows under the date filter. A measure that ignores dates makes it load every row.
32. **Python on Windows:** glob returns backslash paths. Use `os.path`, not `split('/')`.
33. **A slicer's selection (its default)** lives in `visual.objects.general[0].properties.filter.filter` (Version/From/Where). `filterConfig` only declares the field; a selection written there is ignored.
34. **Gradient (FillRule `linearGradient2`) values** are bare `{"Literal": ...}` for `min`/`max` `color` and `nullColoringStrategy` `strategy`, with no `expr` wrapper. The wrapped form renders the visual blank.
35. **Matrix/table totals in an odd font:** a theme without `pivotTable`/`tableEx` total styles falls back to the `header` text class. Set `rowTotal`/`columnTotal` (matrix) and `total` (table) `fontFamily` in the theme.

## Desktop Bridge
36. **The pinned CLI's normal reload command refuses reports opened from `definition.pbir`.** Use `scripts/pbir-reload.mjs`; it also supports an already-open PBIP project. Creating a launcher is not required.
37. **Screenshots show the visible window only.** A minimized window can't be captured or navigated; the scripts restore it first.

## Numbers
38. **Reconcile against data with known freshness:** stale cached data can look like a definition bug. Refresh external sources only when authorized and necessary; otherwise disclose that checks use loaded Desktop data.
39. **Warehouse grouping may be case-sensitive, Power BI's isn't.** Check casing variants of names.
40. **Derived is not a source field:** never tell stakeholders a computed column is a field in the source system.
41. **Check free-text key columns and data maturity** before trusting a flag or a recent month.
42. **Hardcoded texts drift:** a tooltip once described an outdated SLA. Build texts from measures or a targets table.

## Portable authoring lessons

43. **Native UIA and managed UIA are not equivalent for every provider.** The embedded legacy browser warning exposed its controls through CUIAutomation8, while managed UIA returned unnamed panes. Use the supplied native helper; do not guess coordinates or take over the screen. Win32 GetWindowRect is used because UIA returned empty bounds during some reloads.
44. **Capture must not simulate Alt or steal foreground focus.** The earlier Alt workaround left ribbon keyboard hints visible. PrintWindow capture now uses thread-local DPI awareness without keyboard/foreground calls. A minimized window is only restored explicitly.
45. **Button formatting needs two entries.** For text/fill/icon/effect objects, put `show` in an unselectored entry and styling in a separate entry with `selector: {id: "default"}`. Mixing both in either one entry can yield an invisible label or default formatting even when validation passes.
46. **Test drillthrough from each source.** A model-only destination did not appear on a month line chart. Binding the exact month field as another parameter enabled the month route while preserving the product route; both were tested. Keep source year/context and reconcile the transaction table using a verified unique order/line key.
47. **Reference-series drillthrough can be misleading.** A prior-year measure on a selected-year axis may pass the selected year to detail. Explicitly label the selected-year route; a period-aware prior-year route needs separate implementation and testing.
48. **A prior-year comparison can lose leap day.** Shifting each non-leap-year date backward can omit February 29 from the comparison year. Full-month/full-year comparisons should include the complete comparison periods; partial-period definitions need their own agreed rules.
49. **Measure names are not definitions.** A measure named Orders summed quantity in the test model. Inspect DAX and verify distinct order identifiers before labeling a KPI. An unmatched quota date relationship also made attainment unusable.
50. **A saved PNG is required evidence.** Review the image after the final write/reload, not merely a transient UI snapshot. A main-window PrintWindow capture can omit a blocking dialog; also inspect window/handler state. File, schema, rendering, and business-number checks establish different things.
