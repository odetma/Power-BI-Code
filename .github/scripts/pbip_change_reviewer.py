import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TEXT_EXTENSIONS = {".json", ".tmdl", ".m", ".pqm"}

IGNORED_PATH_PATTERNS = [
    re.compile(r"(^|/)\.pbi/"),
]


# Keys that PBIP/PBIR auto-rotates on save or that are otherwise meaningless to a
# reviewer. Stripped before JSON diffing so the summary stays focused on real
# changes. Applied only to JSON files; TMDL and M parsers handle their own noise.
IGNORED_KEYS = {
    "lastModified",
    "modifiedTime",
    "createdTime",
    "version",
    "id",
    "queryHash",
    "lineageTag",
    "securityBindingsSignature",
    "scrollPosition",
    "$schema",
    "tabOrder",
}


# Populated by compare_projects: page "name" (hash-like ID used in
# activePageName) -> human-readable displayName, across base and head.
_PAGE_NAME_LOOKUP: Dict[str, str] = {}

# Populated by main() from CLI args; used to build markdown links to
# the file diff inside the PR. Empty when run locally.
_LINK_CONTEXT: Dict[str, str] = {"repo_url": "", "head_sha": "", "pr_number": ""}


def file_link(path: str) -> str:
    """Return a small markdown link icon to the file's diff in the PR
    (or its blob view if no PR context). Empty string if no repo URL."""
    import hashlib
    from urllib.parse import quote

    repo_url = _LINK_CONTEXT.get("repo_url") or ""
    if not repo_url:
        return ""

    pr_number = _LINK_CONTEXT.get("pr_number") or ""
    head_sha = _LINK_CONTEXT.get("head_sha") or ""

    if pr_number:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
        target = f"{repo_url}/pull/{pr_number}/files#diff-{digest}"
    elif head_sha:
        target = f"{repo_url}/blob/{head_sha}/{quote(path)}"
    else:
        return ""

    return f" [↗]({target})"


