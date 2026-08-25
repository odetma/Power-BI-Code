---
name: pbi-style-presets
description: >
  Expert skill for creating Power BI custom theme JSON files with style presets, including dark
  mode themes. Use this skill whenever a user wants to: create or edit a Power BI theme JSON file,
  define style presets for specific visual types (bar charts, line charts, cards, slicers, tables,
  etc.), set data colors, structural colors, or text classes in a theme, make consistent visual
  formatting across a Power BI report, troubleshoot a theme JSON file, or build named preset
  dropdowns that appear in the Format Visual pane. Also trigger when the user asks for a dark
  mode, dark background, dark theme, or night mode Power BI report or dashboard. Trigger on any
  mention of "Power BI theme", "custom theme JSON", "style preset", "theme file", "visualStyles",
  "dataColors", "dark mode", "dark background", or requests to standardize the look of Power BI
  visuals. Always use this skill — do not attempt to write theme JSON from memory without
  consulting it.
---

# Power BI Custom Theme & Style Presets Expert

You are an expert in crafting Power BI custom theme JSON files, with a focus on the **style presets** feature. Follow this skill carefully for every task.

## Core Concepts

A Power BI theme JSON file has 4 main layers (all optional except `name`):

1. **Theme Colors** — `dataColors`, `good`, `neutral`, `bad`, `maximum`, `center`, `minimum`, `null`
2. **Structural Colors** — `background`, `firstLevelElements`, `secondLevelElements`, `thirdLevelElements`, `fourthLevelElements`, `secondaryBackground`, `tableAccent`
3. **Text Classes** — `textClasses` with primary classes: `callout`, `title`, `header`, `label`
4. **Visual Styles** — `visualStyles` with per-visual-type formatting and **style presets**

> Only include properties you want to override. Everything else inherits from the base theme.

---

## Style Presets — The Core Feature

Style presets let users switch between multiple named formatting options for a visual type via a **Style** dropdown in the Format Visual pane (Visualizations panel → Format Visual → Style).

### JSON Structure

```json
"visualStyles": {
    "<visualName>": {
        "*": {
            "stylePreset": [{ "name": "<DefaultPresetName>" }],
            "<cardName>": [{ "<propertyName>": <value> }]
        },
        "<PresetName1>": {
            "<cardName>": [{ "<propertyName>": <value> }]
        },
        "<PresetName2>": {
            "<cardName>": [{ "<propertyName>": <value> }]
        }
    }
}
```

**Key rules:**
- `"*"` is the **default style** — applied when no preset is selected; also sets which preset is active by default using `"stylePreset": [{ "name": "PresetName" }]`
- Named presets **inherit** from `"*"` — only override what's different
- Preset names appear exactly as written in the Style dropdown in Power BI Desktop
- Use `"*"` as `visualName` to apply a setting to **all** visual types
- Use `"*"` as `cardName` to apply across all formatting cards

### Available Visual Names (common)
| Visual Type | JSON Name |
|---|---|
| Clustered Bar Chart | `barChart` |
| Clustered Column Chart | `columnChart` |
| Stacked Bar Chart | `stackedBarChart` |
| Stacked Column Chart | `stackedColumnChart` |
| Line Chart | `lineChart` |
| Area Chart | `areaChart` |
| Combo Chart | `lineClusteredColumnComboChart` |
| Pie Chart | `pieChart` |
| Donut Chart | `donutChart` |
| Scatter Chart | `scatterChart` |
| Card | `card` |
| Multi-row Card | `multiRowCard` |
| Table | `tableEx` |
| Matrix | `matrix` |
| Slicer (dropdown/list) | `slicer` |
| Text Slicer | `textSlicer` |
| KPI | `kpi` |
| Gauge | `gauge` |
| Map | `map` |
| Funnel | `funnel` |
| Waterfall | `waterfallChart` |
| Treemap | `treemap` |
| All visuals (wildcard) | `*` |

> For exact visual names, use the PBIR method described in the **Finding Property Names** section below.

---

## Finding Property Names (Critical!)

The formatting pane display name does NOT equal the JSON property name. Use one of these two methods:

### Method 1: JSON Schema (Best for exploration)
- Download from: https://github.com/microsoft/powerbi-desktop-samples/tree/main/Report%20Theme%20JSON%20Schema
- Add `"$schema": "./reportThemeSchema.json"` to the theme file
- Use VS Code with Ctrl+Space for autocomplete and property discovery

