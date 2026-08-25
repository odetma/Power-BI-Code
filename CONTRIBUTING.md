# Contributing

Thanks for improving this Power BI resource collection.

## Guidelines

- Keep examples focused and reusable.
- Add short usage notes when introducing a new snippet.
- Use clear file names with extensions, such as `.dax`, `.tmdl`, `.md`, `.json`, or `.csx`.
- Avoid committing generated files, local exports, credentials, PBIX files with private data, or environment-specific paths unless the file is intentionally a public sample.
- Prefer small pull requests grouped by topic.

## Suggested Structure

- DAX snippets: `dax/`
- TMDL/model snippets: `tmdl/`
- Scripts: `scripts/`
- Prompts: `prompts/`
- AI skills/resources: `skills/`

## Validation

Before opening a pull request, check the relevant file type:

- DAX/TMDL: paste into a test model or validate with your normal Power BI tooling.
- JSON themes: validate JSON syntax.
- Python scripts: run `python -m py_compile <file>`.
- GitHub Actions: verify paths and permissions.