def build_page_name_lookup(root: Path) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for path in root.rglob("page.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        name = data.get("name")
        display = data.get("displayName") or name
        if name and display:
            lookup[str(name)] = str(display)
    return lookup


def resolve_page_name(value: Any) -> str:
    label = _PAGE_NAME_LOOKUP.get(str(value))
    return f'"{label}"' if label else str(value)


def read_files(root: Path) -> Dict[str, str]:
    files: Dict[str, str] = {}

    for path in root.rglob("*"):
        if not (path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS):
            continue

        relative_path = str(path.relative_to(root)).replace("\\", "/")
        if any(pattern.search(relative_path) for pattern in IGNORED_PATH_PATTERNS):
            continue

        try:
            files[relative_path] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(
                f"warning: skipping non-UTF-8 file {relative_path}: {exc}",
                file=sys.stderr,
            )

    return files


def try_parse_json(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize_json(val)
            for key, val in sorted(value.items())
            if key not in IGNORED_KEYS
        }

    if isinstance(value, list):
        return [normalize_json(item) for item in value]

    if isinstance(value, str):
        nested = try_parse_json(value)
        if nested is not None:
            return normalize_json(nested)
        return value

    return value


def join_path(base: str, key: str) -> str:
    return f"{base}.{key}" if base else key


def summarize_value(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) > 120:
        return text[:117] + "..."
    return text


# Map known PBIP JSON path prefixes to plain-English labels so reviewers don't
# have to know the schema. Longest prefix wins.
PBIP_PATH_LABELS: List[Tuple[str, str]] = [
    # Field role assignments (these are visual-type specific role buckets)
    ("visual.query.queryState.Values", "Values field"),
    ("visual.query.queryState.Y", "Y-axis field"),
    ("visual.query.queryState.X", "X-axis field"),
    ("visual.query.queryState.Category", "Category field"),
    ("visual.query.queryState.Rows", "Pivot rows"),
    ("visual.query.queryState.Columns", "Pivot columns"),
    ("visual.query.queryState.Tooltips", "Tooltip fields"),
    ("visual.query.queryState.Legend", "Legend field"),
    ("visual.query.queryState.Group", "Group field"),
    ("visual.query.queryState.Series", "Series field"),
    ("visual.query.queryState.Size", "Size field"),
    ("visual.query.queryState.Details", "Details field"),
    ("visual.query.queryState.Axis", "Axis field"),
    ("visual.query.queryState", "Field role assignments"),
    ("visual.query.sortDefinition", "Sort order"),
    ("visual.query", "Visual data query"),
    # Formatting blocks (visual.objects.* are formatting; visualContainerObjects.* are container effects)
    ("visual.objects.categoryLabels", "Category labels formatting"),
    ("visual.objects.dataLabels", "Data labels formatting"),
    ("visual.objects.title", "Title formatting"),
    ("visual.objects.background", "Background formatting"),
    ("visual.objects.subTotals", "Subtotals formatting"),
    ("visual.objects.rowHeaders", "Row headers formatting"),
    ("visual.objects.columnHeaders", "Column headers formatting"),
    ("visual.objects.legend", "Legend formatting"),
    ("visual.objects.labels", "Labels formatting"),
    ("visual.objects.values", "Values formatting"),
    ("visual.objects.general", "General settings"),
    ("visual.objects.plotArea", "Plot area formatting"),
    ("visual.objects.dataPoint", "Data point formatting"),
    ("visual.objects.lineStyles", "Line styles formatting"),
    ("visual.objects", "All visual formatting"),
    ("visual.visualContainerObjects.dropShadow", "Drop shadow effect"),
    ("visual.visualContainerObjects.background", "Container background"),
    ("visual.visualContainerObjects.border", "Container border"),
    ("visual.visualContainerObjects.title", "Container title"),
    ("visual.visualContainerObjects", "Container effects"),
    # Position / layout
    ("visual.position.x", "Visual X position"),
    ("visual.position.y", "Visual Y position"),
    ("visual.position.width", "Visual width"),
    ("visual.position.height", "Visual height"),
    ("visual.position.z", "Visual Z order"),
    ("visual.position", "Visual position"),
    # Other top-level visual properties
    ("visual.expansionStates", "Hierarchy expansion state"),
    ("visual.visualType", "Visual type"),
    ("visual.drillFilterOtherVisuals", "Drill: filter other visuals"),
    ("visual.howCreated", "Visual creation source"),
    # Top-level (page/report-level)
    ("filterConfig", "Visual-level filters"),
    ("howCreated", "Creation source"),
]


def humanize_path(path: str) -> Optional[str]:
    """Map a PBIP JSON path to a friendly label. Returns None if unknown."""
    matches = [
        (prefix, label)
        for prefix, label in PBIP_PATH_LABELS
        if path == prefix
        or path.startswith(prefix + ".")
        or path.startswith(prefix + "[")
    ]
    if not matches:
        return None
    prefix, label = max(matches, key=lambda pair: len(pair[0]))
    rest = path[len(prefix):]
    return f"{label}{rest}" if rest else label


def _projection_field_names(projections: Any) -> List[str]:
    if not isinstance(projections, list):
        return []
    names: List[str] = []
    for proj in projections:
        if not isinstance(proj, dict):
            continue
        ref = proj.get("nativeQueryRef") or proj.get("queryRef")
        if ref:
            names.append(str(ref))
            continue
        label = _field_reference_label(proj.get("field"))
        if label:
            names.append(label)
    return names


def _field_reference_label(value: Any) -> Optional[str]:
    """Return a compact field label from nested PBIP query expressions."""
    if not isinstance(value, dict):
        return None

    for key in ("Measure", "Column", "HierarchyLevel"):
        inner = value.get(key)
        if isinstance(inner, dict):
            prop = inner.get("Property")
            entity = _find_nested_value(inner, "Entity")
            if prop and entity:
                return f"{entity}.{prop}"
            if prop:
                return str(prop)

    aggregation = value.get("Aggregation")
    if isinstance(aggregation, dict):
        label = _field_reference_label(aggregation.get("Expression"))
        if label:
            return label

    for child in value.values():
        label = _field_reference_label(child)
        if label:
            return label

    return None


def _find_nested_value(value: Any, key: str) -> Optional[str]:
    if isinstance(value, dict):
        found = value.get(key)
        if found is not None:
            return str(found)
        for child in value.values():
            nested = _find_nested_value(child, key)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for child in value:
            nested = _find_nested_value(child, key)
            if nested is not None:
                return nested
    return None


ROLE_LABELS: Dict[str, str] = {
    "Values": "Values",
    "Y": "Y-axis",
    "X": "X-axis",
    "Category": "Category",
    "Rows": "Rows",
    "Columns": "Columns",
    "Tooltips": "Tooltips",
    "Legend": "Legend",
    "Group": "Group",
    "Series": "Series",
    "Size": "Size",
    "Details": "Details",
    "Axis": "Axis",
}


def _field_role_from_path(path: str) -> Optional[str]:
    match = re.match(r"^visual\.query\.queryState\.([A-Za-z]\w*)\.projections\[\d+\]$", path)
    if not match:
        return None
    role = match.group(1)
    return ROLE_LABELS.get(role, role)


def describe_added_list_item(path: str, value: Any) -> Optional[str]:
    if re.match(r"^pageOrder\[\d+\]$", path):
        return None

    role = _field_role_from_path(path)
    if role:
        names = _projection_field_names([value])
        if names:
            return f"Added field to {role}: {', '.join(names)}"
        return f"Added field to {role}"

    return f"Added list item: {path} = {summarize_value(value)}"


def describe_removed_list_item(path: str, value: Any) -> Optional[str]:
    if re.match(r"^pageOrder\[\d+\]$", path):
        return None

    role = _field_role_from_path(path)
    if role:
        names = _projection_field_names([value])
        if names:
            return f"Removed field from {role}: {', '.join(names)}"
        return f"Removed field from {role}"

    return f"Removed list item: {path}"


def summarize_pbip_value(path: str, value: Any) -> Optional[str]:
    """Extract a human-readable summary for known PBIP path/value combinations."""
    # queryState role: visual.query.queryState.<Role> -> field names
    if re.match(r"^visual\.query\.queryState\.[A-Za-z]\w*$", path):
        if isinstance(value, dict):
            names = _projection_field_names(value.get("projections"))
            if names:
                return ", ".join(names)
        return None

    # sortDefinition -> "<field> (<direction>)"
    if path == "visual.query.sortDefinition":
        if isinstance(value, dict):
            sorts = value.get("sort")
            if isinstance(sorts, list) and sorts:
                pieces = []
                for entry in sorts:
                    if not isinstance(entry, dict):
                        continue
                    field = entry.get("field", {})
                    name = None
                    if isinstance(field, dict):
                        for kind in ("Measure", "Column"):
                            inner = field.get(kind)
                            if isinstance(inner, dict):
                                name = inner.get("Property")
                                break
                    direction = entry.get("direction", "")
                    if name:
                        pieces.append(f"{name} ({direction})" if direction else str(name))
                if pieces:
                    return ", ".join(pieces)
        return None

    # visual.objects -> list immediate formatting keys (e.g. "categoryLabels, dataLabels")
    if path == "visual.objects" or path == "visual.visualContainerObjects":
        if isinstance(value, dict):
            keys = list(value.keys())
            if keys:
                return ", ".join(keys)
        return None

    # filterConfig -> "<N> filters: <names>"
    if path == "filterConfig":
        if isinstance(value, dict):
            filters = value.get("filters")
            if isinstance(filters, list):
                field_names: List[str] = []
                for f in filters:
                    if not isinstance(f, dict):
                        continue
                    field = f.get("field", {})
                    if isinstance(field, dict):
                        for kind in ("Measure", "Column"):
                            inner = field.get(kind)
                            if isinstance(inner, dict):
                                prop = inner.get("Property")
                                if prop:
                                    field_names.append(str(prop))
                                    break
                count = len(filters)
                if field_names:
                    preview = ", ".join(field_names[:5])
                    suffix = f" (+{len(field_names) - 5} more)" if len(field_names) > 5 else ""
                    return f"{count} filter(s): {preview}{suffix}"
                return f"{count} filter(s)"
        return None

    return None


def _friendly_path_label(path: str) -> Optional[str]:
    for pattern, friendly in JSON_VALUE_PATTERNS:
        if pattern.search(path):
            return friendly
    return None


# Power BI expressions are discriminated unions: a node like `expr` carries
# exactly one variant key (Literal, ThemeDataColor, Aggregation, ...).
# When a user switches a color from a theme palette pick to a custom hex,
# the variant flips entirely — naive diffing reports "added Literal" plus
# "removed ThemeDataColor". We collapse that to one readable change.
EXPR_VARIANT_LABELS: Dict[str, str] = {
    "Literal": "literal",
    "ThemeDataColor": "theme color",
    "Aggregation": "aggregation",
    "Column": "column",
    "Measure": "measure",
    "FillRule": "fill rule",
    "Conditional": "conditional",
    "SourceRef": "source",
    "HierarchyLevel": "hierarchy level",
}


def _summarize_expr_variant(variant: Any) -> Optional[str]:
    """Render a one-line summary of a discriminated-union node like
    {"Literal": {"Value": "'#43D674'"}} or {"ThemeDataColor": {"ColorId": 9}}."""
    if not isinstance(variant, dict) or len(variant) != 1:
        return None

    (key, payload), = variant.items()

    if key == "Literal" and isinstance(payload, dict):
        value = payload.get("Value")
        if isinstance(value, str):
            cleaned = value.strip().strip("'\"")
            return cleaned or "literal"
        if value is not None:
            return f"literal {value}"
        return "literal"

    if key == "ThemeDataColor" and isinstance(payload, dict):
        color_id = payload.get("ColorId")
        percent = payload.get("Percent")
        bits: List[str] = []
        if color_id is not None:
            bits.append(f"slot {color_id}")
        if percent not in (None, 0, 0.0):
            bits.append(f"tint {percent}")
        if bits:
            return f"theme color ({', '.join(bits)})"
        return "theme color"

    return EXPR_VARIANT_LABELS.get(key, key)


def _detect_expr_variant_swap(
    path: str, old: Any, new: Any
) -> Optional[str]:
    """If old/new are both single-variant expression nodes with disjoint
    variant keys, return a consolidated change message; else None."""
    if not (isinstance(old, dict) and isinstance(new, dict)):
        return None
    if not (path.endswith(".expr")):
        return None

    old_keys = set(old.keys())
    new_keys = set(new.keys())
    if not (old_keys and new_keys and old_keys.isdisjoint(new_keys)):
        return None

    old_variant = _summarize_expr_variant(old)
    new_variant = _summarize_expr_variant(new)
    if not (old_variant and new_variant):
        return None

    parent_path = path.rsplit(".", 1)[0]
    label = (
        _friendly_path_label(parent_path)
        or humanize_path(parent_path)
        or "Expression"
    )
    return f"{label} changed: {old_variant} -> {new_variant}"


def describe_added(path: str, value: Any) -> str:
    friendly = _friendly_path_label(path)
    if friendly:
        return f"Added {friendly}: {summarize_value(value)}"

    label = humanize_path(path)
    summary = summarize_pbip_value(path, value)

    if label and summary:
        return f"Added {label}: {summary}"
    if label:
        return f"Added {label}"
    return f"Added property: {path} = {summarize_value(value)}"


def describe_removed(path: str, old_value: Any) -> str:
    friendly = _friendly_path_label(path)
    if friendly:
        return f"Removed {friendly}"

    label = humanize_path(path)
    summary = summarize_pbip_value(path, old_value)

    if label and summary:
        return f"Removed {label} (was: {summary})"
    if label:
        return f"Removed {label}"
    return f"Removed property: {path}"


def json_diff_summary(old: Any, new: Any, path: str = "") -> List[str]:
    changes: List[str] = []

    # Numbers first: PBIP serializes the same value as int or float
    # interchangeably (e.g. Percent 0 vs 0.0). Treat int/float as one kind —
    # report only when the numeric value actually changed, and drop pure
    # int<->float "type" noise entirely.
    old_num = isinstance(old, (int, float)) and not isinstance(old, bool)
    new_num = isinstance(new, (int, float)) and not isinstance(new, bool)
    if old_num and new_num:
        if old != new:
            changes.append(classify_json_value_change(path, old, new))
        return changes

    if type(old) is not type(new):
        # Real type change (not numeric) — label it in friendly terms instead
        # of dumping the raw JSON path.
        label = _friendly_path_label(path) or humanize_path(path)
        if label:
            changes.append(f"{label} changed")
        else:
            changes.append(
                f"Changed type at {path}: {type(old).__name__} -> {type(new).__name__}"
            )
        return changes

    if isinstance(old, dict):
        swap = _detect_expr_variant_swap(path, old, new)
        if swap is not None:
            changes.append(swap)
            return changes

        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for key in sorted(new_keys - old_keys):
            child_path = join_path(path, key)
            changes.append(describe_added(child_path, new[key]))

        for key in sorted(old_keys - new_keys):
            child_path = join_path(path, key)
            changes.append(describe_removed(child_path, old[key]))

        for key in sorted(old_keys & new_keys):
            changes.extend(json_diff_summary(old[key], new[key], join_path(path, key)))

        return changes

    if isinstance(old, list):
        common = min(len(old), len(new))

        for index in range(common):
            changes.extend(
                json_diff_summary(old[index], new[index], f"{path}[{index}]")
            )

        for index in range(common, len(new)):
            description = describe_added_list_item(f"{path}[{index}]", new[index])
            if description:
                changes.append(description)

        for index in range(common, len(old)):
            description = describe_removed_list_item(f"{path}[{index}]", old[index])
            if description:
                changes.append(description)

        return changes

    if old != new:
        changes.append(classify_json_value_change(path, old, new))

    return changes


def path_segments(path: str) -> List[str]:
    return [seg.lower() for seg in re.split(r"[.\[\]]+", path) if seg]


# Conversational labels for common PBIP JSON paths. Each entry is
# (regex matched against the full path, friendly label). First match wins.
JSON_VALUE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Position and layout
    (re.compile(r"^visual\.position\.x$"), "X position"),
    (re.compile(r"^visual\.position\.y$"), "Y position"),
    (re.compile(r"^visual\.position\.width$"), "Width"),
    (re.compile(r"^visual\.position\.height$"), "Height"),
    (re.compile(r"^visual\.position\.z$"), "Z-order"),
    (re.compile(r"^visual\.position\.tabOrder$"), "Tab order"),
    (re.compile(r"^visual\.visualType$"), "Visual type"),
    (re.compile(r"^visual\.howCreated$"), "Visual creation source"),
    # Page-level
    (re.compile(r"^pageBindings\."), "Page binding"),
    (re.compile(r"^width$"), "Page width"),
    (re.compile(r"^height$"), "Page height"),
    (re.compile(r"^displayOption$"), "Page display option"),
    # Title text
    (re.compile(r"\.title.*\.text\.expr\.Literal\.Value$"), "Title text"),
    # Color slot in a theme
    (re.compile(r"\.background.*\.ThemeDataColor\.ColorId$"), "Background theme color slot"),
    (re.compile(r"\.background.*\.ThemeDataColor\.Percent$"), "Background color tint"),
    (re.compile(r"\.background.*\.solid\.color$"), "Background color"),
    (re.compile(r"\.fontColor.*\.ThemeDataColor\.ColorId$"), "Font theme color slot"),
    (re.compile(r"\.fontColor.*\.solid\.color$"), "Font color"),
    (re.compile(r"\.color.*\.ThemeDataColor\.ColorId$"), "Theme color slot"),
    (re.compile(r"\.color.*\.ThemeDataColor\.Percent$"), "Color tint"),
    (re.compile(r"\.color.*\.solid\.color$"), "Color"),
    # Field/measure references
    (re.compile(r"\.queryRef$"), "Field reference"),
    (re.compile(r"\.nativeQueryRef$"), "Native field reference"),
    (re.compile(r"\.Property$"), "Property reference"),
    # Expressions
    (re.compile(r"\.expression$"), "Expression"),
    # Filter renames (filter.name is the filter identifier)
    (re.compile(r"^filterConfig\.filters\[\d+\]\.name$"), "Filter target"),
    (re.compile(r"\.visualContainerObjects\.title.*\.text\.expr\.Literal\.Value$"), "Container title text"),
]


