from pathlib import Path
import json
import re
import argparse
from urllib.parse import quote
from tmdl_metadata import parse_tmdl_table, parse_inline_property

repo_root = Path(".")

IGNORED_MODEL_TABLES = {
    "Model Measures List",
    "Model Relationships List",
    "Model Tables List",
}

IGNORED_VISUAL_TYPES = {
    "shape",
    "image",
    "actionButton",
    "textbox",
    "Unknown",
}

IGNORED_FIELD_EXACT = {
    "developer.microsoft",
    "schema.json",
    "notebooklm.google",
}

IGNORED_FIELD_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".json",
)

SKIP_PAGE_NAMES = {
    "model info",
}

MODEL_REF_PATTERN = re.compile(r"^[\w ]+\.[\w $#()/\-]+$", re.UNICODE)


def read_text(path):
    return path.read_text(encoding="utf-8-sig")


def safe_json(path):
    # Invalid source files must fail generation, not masquerade as empty metadata.
    return json.loads(read_text(path))


def code_block(value, language=""):
    fence = "`" * max(3, 1 + max((len(x) for x in re.findall(r"`+", value)), default=0))
    return f"{fence}{language}\n{value}\n{fence}"


def relative_path(path):
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


SKIP_DIRS = {".git", ".claude", ".pbip-metadata", "node_modules", ".venv", "venv"}


def find_reports(roots=(".",)):
    reports = []
    for root in roots:
        source = (repo_root / root).resolve()
        source.relative_to(repo_root.resolve())
        if not source.is_dir():
            raise ValueError(f"Missing source directory: {root}")
        for report_path in sorted(source.rglob("*.Report")):
            if not report_path.is_dir() or any(part in SKIP_DIRS for part in report_path.parts):
                continue
            name = report_path.name.removesuffix(".Report")
            binding_file = report_path / "definition.pbir"
            binding = safe_json(binding_file).get("datasetReference", {}) if binding_file.exists() else {}
            model = None
            if "byPath" in binding:
                model = (report_path / binding["byPath"]["path"]).resolve()
                model.relative_to(repo_root.resolve())
                if not model.is_dir():
                    raise ValueError(f"Missing bound model: {relative_path(report_path)}")
            elif not binding:
                candidate = report_path.parent / f"{name}.SemanticModel"
                model = candidate if candidate.is_dir() else None
            rel = relative_path(report_path)
            doc = report_path.relative_to(repo_root.resolve()).with_suffix('.md').as_posix()
            reports.append(dict(name=name, report_path=report_path, model_path=model,
                                source=rel, document=doc, workspace=rel.split('/')[0] if '/' in rel else '_root'))
    unique = {r['source']: r for r in reports}
    return [unique[k] for k in sorted(unique)]


_SNOWFLAKE_FQ_RE = re.compile(
    r"\bfrom\s+\"?([A-Za-z0-9_]+)\"?\.\"?([A-Za-z0-9_]+)\"?\.\"?([A-Za-z0-9_]+)\"?",
    re.IGNORECASE,
)


def extract_snowflake_source(expr: str | None):
    """Best-effort fully-qualified Snowflake object (DB.SCHEMA.OBJECT) from a
    Power Query M source, handling both native SQL and step navigation."""
    if not expr:
        return None
    # 1) native SQL: "... from DB.SCHEMA.TABLE ..."
    m = _SNOWFLAKE_FQ_RE.search(expr)
    if m:
        return ".".join(m.groups())
    # 2) Snowflake.Databases(...) navigation: {[Name="X",Kind="Database|Schema|View|Table"]}
    parts = {}
    for name, kind in re.findall(r'\[Name="([^"]+)"\s*,\s*Kind="([^"]+)"\]', expr):
        parts.setdefault(kind.lower(), name)
    chain = [p for p in (parts.get("database"), parts.get("schema"),
                         parts.get("view") or parts.get("table")) if p]
    if len(chain) >= 2:
        return ".".join(chain)
    return None


def describe_partition(p: dict):
    """One-line, human summary of where a partition's data comes from."""
    mode = (p.get("mode") or "").lower()
    kind = (p.get("kind") or "").lower()
    if kind == "entity" or mode == "directquery":
        # Use the referenced model name when the source provides one.
        summary = p.get("expression_source") or "DirectQuery"
        if p.get("entity_name"):
            summary += f" (entity: {p['entity_name']})"
        return summary
    if kind == "calculated":
        return "Calculated table (DAX)"
    if kind in ("m", "query") or p.get("expression"):
        return "Power Query (M)"
    return None