### Method 2: PBIR File Inspection (Most accurate for specific properties)
1. Save report as PBIP: **File → Save As → PBIP**
2. Enable object name copying: **File → Options → Report settings → "Copy object names when right clicking"**
3. Format the visual in the Format pane as desired
4. Right-click the visual → **Copy object name**
5. Open PBIP folder in VS Code, search all files for the object name
6. Find the `"objects"` node — it shows `cardName` and `propertyName`
7. Translate PBIR syntax to theme JSON syntax (see example below)

### PBIR → Theme JSON Translation Example
PBIR file shows:
```json
"objects": {
  "inputText": [{ "properties": { "pillCornerRadius": { "expr": { "Literal": { "Value": "4L" } } } } }]
}
```
Theme JSON equivalent:
```json
"visualStyles": {
    "textSlicer": { "*": { "inputText": [{ "pillCornerRadius": 4 }] } }
}
```

---

## Property Value Types

| Type | Format | Example |
|---|---|---|
| Boolean | `true` / `false` | `"wordWrap": true` |
| Number | plain number | `"fontSize": 12` |
| String | `"double quoted"` | `"fontFace": "Segoe UI"` |
| Solid color | `{ "solid": { "color": "#RRGGBB" } }` | `"color": { "solid": { "color": "#118DFF" } }` |
| Theme color reference | `{ "expr": { "ThemeDataColor": { "ColorId": N, "Percent": P } } }` | ColorId 0-9, Percent -1.0 to 1.0 |
| Enumeration | string matching pane option | `"position": "BottomCenter"` |

---

## Structural Colors Reference

| JSON Property | Also Called | What It Affects |
|---|---|---|
| `firstLevelElements` | `foreground` | Label text, trend lines, card values, KPI text |
| `secondLevelElements` | `foregroundNeutralSecondary` | Legend labels, axis labels, slicer items |
| `thirdLevelElements` | `backgroundLight` | Gridlines, table grid, shape fills |
| `fourthLevelElements` | `foregroundNeutralTertiary` | Dimmed legend, category labels |
| `background` | — | Label bg inside data points, button fill, tooltip bg |
| `secondaryBackground` | `backgroundNeutral` | Table grid outline, shape map default |
| `tableAccent` | — | Table/matrix grid outline when specified |

---

## Text Classes Reference

Primary classes (set these; secondary classes inherit automatically):

| JSON Class | Formats | Default |
|---|---|---|
| `callout` | Card values, KPI indicators | DIN, 45pt, #252423 |
| `title` | Axis titles, visual titles (via largeTitle) | DIN, 12pt, #252423 |
| `header` | Key influencer headers | Segoe UI Semibold, 12pt, #252423 |
| `label` | Table values, axis labels, legend | Segoe UI, 10pt, #252423 |

```json
"textClasses": {
    "callout": { "fontSize": 45, "fontFace": "DIN", "color": "#252423" },
    "title":   { "fontSize": 12, "fontFace": "DIN", "color": "#252423" },
    "header":  { "fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#252423" },
    "label":   { "fontSize": 10, "fontFace": "Segoe UI", "color": "#252423" }
}
```

---

## Complete Example Theme with Style Presets

```json
{
    "$schema": "./reportThemeSchema.json",
    "name": "Corporate Theme with Presets",
    "dataColors": [
        "#118DFF", "#12239E", "#E66C37", "#6B007B",
        "#E044A7", "#744EC2", "#D9B300", "#D64550"
    ],
    "good": "#1AAB40",
    "neutral": "#D9B300",
    "bad": "#D64554",
    "background": "#FFFFFF",
    "firstLevelElements": "#252423",
    "secondLevelElements": "#605E5C",
    "thirdLevelElements": "#F3F2F1",
    "tableAccent": "#118DFF",
    "textClasses": {
        "title": { "fontSize": 14, "fontFace": "Segoe UI", "color": "#252423" },
        "label": { "fontSize": 10, "fontFace": "Segoe UI", "color": "#252423" }
    },
    "visualStyles": {
        "*": {
            "*": {
                "*": [{ "wordWrap": true }],
                "categoryAxis": [{ "gridlineStyle": "dotted" }]
            }
        },
        "columnChart": {
            "*": {
                "stylePreset": [{ "name": "Minimal" }],
                "legend": [{ "show": false }]
            },
            "Minimal": {
                "legend": [{ "show": false }],
                "valueAxis": [{ "showAxisTitle": false }]
            },
            "With Legend": {
                "legend": [{ "show": true, "position": "BottomCenter" }],
                "valueAxis": [{ "gridlineColor": { "solid": { "color": "#E0E0E0" } } }]
            },
            "Highlighted": {
                "legend": [{ "show": true, "position": "Right" }],
                "valueAxis": [{
                    "gridlineColor": { "solid": { "color": "#118DFF" } },
                    "labelColor": { "solid": { "color": {
                        "expr": { "ThemeDataColor": { "ColorId": 0, "Percent": 0 } }
                    }}}
                }]
            }
        }
    }
}
```