def classify_json_value_change(path: str, old: Any, new: Any) -> str:
    if path in {"visual.position.x", "visual.position.y", "position.x", "position.y"}:
        return "Visual moved"

    if path in {
        "visual.position.width",
        "visual.position.height",
        "position.width",
        "position.height",
    }:
        return "Visual resized"

    if re.search(r"\.background.*\.ThemeDataColor\.(ColorId|Percent)$", path):
        return "Background color changed"

    if path.endswith("activePageName"):
        return (
            f"Default opening page changed: {resolve_page_name(old)} -> "
            f"{resolve_page_name(new)}"
        )

    if path == "displayName":
        current_file = _LINK_CONTEXT.get("current_file", "")
        file_name = Path(current_file.replace("\\", "/")).name.lower()
        if file_name == "page.json":
            return f'Page renamed: "{old}" -> "{new}"'
        if file_name == "visual.json":
            return f'Visual title changed: "{old}" -> "{new}"'

    if path == "name" or path.endswith(".name"):
        # Bare 'name' field is usually a hash ID — skip the noisy translation.
        pass

    for pattern, friendly in JSON_VALUE_PATTERNS:
        if pattern.search(path):
            return f"{friendly} changed: {old} -> {new}"

    label = humanize_path(path)
    if label:
        return f"{label} changed: {old} -> {new}"

    return f"Value changed at {path}: {old} -> {new}"