def extract_model_tables(model_path: Path | None):
    if not model_path:
        return []

    tables_folder = model_path / "definition" / "tables"
    if not tables_folder.exists():
        return []

    tables = []
    for table_file in sorted(tables_folder.glob("*.tmdl"), key=lambda p: p.name.lower()):
        parsed = parse_tmdl_table(table_file)
        for partition in parsed['partitions']:
            partition['snowflake_table'] = extract_snowflake_source(partition.get('expression'))
        if parsed["table_name"] in IGNORED_MODEL_TABLES:
            continue
        tables.append(parsed)
    return tables


def extract_model_roles(model_path: Path | None):
    roles = []
    if not model_path:
        return roles

    roles_folder = model_path / "definition" / "roles"
    if not roles_folder.exists():
        return roles

    for rf in sorted(roles_folder.glob("*.tmdl"), key=lambda p: p.name.lower()):
        roles.append({
            "name": rf.stem,
            "content": read_text(rf),
        })
    return roles


def extract_model_functions(model_path: Path | None):
    if not model_path:
        return None

    functions_file = model_path / "definition" / "functions.tmdl"
    if functions_file.exists():
        return read_text(functions_file)
    return None


def extract_relationships(model_path: Path | None):
    relationships = []
    if not model_path:
        return relationships

    rel_file = model_path / "definition" / "relationships.tmdl"
    if not rel_file.exists():
        return relationships

    text = read_text(rel_file)
    blocks = re.split(r"\n(?=relationship\b)", text, flags=re.IGNORECASE)

    for block in blocks:
        b = block.strip()
        if not b.lower().startswith("relationship"):
            continue

        relationships.append({
            "from": parse_inline_property(b, "fromColumn"),
            "to": parse_inline_property(b, "toColumn"),
            "active": parse_inline_property(b, "isActive"),
            "cross_filter": parse_inline_property(b, "crossFilteringBehavior"),
        })

    return relationships


def parse_visual_type(data: dict):
    candidates = [
        data.get("visualType"),
        data.get("visual", {}).get("visualType") if isinstance(data.get("visual"), dict) else None,
        data.get("singleVisual", {}).get("visualType") if isinstance(data.get("singleVisual"), dict) else None,
        data.get("visualContainer", {}).get("singleVisual", {}).get("visualType")
            if isinstance(data.get("visualContainer"), dict) else None,
        data.get("config", {}).get("singleVisual", {}).get("visualType")
            if isinstance(data.get("config"), dict) else None,
    ]

    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()

    raw = json.dumps(data, ensure_ascii=False)
    for t in [
        "slicer",
        "card",
        "cardVisual",
        "lineChart",
        "clusteredColumnChart",
        "pivotTable",
        "tableEx",
        "matrix",
        "barChart",
        "columnChart",
        "pieChart",
    ]:
        if f'"{t}"' in raw:
            return t

    return "Unknown"


def is_noise_field(value: str):
    v = value.strip()

    if not v:
        return True

    if v in IGNORED_FIELD_EXACT:
        return True

    if v.lower().endswith(IGNORED_FIELD_SUFFIXES):
        return True

    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return True

    if re.fullmatch(r"[0-9A-Fa-f]+\.[0-9A-Fa-f]+", v):
        return True

    if re.fullmatch(r"[0-9.]+D", v, re.IGNORECASE):
        return True

    if "." in v and not MODEL_REF_PATTERN.match(v):
        return True

    return False