---

## Dark Mode Presets

When the user asks for a dark mode theme or dark background Power BI report, apply these principles. Dark mode is **not** a simple color inversion — it requires a complete palette rethink.

### Core Design Rules

| Principle | Do | Don't |
|---|---|---|
| Background | Dark gray `#1E1E1E`–`#2D2D2D` | Pure black `#000000` |
| Text / labels | Off-white `#E0E0E0`–`#F0F0F0` | Pure white `#FFFFFF` |
| Gridlines | Very subtle `#3A3A3A`–`#4A4A4A` | Medium gray (too bright, competes with data) |
| Data colors | De-saturated & lightened versions | Same bright colors as light mode (creates neon bleed) |
| Font size | Slightly larger (+1–2pt) | Same as light mode (lower contrast makes text harder to read) |

**Contrast target:** Aim for WCAG AA — at least 4.5:1 for text. Test with WebAIM Contrast Checker.

### Dark Mode Color Mapping

Translate the standard Power BI structural colors to dark-friendly values:

| Theme Property | Light Mode Value | Dark Mode Value |
|---|---|---|
| `background` | `#FFFFFF` | `#1E1E1E` |
| `secondaryBackground` | `#F3F2F1` | `#2A2A2A` |
| `firstLevelElements` (text/values) | `#252423` | `#E0E0E0` |
| `secondLevelElements` (axis labels) | `#605E5C` | `#B0B0B0` |
| `thirdLevelElements` (gridlines) | `#C8C6C4` | `#3A3A3A` |
| `tableAccent` | `#118DFF` | `#5E9FD6` |

### Dark Mode Data Color Palettes

**Palette A — Modern Dark** (cool blues, recommended default):
```json
"dataColors": ["#64B5F6", "#FFB74D", "#81C784", "#F48FB1", "#CE93D8", "#80DEEA", "#FFCC02", "#EF9A9A"]
```

**Palette B — Professional Dark** (softer, corporate):
```json
"dataColors": ["#90CAF9", "#FFAB91", "#A5D6A7", "#F48FB1", "#B39DDB", "#80CBC4", "#FFE082", "#FFCCBC"]
```

**Key rule:** De-saturate light-mode colors by ~20–30%. Use HSL lightness 60–75% for data colors on dark backgrounds. Avoid neon/fully saturated hues.

### Dark Mode Structural Colors Block

```json
{
    "name": "My Dark Theme",
    "background": "#1E1E1E",
    "secondaryBackground": "#2A2A2A",
    "tableAccent": "#5E9FD6",
    "firstLevelElements": "#E0E0E0",
    "secondLevelElements": "#B0B0B0",
    "thirdLevelElements": "#3A3A3A",
    "fourthLevelElements": "#6E6E6E",
    "good": "#81C784",
    "neutral": "#FFB74D",
    "bad": "#EF9A9A",
    "dataColors": ["#64B5F6", "#FFB74D", "#81C784", "#F48FB1", "#CE93D8", "#80DEEA", "#FFCC02", "#EF9A9A"]
}
```

### Dark Mode Text Classes

Increase font size slightly and use off-white:

```json
"textClasses": {
    "callout": { "fontSize": 45, "fontFace": "DIN", "color": "#E0E0E0" },
    "title":   { "fontSize": 14, "fontFace": "Segoe UI", "color": "#F0F0F0" },
    "header":  { "fontSize": 13, "fontFace": "Segoe UI Semibold", "color": "#E0E0E0" },
    "label":   { "fontSize": 11, "fontFace": "Segoe UI", "color": "#C0C0C0" }
}
```

### Dark Mode Visual Style Adjustments

#### 1. Per-Visual Background Color — slicers are the exception

