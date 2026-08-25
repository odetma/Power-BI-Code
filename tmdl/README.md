# TMDL

Power BI TMDL examples for semantic models and advanced measures.

## Contents

| File | Purpose |
| --- | --- |
| [`date-table/dw-dim-date-view.tmdl`](date-table/dw-dim-date-view.tmdl) | Calculated date table with common calendar attributes and sort columns. |
| [`functions.tmdl`](functions.tmdl) | Example model functions for reusable DAX logic such as SPLY, previous month, and VAT. |
| [`html-measures/rtl-matrix-table.tmdl`](html-measures/rtl-matrix-table.tmdl) | RTL-friendly HTML matrix/table measure with drill behavior. |
| [`html-measures/full-dashboard-html.tmdl`](html-measures/full-dashboard-html.tmdl) | Full-page interactive HTML dashboard measure. |

## Usage Notes

- Review table, column, and measure names before pasting into your model.
- HTML measures should be tested in your report layout and target Power BI environment.
- TMDL snippets may include lineage tags from the original model. Remove or regenerate them if needed for your workflow.