def load_pbip_metadata(root: Path) -> Dict[str, Dict[str, str]]:
    metadata: Dict[str, Dict[str, str]] = {"pages": {}, "visuals": {}}

    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        file_name = path.name.lower()

        if file_name == "page.json":
            page_name = (
                data.get("displayName")
                or data.get("name")
                or data.get("id")
                or path.parent.name
            )
            page_folder = str(path.parent.relative_to(root)).replace("\\", "/")
            metadata["pages"][page_folder] = str(page_name)

        if file_name == "visual.json":
            visual_name = extract_visual_display_name(data) or path.parent.name
            visual_folder = str(path.parent.relative_to(root)).replace("\\", "/")
            metadata["visuals"][visual_folder] = str(visual_name)

    return metadata


def extract_visual_display_name(data: Dict[str, Any]) -> Optional[str]:
    candidates: List[Optional[str]] = [data.get("displayName")]

    visual = data.get("visual")
    if isinstance(visual, dict):
        candidates.append(extract_title_from_objects(visual.get("objects")))
        candidates.append(extract_title_from_objects(visual.get("visualContainerObjects")))
        visual_type = visual.get("visualType")
        if visual_type:
            candidates.append(f"{visual_type} visual")

    config = data.get("config")
    if isinstance(config, str):
        config = try_parse_json(config)

    if isinstance(config, dict):
        candidates.append(config.get("displayName"))
        single_visual = config.get("singleVisual")
        if isinstance(single_visual, dict):
            candidates.append(extract_title_from_objects(single_visual.get("objects")))
            visual_type = single_visual.get("visualType")
            if visual_type:
                candidates.append(f"{visual_type} visual")

    for candidate in candidates:
        if candidate:
            return str(candidate).strip("'\"")

    return None


def extract_title_from_objects(objects: Any) -> Optional[str]:
    if not isinstance(objects, dict):
        return None

    title = objects.get("title")
    if not isinstance(title, list) or not title:
        return None

    first = title[0]
    if not isinstance(first, dict):
        return None

    properties = first.get("properties")
    if not isinstance(properties, dict):
        return None

    text = properties.get("text")
    if not isinstance(text, dict):
        return None

    expr = text.get("expr")
    if not isinstance(expr, dict):
        return None

    literal = expr.get("Literal")
    if not isinstance(literal, dict):
        return None

    value = literal.get("Value")
    if value:
        return str(value).strip("'\"")

    return None


def describe_pbip_path(path: str, metadata: Dict[str, Dict[str, str]]) -> str:
    """Short context label like 'page "foo"' or 'visual "bar" on page "foo"';
    falls back to the bare filename when no metadata matches."""
    normalized_path = path.replace("\\", "/")

    page_label = None
    visual_label = None

    for page_path, page_name in metadata["pages"].items():
        if normalized_path.startswith(page_path + "/"):
            page_label = page_name
            break

    for visual_path, visual_name in metadata["visuals"].items():
        if normalized_path.startswith(visual_path + "/"):
            visual_label = visual_name
            break

    if visual_label and page_label:
        return f'visual "{visual_label}" on page "{page_label}"'
    if page_label:
        return f'page "{page_label}"'
    if visual_label:
        return f'visual "{visual_label}"'

    return f"`{Path(normalized_path).name}`"


def extract_textbox_text(data: Any) -> Optional[str]:
    """Walk a visual.json looking for textbox paragraph runs."""
    if not isinstance(data, dict):
        return None

    visual_type = ""
    visual = data.get("visual")
    if isinstance(visual, dict):
        visual_type = str(visual.get("visualType", "")).lower()

    if "textbox" not in visual_type:
        return None

    runs: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "textRuns" in node and isinstance(node["textRuns"], list):
                for run in node["textRuns"]:
                    if isinstance(run, dict):
                        value = run.get("value")
                        if isinstance(value, str):
                            runs.append(value)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    text = "".join(runs).strip()
    return text if text else None


def describe_new_file_entity(
    path: str, content: str, metadata: Dict[str, Dict[str, str]]
) -> str:
    """Friendlier prose for a brand-new PBIP file in the 'New' section."""
    normalized_path = path.replace("\\", "/")
    file_name = Path(normalized_path).name.lower()

    parsed = try_parse_json(content) if file_name.endswith(".json") else None

    if file_name == "visual.json" and isinstance(parsed, dict):
        visual_name = extract_visual_display_name(parsed) or "(unnamed)"
        page_label = None
        for page_path, page_name in metadata["pages"].items():
            if normalized_path.startswith(page_path + "/"):
                page_label = page_name
                break

        textbox_text = extract_textbox_text(parsed)
        snippet = ""
        if textbox_text:
            preview = textbox_text if len(textbox_text) <= 80 else textbox_text[:77] + "..."
            snippet = f' — text: "{preview}"'

        if page_label:
            return f'New visual "{visual_name}" on page "{page_label}"{snippet}'
        return f'New visual "{visual_name}"{snippet}'

    if file_name == "page.json" and isinstance(parsed, dict):
        page_name = parsed.get("displayName") or parsed.get("name") or "(unnamed)"
        return f'New page "{page_name}"'

    if file_name.endswith(".tmdl"):
        return f"New TMDL file: `{Path(normalized_path).name}`"

    if file_name.endswith((".m", ".pqm")):
        return f"New Power Query file: `{Path(normalized_path).name}`"

    return f"New file: `{Path(normalized_path).name}`"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def normalize_tmdl_text(text: str) -> str:
    lines = [
        line for line in normalize_text(text).split("\n")
        if "annotation PBIDesktopVersion" not in line
    ]
    return "\n".join(lines).strip()