Set a dark `background` card globally on all visuals via `"*"`. Then **explicitly suppress it for slicers** — slicers should blend into the page canvas, not sit inside a filled box. Instead, color the slicer's values area using `items.background`, which targets only the selectable items inside the slicer (list rows / dropdown popup), not the outer visual container.

```json
"visualStyles": {
    "*": {
        "*": {
            "background": [{ "show": true, "color": { "solid": { "color": "#2A2A2A" } }, "transparency": 0 }],
            "categoryAxis": [{ "gridlineColor": { "solid": { "color": "#3A3A3A" } } }],
            "valueAxis": [{ "gridlineColor": { "solid": { "color": "#3A3A3A" } } }],
            "border": [{ "show": false }]
        }
    },
    "slicer": {
        "*": {
            "background": [{ "show": false }],
            "items": [{
                "fontColor": { "solid": { "color": "#E0E0E0" } },
                "background": { "solid": { "color": "#2A2A2A" } }
            }],
            "data": [{
                "fontColor": { "solid": { "color": "#E0E0E0" } },
                "fontSize": 11
            }],
            "header": [{
                "show": true,
                "fontColor": { "solid": { "color": "#E0E0E0" } },
                "background": { "solid": { "color": "#252525" } },
                "fontSize": 12,
                "outline": "BottomOnly"
            }]
        }
    }
}
```

> **Also suppress** `group`, `basicShape`, and `image` visuals: `"group": { "*": { "background": [{ "show": false }] } }`.

#### 2. Alternating Row Colors for tableEx and matrix — applies to EVERY dark-background style preset

This is the most common dark mode breakage: Power BI's default secondary row color is white (or near-white). On a dark background this makes every other row flash white — one row looks fine (dark bg + light text) and the next looks terrible (white bg + light text, nearly unreadable).

**⚠️ This rule applies to EVERY named style preset that uses a dark background — not just the default `"*"` style.** If you create additional named presets (e.g. `"Dark Compact"`, `"Dark Highlighted"`, `"Executive Dark"`), each one that has a dark background must independently repeat all four row color properties. Named presets only inherit from `"*"` but do NOT inherit the `values` row colors reliably across presets — Power BI can fall back to its base theme defaults, which are light-mode values. **Any time you define a new dark-background preset for a table or matrix, add the full four-property `values` block to it.**

```json
"tableEx": {
    "*": {
        "grid": [{
            "gridVertical": false,
            "gridHorizontal": true,
            "gridHorizontalColor": { "solid": { "color": "#3A3A3A" } },
            "outlineColor": { "solid": { "color": "#3A3A3A" } }
        }],
        "columnHeaders": [{
            "fontColor": { "solid": { "color": "#E0E0E0" } },
            "backColor": { "solid": { "color": "#252525" } }
        }],
        "values": [{
            "fontColorPrimary":   { "solid": { "color": "#E0E0E0" } },
            "backColorPrimary":   { "solid": { "color": "#2A2A2A" } },
            "fontColorSecondary": { "solid": { "color": "#E0E0E0" } },
            "backColorSecondary": { "solid": { "color": "#333333" } }
        }],
        "total": [{
            "fontColor": { "solid": { "color": "#E0E0E0" } },
            "backColor": { "solid": { "color": "#252525" } }
        }]
    },
    "Dark Compact": {
        "values": [{
            "fontColorPrimary":   { "solid": { "color": "#E0E0E0" } },
            "backColorPrimary":   { "solid": { "color": "#2A2A2A" } },
            "fontColorSecondary": { "solid": { "color": "#E0E0E0" } },
            "backColorSecondary": { "solid": { "color": "#333333" } }
        }]
    }
}
```

The same pattern applies to `matrix` — repeat the `values` block in every named dark preset:

