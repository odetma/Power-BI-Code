# Scripts

Automation and helper scripts for Power BI development.

## Contents

| File | Purpose |
| --- | --- |
| [`tabular-editor/export-model-metadata.csx`](tabular-editor/export-model-metadata.csx) | Tabular Editor C# script that exports tables, columns, measures, partitions, relationships, functions, and roles into a text file. |

## Usage Notes

- Update local paths inside the script before running it.
- Run from Tabular Editor against the model you want to inspect.
- Review output before sharing, because model metadata may include sensitive business logic or source queries.