def describe_database_tmdl_change(old_text: str, new_text: str) -> Optional[str]:
    old_match = re.search(r"^\s*compatibilityLevel:\s*(\d+)\s*$", old_text, re.MULTILINE)
    new_match = re.search(r"^\s*compatibilityLevel:\s*(\d+)\s*$", new_text, re.MULTILINE)
    if old_match and new_match and old_match.group(1) != new_match.group(1):
        return (
            "Semantic model compatibility level changed: "
            f"{old_match.group(1)} -> {new_match.group(1)}"
        )
    return None


# === TMDL ===

TMDL_OBJECT_TYPES = (
    "table",
    "measure",
    "column",
    "calculationGroup",
    "calculationItem",
    "relationship",
    "partition",
    "hierarchy",
    "level",
    "model",
    "dataSource",
    "culture",
    "expression",
    "perspective",
    "role",
    "annotation",
)

TMDL_OBJECT_HEADER = re.compile(
    rf"^(?P<indent>[ \t]*)(?P<type>{'|'.join(TMDL_OBJECT_TYPES)})\b(?P<rest>.*)$"
)


def clean_tmdl_segment(segment: str) -> str:
    eq = segment.find(" =")
    return segment[:eq].rstrip() if eq != -1 else segment.strip()


def clean_tmdl_key(key: str) -> str:
    return " > ".join(clean_tmdl_segment(part) for part in key.split(" > "))


