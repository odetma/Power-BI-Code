# Scripts

Automation and helper scripts for Power BI development.

## Contents

| File | Purpose |
| --- | --- |
| [`pbip-metadata-installer/`](pbip-metadata-installer/) | Install generated PBIP Markdown documentation and a GitHub Actions publishing workflow; optional service metadata. |
| [`tabular-editor/export-model-metadata.csx`](tabular-editor/export-model-metadata.csx) | Tabular Editor C# script that exports tables, columns, measures, partitions, relationships, functions, and roles into a text file. |

## Usage Notes

- Update local paths inside the script before running it.
- Run from Tabular Editor against the model you want to inspect.
- Review output before sharing, because model metadata may include sensitive business logic or source queries.

## PBIP documentation installer

Start with the [installation guide](pbip-metadata-installer/README.md). The installer discovers source folders, supports dry runs and backups, and preserves multiline DAX/M and descriptions. Optional Power BI credentials are configured in the destination repository, never bundled here.
