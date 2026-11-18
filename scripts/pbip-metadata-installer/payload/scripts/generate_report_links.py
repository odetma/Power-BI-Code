"""Enrich generated PBIP docs with read-only Power BI workspace metadata.

Uses existing GitHub credentials. No App API, Workato, or model queries.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

API = 'https://api.powerbi.com/v1.0/myorg'
def strip_service_blocks(doc):
    lines, fence, service = [], None, False
    for line in doc.splitlines(keepends=True):
        stripped = line.rstrip('\r\n')
        match = re.match(r'^(`{3,})', stripped)
        if match:
            if fence is None:
                fence = match.group(1)
            elif stripped == fence:
                fence = None
        if fence is None and stripped == '<!-- service:start -->':
            service = True
            continue
        if service and stripped == '<!-- service:end -->':
            service = False
            continue
        if not service:
            lines.append(line)
    if service:
        raise ValueError('Unclosed service metadata block')
    return ''.join(lines)


def guid(value):
    return str(uuid.UUID(str(value)))


def request(url, token=None, data=None):
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers, data=data), timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                delay = exc.headers.get('Retry-After', '')
                time.sleep(min(int(delay), 30) if delay.isdigit() else 2 ** attempt)
                continue
            # Never print tokens, secrets, or response bodies into logs.
            raise RuntimeError(f'Microsoft API returned HTTP {exc.code}; check credentials, tenant API setting and workspace access.') from None
        except urllib.error.URLError:
            if attempt == 3:
                raise RuntimeError('Could not reach Microsoft API.') from None
            time.sleep(2 ** attempt)


def get_token():
    names = ('AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET')
    missing = [n for n in names if not os.environ.get(n, '').strip()]
    if missing:
        raise ValueError('Missing environment settings: ' + ', '.join(missing))
    tenant = guid(os.environ['AZURE_TENANT_ID'].strip())
    body = urllib.parse.urlencode(dict(client_id=guid(os.environ['AZURE_CLIENT_ID'].strip()),
        client_secret=os.environ['AZURE_CLIENT_SECRET'], grant_type='client_credentials',
        scope='https://analysis.windows.net/powerbi/api/.default')).encode()
    return request(f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token', data=body)['access_token']


def parse_mapping(raw):
    mapping = json.loads(raw)
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('WORKSPACE_MAPPING must be a non-empty JSON object.')
    return {str(k): guid(v.get('id') if isinstance(v, dict) else v) for k, v in mapping.items()}


def list_reports(workspace, token):
    url = f'{API}/groups/{workspace}/reports'
    reports = []
    while url:
        # Do not forward a bearer token to an arbitrary pagination host.
        if not url.startswith(API + '/'):
            raise ValueError('Unexpected Power BI pagination URL')
        payload = request(url, token=token)
        reports.extend(payload.get('value', []))
        url = payload.get('@odata.nextLink')
    return reports


def enrich(doc, report, workspace):
    clean = strip_service_blocks(doc)
    if report is None:
        block = '<!-- service:start -->\n- Service status: No unique matching published report.\n<!-- service:end -->\n'
    else:
        rid = guid(report['id'])
        link = f'https://app.powerbi.com/groups/{workspace}/reports/{rid}'
        rows = ['<!-- service:start -->', f'- Link: {link}', f'- Report ID: {rid}',
                f'- Report workspace ID: {workspace}']
        if report.get('datasetId'):
            rows.append(f"- Dataset ID: {guid(report['datasetId'])}")
        # Thin reports can point at a dataset in a different workspace.
        if report.get('datasetWorkspaceId'):
            rows.append(f"- Dataset workspace ID: {guid(report['datasetWorkspaceId'])}")
        rows += ['- Link type: Workspace (requires access).', '<!-- service:end -->']
        block = '\n'.join(rows) + '\n'
        # Only page headings outside fenced code are eligible for link injection.
        lines, fence = [], None
        for line in clean.splitlines(keepends=True):
            stripped = line.rstrip('\r\n')
            match = re.match(r'^(`{3,})', stripped)
            if match:
                if fence is None:
                    fence = match.group(1)
                elif stripped == fence:
                    fence = None
            lines.append(line)
            if fence is None and stripped.startswith('Page ID: '):
                page = stripped[len('Page ID: '):]
                lines.append('<!-- service:start -->\nPage link: ' + link + '?pageName=' + urllib.parse.quote(page, safe='') + '\n<!-- service:end -->\n')
        clean = ''.join(lines)
    if '## General\n' not in clean:
        raise ValueError('Generated report has no General section')
    return clean.replace('## General\n', '## General\n' + block, 1)


def build_updates(docs, manifest, mapping, inventories, overrides):
    # Windows short/long directory aliases must produce one consistent key form.
    docs = docs.resolve()
    updates, index = {}, ['# Published report links', '', 'Workspace links require access. Matching is scoped to a workspace.', '']
    missing = []
    datasets = ['# Report dataset IDs', '', 'Report workspace IDs do not establish dataset location.', '']
    local_counts = defaultdict(int)
    for item in manifest:
        local_counts[(item['workspace'], item['name'])] += 1
    for item in manifest:
        folder = item['workspace']
        if folder not in mapping:
            raise ValueError(f'Missing WORKSPACE_MAPPING entry for {folder}')
        reports = inventories[folder]
        override = overrides.get(item['source'])
        if override:
            matches = [r for r in reports if r['id'] == guid(override)]
        else:
            matches = [r for r in reports if r.get('name') == item['name']] if local_counts[(folder, item['name'])] == 1 else []
        report = matches[0] if len(matches) == 1 else None
        path = (docs / item['document']).resolve()
        path.relative_to(docs.resolve())
        updates[path] = enrich(path.read_text(encoding='utf-8'), report, mapping[folder])
        if report:
            link = f"https://app.powerbi.com/groups/{mapping[folder]}/reports/{guid(report['id'])}"
            index.append(f"- [{item['source']}]({link})")
            datasets.append(f"- {item['source']} — Dataset ID: {report.get('datasetId') or 'Unavailable'} — Report workspace ID: {mapping[folder]} — Dataset workspace ID: {report.get('datasetWorkspaceId') or 'Not returned by API'}")
        else:
            missing.append(item['source'])
            index.append(f"- {item['source']}: no unique published match; no link assigned.")
    updates[docs / 'report_links.md'] = '\n'.join(index) + '\n'
    updates[docs / 'report_datasets.md'] = '\n'.join(datasets) + '\n'
    updates[docs / 'service-status.json'] = json.dumps(dict(matched=len(manifest)-len(missing), unmatched=missing), ensure_ascii=False, indent=2) + '\n'
    return updates, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', type=Path, default=Path('output'))
    args = parser.parse_args()
    mapping = parse_mapping(os.environ.get('WORKSPACE_MAPPING', ''))
    overrides = json.loads(os.environ.get('REPORT_MAPPING', '') or '{}')
    if not isinstance(overrides, dict):
        raise ValueError('REPORT_MAPPING must be an object keyed by report source path.')
    manifest = json.loads((args.dir / 'manifest.json').read_text(encoding='utf-8'))
    token = get_token()
    inventories = {folder: list_reports(wid, token) for folder, wid in mapping.items()}
    # Fetch and validate every workspace before changing any docs.
    updates, missing = build_updates(args.dir, manifest, mapping, inventories, overrides)
    for path, content in updates.items():
        path.write_text(content, encoding='utf-8')
    print(f'Service metadata: {len(manifest)-len(missing)} matched, {len(missing)} unmatched.')
    if missing:
        print('Unmatched reports: ' + ', '.join(missing))


if __name__ == '__main__':
    main()