def extract_tmdl_expression(body: str) -> Optional[str]:
    """Pull the expression that follows '=' on a TMDL header line.
    Handles single-line ('measure foo = SUM(x)') and triple-backtick
    multi-line forms. Returns None if there's no expression."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        eq_idx = line.find("=")
        if eq_idx == -1:
            continue
        rest = line[eq_idx + 1:].strip()
        if rest.startswith("```"):
            collected: List[str] = []
            for follow in lines[i + 1:]:
                if follow.strip() == "```":
                    break
                collected.append(follow)
            indent = min(
                (len(l) - len(l.lstrip()) for l in collected if l.strip()),
                default=0,
            )
            return "\n".join(l[indent:] for l in collected).strip() or None
        return rest or None
    return None


def fenced_block(language: str, content: str, indent: str = "  ") -> str:
    """Multi-line code block where every line carries `indent`, so it
    nests cleanly under a markdown bullet without breaking out."""
    out = [f"{indent}```{language}"]
    for line in content.split("\n"):
        out.append(f"{indent}{line}" if line else indent.rstrip())
    out.append(f"{indent}```")
    return "\n".join(out)


def extract_tmdl_objects(text: str) -> Dict[str, Tuple[str, str]]:
    """Walk TMDL line-by-line tracking indentation. Returns
    {full_key: (leaf_type, body)} where full_key chains parent context
    (e.g. 'table foo > measure bar')."""
    objects: Dict[str, Tuple[str, str]] = {}
    lines = text.splitlines()

    stack: List[Tuple[int, str]] = []
    current_key: Optional[str] = None
    current_type: Optional[str] = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_key, current_type, current_lines
        if current_key is not None and current_type is not None:
            objects[current_key] = (
                current_type,
                "\n".join(current_lines).rstrip(),
            )
        current_key = None
        current_type = None
        current_lines = []

    for raw_line in lines:
        if not raw_line.strip():
            if current_key is not None:
                current_lines.append(raw_line)
            continue

        match = TMDL_OBJECT_HEADER.match(raw_line)
        if match:
            indent = len(match.group("indent").expandtabs(4))
            obj_type = match.group("type")
            header = raw_line.strip()

            while stack and stack[-1][0] >= indent:
                stack.pop()

            parent_prefix = stack[-1][1] if stack else ""
            this_key = f"{parent_prefix}{header}"

            flush()

            current_key = this_key
            current_type = obj_type
            current_lines = [raw_line]

            stack.append((indent, this_key + " > "))
            continue

        if current_key is not None:
            current_lines.append(raw_line)

    flush()
    return objects


def filter_top_level_keys(keys: set) -> set:
    """Drop keys whose parent is also in the set; avoids reporting child
    annotations/columns separately when their containing measure/table is
    being added or removed wholesale."""
    keys = {key for key in keys if "annotation PBIDesktopVersion" not in key}
    sorted_keys = sorted(keys, key=len)
    kept: List[str] = []
    for key in sorted_keys:
        if any(key.startswith(parent + " > ") for parent in kept):
            continue
        kept.append(key)
    return set(kept)


def tmdl_object_description(verb: str, leaf_type: str, key: str, expression: Optional[str]) -> str:
    cleaned = clean_tmdl_key(key)
    head = f"{verb} TMDL {leaf_type}: `{cleaned}`"
    if expression is None:
        return head
    language = "dax" if leaf_type.lower() == "measure" else "m" if leaf_type.lower() == "partition" else ""
    if not language:
        return head
    return f"{head}\n{fenced_block(language, expression)}"


# When more than this many same-type siblings (e.g. columns on one table) are
# added/removed/changed together, collapse them into one summarized line instead
# of a bullet per object — a table gaining 100 columns must not flood the summary.
_TMDL_ROLLUP_THRESHOLD = 6


def _tmdl_leaf_parts(key: str):
    """(parent_key, leaf_name) for a TMDL key like 'table X > column Y'."""
    if " > " in key:
        parent, last = key.rsplit(" > ", 1)
    else:
        parent, last = "", key
    parts = last.split(" ", 1)
    name = clean_tmdl_segment(parts[1]) if len(parts) > 1 else clean_tmdl_segment(last)
    return parent, name


def _rollup_tmdl_group(verb: str, leaf_type: str, parent: str, names: List[str]) -> str:
    plural = leaf_type if leaf_type.endswith("s") else f"{leaf_type}s"
    where = f" in {clean_tmdl_key(parent)}" if parent else ""
    preview = ", ".join(names[:8])
    more = f" (+{len(names) - 8} more)" if len(names) > 8 else ""
    return f"{verb} {len(names)} {plural}{where}: {preview}{more}"


def _group_tmdl_keys(keys):
    """Group keys by (parent, leaf_type), preserving sorted order."""
    groups: Dict[tuple, List[str]] = {}
    order: List[tuple] = []
    for key in sorted(keys):
        parent, _ = _tmdl_leaf_parts(key)
        # leaf_type is the first word of the last segment (column/measure/...)
        last = key.rsplit(" > ", 1)[-1]
        leaf_type = last.split(" ", 1)[0]
        gkey = (parent, leaf_type)
        if gkey not in groups:
            groups[gkey] = []
            order.append(gkey)
        groups[gkey].append(key)
    return order, groups


def _describe_added_removed(verb: str, keys, objects) -> List[str]:
    order, groups = _group_tmdl_keys(keys)
    lines: List[str] = []
    for gkey in order:
        members = groups[gkey]
        parent, leaf_type = gkey
        if len(members) > _TMDL_ROLLUP_THRESHOLD:
            names = [_tmdl_leaf_parts(k)[1] for k in members]
            lines.append(_rollup_tmdl_group(verb, leaf_type, parent, names))
        else:
            for key in members:
                lt, body = objects[key]
                lines.append(tmdl_object_description(verb, lt, key, extract_tmdl_expression(body)))
    return lines


def compare_tmdl(old_text: str, new_text: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {"added": [], "removed": [], "modified": []}

    if normalize_tmdl_text(old_text) == normalize_tmdl_text(new_text):
        return result

    old_objects = extract_tmdl_objects(old_text)
    new_objects = extract_tmdl_objects(new_text)

    old_keys = set(old_objects.keys())
    new_keys = set(new_objects.keys())

    added_keys = filter_top_level_keys(new_keys - old_keys)
    removed_keys = filter_top_level_keys(old_keys - new_keys)

    result["added"] = _describe_added_removed("New", added_keys, new_objects)
    result["removed"] = _describe_added_removed("Removed", removed_keys, old_objects)

    # --- modified: build detailed line per object, then roll up bulk groups ---
    changed_keys = [
        key for key in (old_keys & new_keys)
        if normalize_tmdl_text(old_objects[key][1]) != normalize_tmdl_text(new_objects[key][1])
    ]
    detailed: Dict[str, str] = {}
    for key in changed_keys:
        new_leaf, new_body = new_objects[key]
        _, old_body = old_objects[key]
        cleaned = clean_tmdl_key(key)
        old_expr = extract_tmdl_expression(old_body)
        new_expr = extract_tmdl_expression(new_body)
        if new_leaf.lower() in ("measure", "partition") and old_expr is not None and new_expr is not None and old_expr != new_expr:
            language = "dax" if new_leaf.lower() == "measure" else "m"
            label = "DAX measure" if new_leaf.lower() == "measure" else "Power Query partition"
            detailed[key] = (
                f"{label} changed: `{cleaned}`\n"
                f"  Before:\n{fenced_block(language, old_expr, '    ')}\n"
                f"  After:\n{fenced_block(language, new_expr, '    ')}"
            )
        else:
            detailed[key] = classify_tmdl_object_change(key, new_leaf, old_body, new_body)

    order, groups = _group_tmdl_keys(changed_keys)
    for gkey in order:
        members = groups[gkey]
        parent, leaf_type = gkey
        if len(members) > _TMDL_ROLLUP_THRESHOLD:
            names = [_tmdl_leaf_parts(k)[1] for k in members]
            result["modified"].append(_rollup_tmdl_group("Changed", leaf_type, parent, names))
        else:
            for key in members:
                result["modified"].append(detailed[key])

    if not any(result.values()) and normalize_tmdl_text(old_text) != normalize_tmdl_text(new_text):
        result["modified"].append("TMDL file changed")

    return result


def classify_tmdl_object_change(
    key: str, leaf_type: str, old_body: str, new_body: str
) -> str:
    leaf = leaf_type.lower()

    if leaf == "measure":
        return f"DAX measure changed: {key}"

    if leaf == "partition":
        return f"Power Query partition changed: {key}"

    if leaf == "relationship":
        return f"Relationship changed: {key}"

    if leaf == "column":
        return f"Column definition changed: {key}"

    if leaf == "table":
        return f"Table definition changed: {key}"

    if leaf == "calculationgroup":
        return f"Calculation group changed: {key}"

    return f"TMDL {leaf_type} changed: {key}"


# === M / Power Query ===


def strip_m_strings_and_comments(text: str) -> str:
    """Replace string literals and comments with spaces of equal length so
    later depth/identifier scans see correct offsets but no syntactic noise."""
    out: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        if text[i : i + 2] == "/*":
            end = text.find("*/", i + 2)
            end = (end + 2) if end != -1 else n
            out.append(" " * (end - i))
            i = end
            continue

        if text[i : i + 2] == "//":
            end = text.find("\n", i)
            end = end if end != -1 else n
            out.append(" " * (end - i))
            i = end
            continue

        if text[i : i + 2] == '#"':
            j = i + 2
            while j < n and text[j] != '"':
                j += 1
            j = min(j + 1, n)
            out.append(text[i:j])
            i = j
            continue

        if text[i] == '"':
            j = i + 1
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            j = min(j + 1, n)
            out.append(" " * (j - i))
            i = j
            continue

        out.append(text[i])
        i += 1

    return "".join(out)


def split_m_top_level_commas(text: str) -> List[str]:
    """Split a let-body fragment on commas that are outside parens/brackets/braces
    AND outside nested `let ... in` blocks."""
    parts: List[str] = []
    depth = 0
    nested_lets = 0
    start = 0
    i = 0

    while i < len(text):
        ch = text[i]

        if ch in "([{":
            depth += 1
            i += 1
            continue

        if ch in ")]}":
            depth -= 1
            i += 1
            continue

        if depth == 0:
            if _word_at(text, i, "let"):
                nested_lets += 1
                i += 3
                continue
            if _word_at(text, i, "in"):
                if nested_lets > 0:
                    nested_lets -= 1
                    i += 2
                    continue

        if depth == 0 and nested_lets == 0 and ch == ",":
            parts.append(text[start:i])
            i += 1
            start = i
            continue

        i += 1

    parts.append(text[start:])
    return parts


def _word_at(text: str, i: int, word: str) -> bool:
    end = i + len(word)
    if end > len(text) or text[i:end] != word:
        return False
    if i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_"):
        return False
    if end < len(text) and (text[end].isalnum() or text[end] == "_"):
        return False
    return True


def extract_m_steps(text: str) -> Dict[str, str]:
    """Extract steps from a `let ... in` M block as {step_name: step_body}.
    Handles nested let blocks, parens, comments, and strings."""
    sanitized = strip_m_strings_and_comments(text)

    let_pos = -1
    i = 0
    while i < len(sanitized):
        if _word_at(sanitized, i, "let"):
            let_pos = i + 3
            break
        i += 1

    if let_pos == -1:
        return {}

    depth = 0
    nested_lets = 0
    in_pos = -1
    i = let_pos

    while i < len(sanitized):
        ch = sanitized[i]

        if ch in "([{":
            depth += 1
            i += 1
            continue

        if ch in ")]}":
            depth -= 1
            i += 1
            continue

        if depth == 0:
            if _word_at(sanitized, i, "let"):
                nested_lets += 1
                i += 3
                continue
            if _word_at(sanitized, i, "in"):
                if nested_lets > 0:
                    nested_lets -= 1
                    i += 2
                    continue
                in_pos = i
                break

        i += 1

    if in_pos == -1:
        return {}

    body_sanitized = sanitized[let_pos:in_pos]
    body_original = text[let_pos:in_pos]

    san_segments = split_m_top_level_commas(body_sanitized)

    orig_segments: List[str] = []
    cursor = 0
    for seg in san_segments:
        seg_end = cursor + len(seg)
        orig_segments.append(body_original[cursor:seg_end])
        cursor = seg_end + 1

    name_re = re.compile(
        r'^\s*(#"[^"]+"|[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', re.DOTALL
    )
    steps: Dict[str, str] = {}
    for raw in orig_segments:
        if not raw.strip():
            continue
        match = name_re.match(raw)
        if not match:
            continue
        name = match.group(1).strip()
        body = normalize_text(match.group(2))
        steps[name] = body

    return steps


def compare_m_code(old_text: str, new_text: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {"added": [], "removed": [], "modified": []}

    old_steps = extract_m_steps(old_text)
    new_steps = extract_m_steps(new_text)

    old_keys = set(old_steps.keys())
    new_keys = set(new_steps.keys())

    for key in sorted(new_keys - old_keys):
        result["added"].append(
            f"New Power Query step: `{key}`\n{fenced_block('m', new_steps[key])}"
        )

    for key in sorted(old_keys - new_keys):
        result["removed"].append(
            f"Removed Power Query step: `{key}`\n{fenced_block('m', old_steps[key])}"
        )

    for key in sorted(old_keys & new_keys):
        if old_steps[key] != new_steps[key]:
            classification = classify_m_step_change(key, old_steps[key], new_steps[key])
            result["modified"].append(
                f"{classification}\n"
                f"  Before:\n{fenced_block('m', old_steps[key], '    ')}\n"
                f"  After:\n{fenced_block('m', new_steps[key], '    ')}"
            )

    if not any(result.values()) and normalize_text(old_text) != normalize_text(new_text):
        result["modified"].append("Power Query code changed")

    return result


def classify_m_step_change(step_name: str, old_body: str, new_body: str) -> str:
    combined = f"{step_name} {old_body} {new_body}".lower()

    if "table.selectrows" in combined:
        return f"Filter logic changed in Power Query step: {step_name}"

    if "table.renamecolumns" in combined:
        return f"Column rename logic changed in Power Query step: {step_name}"

    if "table.removecolumns" in combined:
        return f"Removed columns logic changed in Power Query step: {step_name}"

    if "table.selectcolumns" in combined:
        return f"Selected columns logic changed in Power Query step: {step_name}"

    if "table.transformcolumntypes" in combined:
        return f"Column type logic changed in Power Query step: {step_name}"

    if "table.addcolumn" in combined:
        return f"Added column logic changed in Power Query step: {step_name}"

    if "table.nestedjoin" in combined or "table.join" in combined:
        return f"Join logic changed in Power Query step: {step_name}"

    if "table.groupby" in combined:
        return f"Group by logic changed in Power Query step: {step_name}"

    if "snowflake" in combined or "sql.database" in combined or "odata.feed" in combined:
        return f"Source connection changed in Power Query step: {step_name}"

    return f"Power Query step changed: {step_name}"


def classify_text_change(file_path: str, old_text: str, new_text: str) -> Dict[str, List[str]]:
    _LINK_CONTEXT["current_file"] = file_path
    try:
        lower_path = file_path.lower()

        if lower_path.endswith(".json"):
            old_json = try_parse_json(old_text)
            new_json = try_parse_json(new_text)

            if old_json is not None and new_json is not None:
                return {
                    "added": [],
                    "removed": [],
                    "modified": json_diff_summary(
                        normalize_json(old_json), normalize_json(new_json)
                    ),
                }

        if lower_path.endswith(".tmdl"):
            if lower_path.endswith("/database.tmdl") or lower_path.endswith("\\database.tmdl"):
                description = describe_database_tmdl_change(old_text, new_text)
                if description:
                    return {"added": [], "removed": [], "modified": [description]}
            return compare_tmdl(old_text, new_text)

        if lower_path.endswith((".m", ".pqm")):
            return compare_m_code(old_text, new_text)

        return {"added": [], "removed": [], "modified": ["Text file changed"]}
    finally:
        _LINK_CONTEXT["current_file"] = ""


# === New / Deleted roll-up ===================================================
# A brand-new report drops hundreds of files into the diff. Listing each one
# (every visual, bookmark, theme, TMDL table) buries the signal. Instead we roll
# up to the notable level: a whole new report -> one line (+ its page names), a
# new page -> one line (no per-visual detail), supporting files -> a count.


def _project_root_of(path: str) -> Optional[str]:
    """Return the path up to and including the first `*.Report` / `*.SemanticModel`
    segment, or None if the path isn't inside a PBIP project."""
    acc: List[str] = []
    for seg in path.split("/"):
        acc.append(seg)
        if seg.endswith(".Report") or seg.endswith(".SemanticModel"):
            return "/".join(acc)
    return None