def extract_visual_fields_and_filters(data: dict):
    fields = set()
    visual_filters = []

    def walk(obj):
        if isinstance(obj, dict):
            table = None
            column = None
            measure = None

            for k, v in obj.items():
                kl = str(k).lower()

                if kl in {"entity", "table", "tablename"} and isinstance(v, str):
                    table = v
                elif kl in {"property", "column", "columnname"} and isinstance(v, str):
                    column = v
                elif kl in {"measure", "measurename"} and isinstance(v, str):
                    measure = v

            if measure and table:
                fields.add(f"{table}.{measure}")
            elif column and table:
                fields.add(f"{table}.{column}")

            for kind in ("Measure", "Column"):
                reference = obj.get(kind)
                if isinstance(reference, dict):
                    source = reference.get("Expression", {}).get("SourceRef", {})
                    entity, prop = source.get("Entity"), reference.get("Property")
                    if entity and prop:
                        fields.add(f"{entity}.{prop}")

            dumped = json.dumps(obj, ensure_ascii=False)
            if "IsDataExists" in dumped:
                visual_filters.append("IsDataExists = 1")

            for v in obj.values():
                walk(v)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    raw = json.dumps(data, ensure_ascii=False)
    dotted = re.findall(r"\b([\w ]+)\.([\w $#()/\-]+)\b", raw)

    for t, f in dotted:
        candidate = f"{t.strip()}.{f.strip()}"
        if not is_noise_field(candidate):
            fields.add(candidate)

    cleaned_fields = []
    for x in sorted(fields):
        if is_noise_field(x):
            continue
        if (
            x.startswith("Model Measures List.")
            or x.startswith("Model Relationships List.")
            or x.startswith("Model Tables List.")
        ):
            continue
        cleaned_fields.append(x)

    filters_clean = []
    seen = set()
    for f in visual_filters:
        if f not in seen:
            seen.add(f)
            filters_clean.append(f)

    return cleaned_fields, filters_clean


def parse_literal_value(val):
    if isinstance(val, dict):
        literal = val.get("Literal")
        if isinstance(literal, dict):
            raw = literal.get("Value")
            if isinstance(raw, str):
                return raw.strip('"').strip("'")
            return raw
    return val


def extract_filter_items(data, keep_model_lists=False):
    items = []

    def walk_filters(obj):
        if isinstance(obj, dict):
            field_info = obj.get("field")
            filter_info = obj.get("filter")

            if isinstance(field_info, dict):
                entity = None
                prop = None

                col = field_info.get("Column")
                if isinstance(col, dict):
                    prop = col.get("Property")
                    expr = col.get("Expression")
                    if isinstance(expr, dict):
                        src = expr.get("SourceRef")
                        if isinstance(src, dict):
                            entity = src.get("Entity") or src.get("Source")

                if entity and prop:
                    if keep_model_lists or not entity.startswith("Model "):
                        label = f"{entity}.{prop}"

                        values = []
                        if isinstance(filter_info, dict):
                            where = filter_info.get("Where", [])
                            if isinstance(where, list):
                                for w in where:
                                    cond = w.get("Condition", {}) if isinstance(w, dict) else {}
                                    in_node = cond.get("In", {}) if isinstance(cond, dict) else {}
                                    raw_values = in_node.get("Values", [])
                                    if isinstance(raw_values, list):
                                        for row in raw_values:
                                            if isinstance(row, list):
                                                for cell in row:
                                                    values.append(parse_literal_value(cell))

                        if values:
                            pretty_vals = ", ".join(str(v) for v in values)
                            items.append(f"{label} = {pretty_vals}")
                        else:
                            items.append(label)

            for v in obj.values():
                walk_filters(v)

        elif isinstance(obj, list):
            for item in obj:
                walk_filters(item)

    walk_filters(data)

    result = []
    seen = set()
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)

    return result