```json
"matrix": {
    "*": {
        "grid": [{
            "gridVertical": false,
            "gridHorizontal": true,
            "gridHorizontalColor": { "solid": { "color": "#3A3A3A" } },
            "outlineColor": { "solid": { "color": "#3A3A3A" } }
        }],
        "columnHeaders": [{
            "fontColor": { "solid": { "color": "#E0E0E0" } },
            "backColor": { "solid": { "color": "#252525" } }
        }],
        "rowHeaders": [{
            "fontColor": { "solid": { "color": "#E0E0E0" } },
            "backColor": { "solid": { "color": "#2A2A2A" } }
        }],
        "values": [{
            "fontColorPrimary":   { "solid": { "color": "#E0E0E0" } },
            "backColorPrimary":   { "solid": { "color": "#2A2A2A" } },
            "fontColorSecondary": { "solid": { "color": "#E0E0E0" } },
            "backColorSecondary": { "solid": { "color": "#333333" } }
        }],
        "subTotals": [{
            "fontColor": { "solid": { "color": "#E0E0E0" } },
            "backColor": { "solid": { "color": "#252525" } }
        }]
    },
    "Dark Compact": {
        "values": [{
            "fontColorPrimary":   { "solid": { "color": "#E0E0E0" } },
            "backColorPrimary":   { "solid": { "color": "#2A2A2A" } },
            "fontColorSecondary": { "solid": { "color": "#E0E0E0" } },
            "backColorSecondary": { "solid": { "color": "#333333" } }
        }]
    }
}
```


> **Checklist when adding any new dark-background named preset for tableEx or matrix:**
> 1. Does this preset use a dark background? → Yes → add the full `values` block with all four properties
> 2. Did you add it to both `tableEx` AND `matrix`? → Do both together, they share the same breakage pattern

#### Other key visual overrides

```json
"columnChart": {
    "*": {
        "stylePreset": [{ "name": "Dark Clean" }],
        "legend": [{ "show": false }]
    },
    "Dark Clean": {
        "valueAxis": [{ "showAxisTitle": false }]
    },
    "Dark With Legend": {
        "legend": [{ "show": true, "position": "BottomCenter" }]
    }
},
"card": {
    "*": {
        "labels": [{ "color": { "solid": { "color": "#B0B0B0" } } }]
    }
}
```

### Dark Mode Pitfalls

- **Don't invert colors naively** — bright colors on dark backgrounds create visual "bleed" (neon glow effect)
- **Avoid pure black** — `#000000` is too harsh; use `#1E1E1E` or `#2D2D2D`
- **Slicers: suppress visual background, set items background** — set `background.show: true` globally, then override slicers with `background: show false` so they don't get a filled box; separately set `items.background` to dark for the selectable values area. These are two different properties — the global background rule does NOT color slicer items
- **Repeat row colors in every dark-background named preset** — set all four of `backColorPrimary`, `fontColorPrimary`, `backColorSecondary`, `fontColorSecondary` in `"*"` AND in every additional dark-background named preset for `tableEx` and `matrix`. Named presets do not reliably inherit row colors from `"*"` — any preset you add without them will show the broken "one row fine, one row white" problem
- **Keep text minimal** — reading long text on dark backgrounds is harder; lean on visuals
- **Limit data colors to 4–5** — too many colors overwhelm on dark backgrounds
- **Gridlines must be subtle** — in dark mode they should nearly disappear, just guiding the eye
- **Maintain color meaning** — if red = bad in light mode, use a soft red in dark mode too (e.g., `#EF9A9A`)
-**Title color** - When generating a dark mode theme, you MUST explicitly override visual titles to use a light font color.


---

## Step-by-Step Workflow

When a user asks to create or extend a theme with style presets:

1. **Clarify scope** — which visual types need presets? What formatting matters (colors, legend, axes, labels, fonts)?
2. **Design preset names** — clear, meaningful names that will appear in the UI dropdown
3. **Define the `"*"` default** — set baseline formatting + default preset name via `stylePreset`
4. **Define each named preset** — only include what differs from the default
5. **Combine with top-level theme settings** — add `dataColors`, `textClasses`, structural colors as needed
6. **Validate** — remind user to validate against JSON schema in VS Code before importing
7. **Import instructions** — View ribbon → Themes dropdown → Browse for themes → select the JSON file

---

## Common Pitfalls

- Do NOT copy property names from the formatting pane — use schema or PBIR
- Do NOT define the same preset name twice for one visual type
- Do NOT put conditional formatting rules in the theme — not supported
- ALWAYS set `"stylePreset": [{ "name": "..." }]` inside `"*"` to set the default active preset
- Named presets inherit from `"*"` — define shared settings there, only put overrides in named presets
- Use `"$schema"` reference for VS Code autocomplete help

---

## Reference Files

Read these when you need deeper detail:

- `references/card-property-examples.md` — Common card names and property examples per visual type
- `assets/starter-theme.json` — Minimal light-mode starter template ready to customize
- `assets/dark-mode-starter-theme.json` — Ready-to-import dark mode starter theme with presets, data colors, structural colors, and key visual overrides