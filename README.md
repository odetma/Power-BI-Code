# Power BI Code

Reusable Power BI snippets, PBIP utilities, prompts, and theme-building resources shared by Odet Maimoni.

This repository is meant to accompany tutorials and posts. Each folder contains copy-ready examples that you can adapt to your own Power BI models, reports, and automation workflows.

## What's Inside

| Area | Folder | Use it for |
| --- | --- | --- |
| DAX functions | [`dax/`](dax/) | Reusable DAX query functions, especially time-intelligence helpers. |
| TMDL examples | [`tmdl/`](tmdl/) | Date table definitions, model functions, and HTML-measure examples. |
| Scripts | [`scripts/`](scripts/) | Tabular Editor and automation scripts for Power BI development workflows. |
| Prompts | [`prompts/`](prompts/) | Prompt templates for Power BI QA, report review, and AI-assisted workflows. |
| Theme skill | [`skills/power-bi-theme-style/`](skills/power-bi-theme-style/) | Instructions and starter assets for extracting PBIP styling and creating Power BI theme presets. |
| PBIP change summary | [`.github/workflows/pbip-summary.yml`](.github/workflows/pbip-summary.yml) | GitHub Actions workflow that summarizes PBIP/TMDL/report changes in pull requests. |

## Quick Start

1. Browse the folder that matches your use case.
2. Read the folder-level `README.md` for usage notes.
3. Copy the relevant snippet into your Power BI model, Tabular Editor script, PBIP project, or AI workflow.
4. Replace sample table, column, path, and measure names with your own model names.

## Repository Map

```text
.
├── dax/
│   └── time-intelligence/
├── tmdl/
│   ├── date-table/
│   └── html-measures/
├── scripts/
│   └── tabular-editor/
├── prompts/
├── skills/
│   └── power-bi-theme-style/
└── .github/
    ├── scripts/
    └── workflows/
```

## Highlights

- Safe same-period-last-year DAX logic for incomplete periods and leap years.
- A reusable TMDL date table.
- HTML-based Power BI measures for advanced table/dashboard layouts.
- A Tabular Editor C# script for exporting model metadata.
- A PBIP pull-request summary workflow for reviewers.
- Theme extraction and style preset resources for Power BI custom themes.

## Requirements

Most snippets can be used independently. Depending on the file, you may need:

- Power BI Desktop.
- Tabular Editor 2 or 3 for C# scripts and TMDL workflows.
- A PBIP project if using the PBIP change summary workflow.
- GitHub Actions enabled if copying the workflow into another repository.

## Notes

- Treat these files as starting points. Validate all code against your own model structure before using it in production.
- Some examples use specific sample table names such as `DIM_DATE`, `DW_DIM_DATE_VW`, `FactSales`, or `DimProduct`. Rename them to match your model.
- HTML measures can be powerful, but they should be tested carefully for performance and rendering behavior in your report environment.

## Contributing

Issues and pull requests are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

## License

This repository is available under the MIT License. See [`LICENSE`](LICENSE).