def extract_report_level_filters(report_path: Path):
    result = []

    candidates = [
        report_path / "definition" / "report.json",
        report_path / "definition" / "filters.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            data = safe_json(candidate)
            if isinstance(data, dict):
                items = extract_filter_items(data, keep_model_lists=True)
                if items:
                    result.append({
                        "name": candidate.name,
                        "items": items,
                    })

    return result


def page_is_hidden(page_json_data: dict | None) -> bool:
    if not isinstance(page_json_data, dict):
        return False

    visibility = str(page_json_data.get("visibility", "")).strip().lower()
    return visibility == "hiddeninviewmode"


def extract_page_level_filters(page_dir: Path):
    result = []

    candidates = [
        page_dir / "page.json",
        page_dir / "filters.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            data = safe_json(candidate)
            if isinstance(data, dict):
                items = extract_filter_items(data, keep_model_lists=True)
                if items:
                    result.append({
                        "name": candidate.name,
                        "items": items,
                    })

    return result


def extract_report_pages_legacy(report_path: Path):
    """Pages for reports still stored as a single report.json (pre-PBIR).

    Everything the newer format keeps in definition/pages lives in the
    "sections" array here. The catch is that each visualContainer stores its
    config as a JSON *string* rather than an object, so it needs a second parse
    before the shared helpers can read it - without that they see nothing and
    the report comes out with no pages at all.
    """
    pages = []
    report_json = report_path / "report.json"
    data = safe_json(report_json) if report_json.exists() else None
    if not isinstance(data, dict):
        return pages

    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue

        display_name = section.get("displayName") or section.get("name") or ""
        if display_name.strip().lower() in SKIP_PAGE_NAMES:
            continue

        section_config = section.get("config")
        if isinstance(section_config, str):
            try:
                section_config = json.loads(section_config)
            except (ValueError, TypeError):
                section_config = None
        if isinstance(section_config, dict) and section_config.get("visibility") == 1:
            continue

        visuals = []
        for container in section.get("visualContainers", []):
            if not isinstance(container, dict):
                continue

            config = container.get("config")
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except (ValueError, TypeError):
                    continue
            if not isinstance(config, dict):
                continue

            visual_type = parse_visual_type(config)
            if visual_type in IGNORED_VISUAL_TYPES:
                continue

            fields, filters = extract_visual_fields_and_filters(config)
            if not fields and not filters:
                continue

            visuals.append({
                "type": visual_type,
                "fields": fields,
                "filters": filters,
            })

        pages.append({
            "page_id": section.get("name") or "",
            "page_name": display_name,
            "page_filters": [],
            "visuals": visuals,
        })

    return pages


def extract_report_pages(report_path: Path):
    pages = []
    pages_root = report_path / "definition" / "pages"
    if not pages_root.exists():
        return extract_report_pages_legacy(report_path)

    for page_dir in sorted([p for p in pages_root.iterdir() if p.is_dir()], key=lambda p: p.name):
        page_name = page_dir.name
        display_name = page_name

        page_json = page_dir / "page.json"
        page_json_data = safe_json(page_json) if page_json.exists() else None

        if isinstance(page_json_data, dict):
            display_name = page_json_data.get("displayName") or page_json_data.get("name") or display_name

        if display_name.strip().lower() in SKIP_PAGE_NAMES:
            continue

        if page_is_hidden(page_json_data):
            continue

        page_filters = extract_page_level_filters(page_dir)

        visuals = []
        visuals_dir = page_dir / "visuals"
        if visuals_dir.exists():
            for visual_dir in sorted([v for v in visuals_dir.iterdir() if v.is_dir()], key=lambda p: p.name):
                visual_json = visual_dir / "visual.json"
                data = safe_json(visual_json) if visual_json.exists() else None

                visual_type = "Unknown"
                fields = []
                filters = []

                if isinstance(data, dict):
                    visual_type = parse_visual_type(data)
                    fields, filters = extract_visual_fields_and_filters(data)

                if visual_type in IGNORED_VISUAL_TYPES:
                    continue

                if not fields and not filters:
                    continue

                visuals.append({
                    "type": visual_type,
                    "fields": fields,
                    "filters": filters,
                })

        pages.append({
            "page_id": page_name,
            "page_name": display_name,
            "page_filters": page_filters,
            "visuals": visuals,
        })

    return pages


def extract_custom_visuals(report_path: Path):
    folder = report_path / "CustomVisuals"
    if not folder.exists():
        return []
    return sorted([p.name for p in folder.iterdir()])


EXTERNAL_MEASURE = re.compile(
    r'EXTERNALMEASURE\(\s*"[^"]*"\s*,[^,]*,\s*"DirectQuery to AS - ([^"]+)"',
    re.IGNORECASE,
)


def owning_model(expression):
    """Identify a measure's originating model from an EXTERNALMEASURE pointer."""
    if not expression:
        return None
    match = EXTERNAL_MEASURE.search(expression)
    return match.group(1).strip() if match else None


def pages_by_field(pages):
    """field reference -> the pages whose visuals use it.

    Answering "which page shows X" means joining the measure list to the page
    listings, and in a large document those sit thousands of lines apart: the
    term is dense where the measure is defined and appears once, buried in a
    field list, where it is actually used. Retrieval goes to the dense end. The
    index is cheap to build here and lets the measure entry carry its own
    answer.
    """
    index = {}
    for page in pages:
        for visual in page.get("visuals", []):
            for field in visual.get("fields", []):
                index.setdefault(field, set()).add(page["page_name"])
    return index


def build_markdown(report_name, report_path, model_path):
    report_filters = extract_report_level_filters(report_path)
    pages = extract_report_pages(report_path)
    custom_visuals = extract_custom_visuals(report_path)

    tables = extract_model_tables(model_path)
    roles = extract_model_roles(model_path)
    functions_text = extract_model_functions(model_path)
    relationships = extract_relationships(model_path)

    field_pages = pages_by_field(pages)

    lines = []
    lines.append(f"# {report_name}")
    lines.append("")
    lines.append("## General")
    lines.append(f"- Report folder: `{relative_path(report_path)}`")
    lines.append(f"- Semantic model folder: `{relative_path(model_path)}`" if model_path else "- Semantic model folder: Not found")
    lines.append("")

    lines.append("## Tables")
    lines.append("==================================================")
    if tables:
        for t in tables:
            lines.append(f"  - {t['table_name']}")
    else:
        lines.append("  No tables found")
    lines.append("--------------------------------------------------")
    lines.append("")

    for t in tables:
        # Keep report context on every table heading for partial-document readers.
        lines.append(f"Table: {t['table_name']}  [{report_name}]")
        lines.append("==================================================")

        if t["description"]:
            lines.append("Description:")
            lines.append(code_block(t["description"], "text"))
            lines.append("")

        lines.append("Columns:")
        if t["columns"]:
            for c in t["columns"]:
                dtype = f" ({c['data_type']})" if c["data_type"] else ""
                lines.append(f"  - {c['name']}{dtype}")
                if c["description"]:
                    lines.append(code_block(c["description"], "text"))
        else:
            lines.append("  None")

        if t["calculated_columns"]:
            lines.append("Calculated Columns:")
            for cc in t["calculated_columns"]:
                dtype = f" ({cc['data_type']})" if cc.get("data_type") else ""
                lines.append(f"  - {cc['name']}{dtype}")
                if cc["description"]:
                    lines.append(code_block(cc["description"], "text"))
                if cc["expression"]:
                    lines.append("    DAX:")
                    lines.append(code_block(cc["expression"], "dax"))

        if t["measures"]:
            lines.append("Measures:")
            for m in t["measures"]:
                lines.append(f"  - {m['name']}")
                if m["description"]:
                    lines.append(code_block(m["description"], "text"))
                if m["display_folder"]:
                    lines.append(f"    Display Folder: {m['display_folder']}")
                if m["format_string"]:
                    lines.append(f"    Format String: {m['format_string']}")
                defined_in = owning_model(m["expression"])
                if defined_in:
                    lines.append(
                        f"    Defined in: {defined_in} - this report only"
                        " displays it, through a live connection"
                    )
                used_on = field_pages.get(f"{t['table_name']}.{m['name']}")
                if used_on:
                    lines.append(f"    Used on pages: {', '.join(sorted(used_on))}")
                if m["expression"]:
                    lines.append("    DAX:")
                    lines.append(code_block(m["expression"], "dax"))

        if t["hierarchies"]:
            lines.append("Hierarchies:")
            for h in t["hierarchies"]:
                lines.append(f"  - {h['name']}")

        if t["partitions"]:
            lines.append("Sources / Partitions:")
            for idx, p in enumerate(t["partitions"], start=1):
                lines.append(f"  Partition {idx}: {p['name']}")
                desc = describe_partition(p)
                if desc:
                    lines.append(f"    Source type: {desc}")
                if p.get("snowflake_table"):
                    lines.append(f"    Snowflake table: {p['snowflake_table']}")
                if p.get("expression"):
                    lines.append(code_block(p["expression"], "powerquery" if p.get("kind") == "m" else "text"))
                elif not desc:
                    lines.append("    (source not captured)")

        lines.append("--------------------------------------------------")
        lines.append("")

    lines.append("Relationships:")
    lines.append("==================================================")
    if relationships:
        for r in relationships:
            label = f"  - {r['from']} -> {r['to']}" if r["from"] and r["to"] else "  - Relationship"
            lines.append(label)
            if r["active"] is not None:
                lines.append(f"    Active: {r['active']}")
            if r["cross_filter"] is not None:
                lines.append(f"    CrossFilterDirection: {r['cross_filter']}")
            lines.append("")
    else:
        lines.append("  No relationships found")
        lines.append("")

    lines.append("functions.tmdl:")
    lines.append("==================================================")
    if functions_text:
        lines.append(code_block(functions_text, "tmdl"))
    else:
        lines.append("Not found (skipped)")
    lines.append("")

    lines.append("roles:")
    lines.append("==================================================")
    if roles:
        for role in roles:
            lines.append(f"File: {role['name']}.tmdl")
            lines.append("." * 50)
            lines.append(code_block(role["content"], "tmdl"))
            lines.append("." * 50)
            lines.append("")
    else:
        lines.append("Not found (skipped)")
        lines.append("")

    lines.append("## Report Metadata")
    lines.append("==================================================")

    lines.append("Report Filters:")
    if report_filters:
        for rf in report_filters:
            lines.append(f"- Source: {rf['name']}")
            for item in rf["items"]:
                lines.append(f"  - {item}")
    else:
        lines.append("- No report-level filters found")
    lines.append("")

    lines.append("Pages:")
    if pages:
        for p in pages:
            lines.append(f"- {p['page_name']}")
    else:
        lines.append("- No pages found")
    lines.append("")

    for p in pages:
        lines.append(f"Page: {p['page_name']}  [{report_name}]")
        if p.get("page_id"):
            lines.append(f"Page ID: {p['page_id']}")
        lines.append("--------------------------------------------------")

        lines.append("Page Filters:")
        if p["page_filters"]:
            for pf in p["page_filters"]:
                lines.append(f"- Source: {pf['name']}")
                for item in pf["items"]:
                    lines.append(f"  - {item}")
        else:
            lines.append("- No page-level filters found")
        lines.append("")

        if p["visuals"]:
            for v in p["visuals"]:
                lines.append(f"- {v['type']}")
                if v["fields"]:
                    lines.append("  Fields:")
                    for field in v["fields"]:
                        lines.append(f"    - {field}")
                if v["filters"]:
                    lines.append("  Visual Filters:")
                    for vf in v["filters"]:
                        lines.append(f"    - {vf}")
        else:
            lines.append("No visuals found")
        lines.append("")

    lines.append("Custom Visuals:")
    lines.append("--------------------------------------------------")
    if custom_visuals:
        for cv in custom_visuals:
            lines.append(f"- {cv}")
    else:
        lines.append("No custom visuals found")
    lines.append("")

    return "\n".join(lines)


def main():
    global repo_root
    parser = argparse.ArgumentParser(description="Generate PBIP metadata without querying model data.")
    parser.add_argument("--repo-root", type=Path, default=Path('.'))
    parser.add_argument("--source", action="append", help="Repository-relative source directory; overrides configuration")
    parser.add_argument("--config", type=Path, help="Configuration JSON with source_directories")
    parser.add_argument("--out", type=Path, default=Path('output'))
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    config_path = args.config or repo_root / '.pbip-metadata/config.json'
    config = safe_json(config_path) if config_path.exists() else {}
    sources = args.source or config.get('source_directories', ['.'])
    if not isinstance(sources, list) or not sources or not all(isinstance(s, str) and s for s in sources):
        raise ValueError('source_directories must be a non-empty list of relative paths.')
    reports = find_reports(sources)
    if not reports:
        raise SystemExit('No reports found; refusing to publish an empty documentation set.')
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit('Output must be empty to prevent stale documents. Choose a new output directory.')
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    index = ['# Power BI report documentation', '',
             'Generated from repository metadata. This is not live business data.', '',
             'Service links are workspace links and require workspace/report access.', '']
    for report in reports:
        content = build_markdown(report['name'], report['report_path'], report['model_path'])
        # Include named Power Query expressions without truncation.
        if report['model_path']:
            expressions = report['model_path'] / 'definition' / 'expressions.tmdl'
            if expressions.exists():
                content += '\n## Named expressions\n\n' + code_block(read_text(expressions), 'tmdl') + '\n'
        target = args.out / report['document']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + '\n', encoding='utf-8')
        manifest.append({k: report[k] for k in ('name', 'source', 'document', 'workspace')})
        index.append(f"- [{report['source']}]({quote(report['document'])})")
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.out / 'README.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    print(f'Generated {len(reports)} report documents.')


if __name__ == "__main__":
    main()
