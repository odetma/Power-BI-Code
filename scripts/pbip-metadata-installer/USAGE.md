# Using PBIP metadata documentation

## Generate a local preview

From the installed destination repository:

```sh
python .pbip-metadata/scripts/generate_pbip_md.py --out pbip-metadata-output
```

The output folder must be new or empty. Choose another `--out` path for another
preview. This prevents obsolete documents from surviving a regeneration.
Source folders are read from `.pbip-metadata/config.json`.

## Enable optional Power BI Service enrichment

Local metadata works without credentials. Service enrichment adds workspace
links and published IDs; it does not query business data or refresh models.

1. In the [Entra admin center](https://entra.microsoft.com), select the tenant
   that contains your Power BI workspaces.
2. Open **Entra ID > App registrations > New registration**. Enter your own app
   name, select **Single tenant**, leave Redirect URI empty and register.
   The portal also creates a service principal under Enterprise applications.
3. Record **Application (client) ID** and **Directory (tenant) ID**. Under
   **Certificates & secrets**, create a client secret and store its **Value**
   directly in GitHub Secrets. The Secret ID is not the credential.
4. Under **Entra ID > Groups**, create a **Security** group with **Assigned**
   membership. Add the application's service principal as a member.
5. Ask a Fabric administrator to allow that group in the tenant setting
   **Service principals can call Fabric public APIs** (older interfaces call it
   **Allow service principals to use Power BI APIs**).
6. Grant the service principal access to the required Power BI workspaces using
   **Manage access**. Choose the role with your administrator; Microsoft's
   documented service-principal setup uses Member or Admin, which includes
   write permissions. The scripts themselves only read workspace metadata.
7. In your repository, open **Settings > Secrets and variables > Actions** and
   add the configuration below. Set `service_enrichment` to `true` in
   `.pbip-metadata/config.json`, then commit the change.

| Name | GitHub type | Value |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | Variable | Your application/client ID |
| `AZURE_TENANT_ID` | Variable | Your directory/tenant ID |
| `AZURE_CLIENT_SECRET` | Secret | Your client secret **value** |
| `WORKSPACE_MAPPING` | Variable | JSON mapping top-level repository folders to workspace IDs |
| `REPORT_MAPPING` | Optional variable | JSON mapping report source paths to published report IDs |

Use repository-level variables/secrets. Environment-scoped secrets require an
explicit `environment:` declaration in the workflow and are not used by default.
The two identity IDs may also be stored as secrets. Never commit credential
values into configuration files.

Example mapping, with placeholders that you must replace:

```json
{"Finance": "<WORKSPACE_ID>", "Operations": "<ANOTHER_WORKSPACE_ID>"}
```

The workspace ID is the segment after `/groups/` in its Power BI URL. For reports
at the repository root, use `{"_root": "<WORKSPACE_ID>"}`.

No Power BI API permissions need to be added to the App Registration for this
service-principal path; access is governed by the tenant setting and workspace
permissions. See [Microsoft's service-principal guide](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-service-principal)
and [Fabric developer settings](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer).

## Run and find the output

After the installed files reach the default branch, open **Actions > PBIP
Metadata Documentation > Run workflow**. The workflow also runs on relevant
source changes and daily at **05:00 UTC**. Change the cron in the installed
workflow if you need a different time.

- **PR run:** unit tests and local generation only; download the `pbip-metadata`
  artifact from the completed run. No service credentials are used on PRs.
- **Default-branch run:** generation, optional service enrichment and publication
  to the configured documentation branch (default: `pbip-metadata`).
- **Published files:** switch to that branch and open `metadata/README.md`.
  Per-report files retain the original folder hierarchy beneath `metadata/`.
- **With service enabled:** `report_links.md`, `report_datasets.md` and
  `service-status.json` provide published links, IDs and match results.

Workspace links require the reader to have access. These are not Power BI App
links. App membership is never assumed. Dataset IDs do not establish dataset
location; cross-workspace dataset IDs are included only when returned by the API.

Matching uses the exact report name within the mapped workspace. For renamed or
ambiguous reports, set `REPORT_MAPPING`, for example:

```json
{"Finance/Local Report.Report": "<PUBLISHED_REPORT_ID>"}
```

Unmatched reports are documented without an invented link. Check
`service-status.json` for details.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing environment settings | Repository-level secret/variable names and spelling |
| Authentication fails | Tenant/client IDs, secret value vs. Secret ID, and secret expiry |
| API returns 401/403/404 | Tenant setting, group membership, workspace access, correct workspace ID and propagation delay |
| No matching reports | Exact published names, correct workspace mapping, or `REPORT_MAPPING` |
| Publication fails | GitHub Actions permissions and rules protecting the documentation branch |
| Output directory is not empty | Choose a new preview directory |
| Installer refuses an existing file | Compare against your version; use upgrade only for unchanged managed files |
| Default branch renamed | Update the installed workflow's push branch filter |

An API or parsing failure stops publication; the last successful published
documentation remains available. Preview artifacts may still be uploaded on a
failed run, so check the run status before using them. Rotate the GitHub secret
before it expires.

The generator reads schema and expressions, not actual model values. It cannot
answer live business questions or report refresh status. Multiline code and
descriptions are preserved using TMDL indentation/fence boundaries; malformed
JSON and unclosed TMDL fences fail visibly.