def _project_display_name(root: str) -> str:
    leaf = root.split("/")[-1]
    for ext in (".Report", ".SemanticModel"):
        if leaf.endswith(ext):
            return leaf[: -len(ext)]
    return leaf


def _page_folder_of(path: str) -> Optional[str]:
    """`.../pages/<id>` for a page.json or one of its visuals; None otherwise.
    The trailing slash requirement excludes `.../pages/pages.json`."""
    match = re.search(r"^(.*/pages/[^/]+)/", path)
    return match.group(1) if match else None


def _page_name_for(page_folder: str, files: Dict[str, str]) -> Optional[str]:
    content = files.get(page_folder + "/page.json")
    if not content:
        return None
    data = try_parse_json(content)
    if isinstance(data, dict):
        name = data.get("displayName") or data.get("name")
        return str(name).strip() if name else None
    return None


def _join_names(names: List[str], cap: int = 15) -> str:
    names = [n for n in names if n]
    if len(names) <= cap:
        return ", ".join(names)
    return ", ".join(names[:cap]) + f" (+{len(names) - cap} more)"


def _table_names(paths: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        m = re.search(r"/tables/([^/]+)\.tmdl$", p)
        if m:
            out.append(m.group(1))
    return sorted(out)


def _pick_link_path(paths: List[str]) -> str:
    for suffix in ("/report.json", "/model.tmdl", "/definition.pbism", "/definition.pbir"):
        for p in paths:
            if p.endswith(suffix):
                return p
    return sorted(paths)[0]


def _dedupe_preserve_order(entries: List[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for entry in entries:
        if entry in seen:
            continue
        seen.add(entry)
        unique.append(entry)
    return unique


def _rollup_auto_date_table_changes(entries: List[str]) -> List[str]:
    """Collapse Power BI auto date table churn into one reviewer-friendly line."""
    table_names = set()
    matched_indexes = set()
    pattern = re.compile(
        r"^- Column definition changed: table "
        r"((?:LocalDateTable|DateTableTemplate)_[^ >]+) > column "
    )

    for index, entry in enumerate(entries):
        match = pattern.search(entry)
        if not match:
            continue
        table_names.add(match.group(1))
        matched_indexes.add(index)

    if len(matched_indexes) < 10:
        return entries

    rolled_up: List[str] = []
    inserted = False
    for index, entry in enumerate(entries):
        if index not in matched_indexes:
            rolled_up.append(entry)
            continue
        if not inserted:
            rolled_up.append(
                "- Auto date table definitions refreshed "
                f"({len(table_names)} generated table(s))"
            )
            inserted = True

    return rolled_up


def rollup_new_or_deleted(
    paths: set, files: Dict[str, str], counterpart: set, *, new: bool
) -> List[str]:
    """Collapse a set of wholly added/removed files into notable bullets."""
    verb = "New" if new else "Deleted"
    page_verb = "New page" if new else "Removed page"
    word = "added" if new else "removed"
    lines: List[str] = []

    by_project: Dict[str, List[str]] = {}
    loose: List[str] = []
    for p in paths:
        root = _project_root_of(p)
        if root:
            by_project.setdefault(root, []).append(p)
        else:
            loose.append(p)

    for root in sorted(by_project):
        proj_paths = sorted(by_project[root])
        name = _project_display_name(root)
        is_model = root.endswith(".SemanticModel")
        wholly = not any(c == root or c.startswith(root + "/") for c in counterpart)

        # --- entire project added / removed -> one headline line ---
        if wholly:
            link = file_link(_pick_link_path(proj_paths))
            if is_model:
                tables = _table_names(proj_paths)
                lines.append(f"- {verb} semantic model: **{name}**{link}")
                if tables:
                    lines.append(f"  - {len(tables)} table(s): {_join_names(tables)}")
            else:
                pages = [
                    _page_name_for(p[: -len("/page.json")], files) or "(unnamed)"
                    for p in proj_paths
                    if p.endswith("/page.json")
                ]
                badge = "🆕 " if new else ""
                lines.append(f"- {badge}{verb} report: **{name}**{link}")
                if pages:
                    lines.append(f"  - {len(pages)} page(s): {_join_names(sorted(pages))}")
            continue

        # --- project exists on both sides: summarize at page / table level ---
        page_groups: Dict[str, List[str]] = {}
        others: List[str] = []
        for p in proj_paths:
            pf = _page_folder_of(p)
            if pf:
                page_groups.setdefault(pf, []).append(p)
            else:
                others.append(p)

        for pf in sorted(page_groups):
            page_wholly = not any(c.startswith(pf + "/") for c in counterpart)
            pname = _page_name_for(pf, files) or pf.split("/")[-1]
            if page_wholly:
                lines.append(f'- {page_verb}: "{pname}"{file_link(pf + "/page.json")}')
            else:
                visuals = [p for p in page_groups[pf] if p.endswith("visual.json")]
                if visuals:
                    lines.append(
                        f'- Page "{pname}": {len(visuals)} visual(s) {word}'
                        f'{file_link(pf + "/page.json")}'
                    )

        if is_model:
            for t in _table_names(others):
                lines.append(f"- {verb} table: `{t}`")
            rest = [p for p in others if not re.search(r"/tables/[^/]+\.tmdl$", p)]
            if rest:
                lines.append(f"- {len(rest)} model definition file(s) {word}")
        elif others:
            lines.append(
                f"- {len(others)} supporting file(s) {word} "
                f"(bookmarks, theme, resources){file_link(sorted(others)[0])}"
            )

    for p in sorted(loose):
        lines.append(f"- {verb} file: `{Path(p).name}`{file_link(p)}")

    return lines


def compare_projects(old_root: Path, new_root: Path) -> str:
    old_files = read_files(old_root)
    new_files = read_files(new_root)

    metadata = load_pbip_metadata(new_root)

    _PAGE_NAME_LOOKUP.clear()
    _PAGE_NAME_LOOKUP.update(build_page_name_lookup(old_root))
    _PAGE_NAME_LOOKUP.update(build_page_name_lookup(new_root))

    old_paths = set(old_files.keys())
    new_paths = set(new_files.keys())

    new_section: List[str] = []
    deleted_section: List[str] = []
    modified_section: List[str] = []

    new_section.extend(
        rollup_new_or_deleted(new_paths - old_paths, new_files, old_paths, new=True)
    )
    deleted_section.extend(
        rollup_new_or_deleted(old_paths - new_paths, old_files, new_paths, new=False)
    )

    for path in sorted(old_paths & new_paths):
        if old_files[path] == new_files[path]:
            continue

        result = classify_text_change(path, old_files[path], new_files[path])
        if not any(result.values()):
            continue

        context = describe_pbip_path(path, metadata)
        link = file_link(path)

        for category, section in (
            ("added", new_section),
            ("removed", deleted_section),
            ("modified", modified_section),
        ):
            entries = result[category]
            if not entries:
                continue
            entries = _dedupe_preserve_order(entries)
            for entry in entries[:80]:
                if "\n" in entry:
                    head, body = entry.split("\n", 1)
                    section.append(f"- {head} (in {context}){link}")
                    section.append(body)
                else:
                    section.append(f"- {entry} (in {context}){link}")
            if len(entries) > 80:
                section.append(f"- Additional changes hidden: {len(entries) - 80} (in {context}){link}")

    lines: List[str] = ["# PBIP Change Summary", ""]

    if new_section:
        lines.append("## New")
        lines.extend(new_section)
        lines.append("")

    if deleted_section:
        lines.append("## Deleted")
        lines.extend(deleted_section)
        lines.append("")

    if modified_section:
        modified_section = _rollup_auto_date_table_changes(modified_section)
        lines.append("## Modified")
        lines.extend(modified_section)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a readable PBIP change summary."
    )

    parser.add_argument("--old", required=True, help="Path to the old PBIP folder.")
    parser.add_argument("--new", required=True, help="Path to the new PBIP folder.")
    parser.add_argument(
        "--output",
        default="pbip_change_summary.md",
        help="Output markdown file.",
    )
    parser.add_argument("--repo-url", default="", help="GitHub repo URL for file links.")
    parser.add_argument("--head-sha", default="", help="PR head commit SHA for file links.")
    parser.add_argument("--pr-number", default="", help="PR number for diff anchors.")

    args = parser.parse_args()

    old_root = Path(args.old)
    new_root = Path(args.new)

    for label, root in (("--old", old_root), ("--new", new_root)):
        if not root.exists():
            print(f"error: {label} path does not exist: {root}", file=sys.stderr)
            return 2
        if not root.is_dir():
            print(f"error: {label} path is not a directory: {root}", file=sys.stderr)
            return 2

    _LINK_CONTEXT["repo_url"] = args.repo_url
    _LINK_CONTEXT["head_sha"] = args.head_sha
    _LINK_CONTEXT["pr_number"] = args.pr_number

    summary = compare_projects(old_root, new_root)

    output_path = Path(args.output)
    output_path.write_text(summary, encoding="utf-8")

    print(f"Summary created: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
