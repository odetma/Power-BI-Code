# Power BI Theme: Card & Property Examples per Visual Type

This reference lists the most commonly used `cardName` values and their properties for the most popular visual types. Use these when writing `visualStyles` in a theme JSON file.

---

## All Visuals (`*`)

```json
"*": {
    "*": {
        "background": [{ "show": true, "color": { "solid": { "color": "#FFFFFF" } }, "transparency": 0 }],
        "border": [{ "show": false, "color": { "solid": { "color": "#CCCCCC" } }, "radius": 4 }],
        "title": [{ "show": true, "fontColor": { "solid": { "color": "#252423" } }, "fontSize": 12, "fontFamily": "Segoe UI" }],
        "visualHeader": [{ "show": true }],
        "*": [{ "wordWrap": true }]
    }
}
```

---

## Column Chart / Bar Chart (`columnChart`, `barChart`, `stackedColumnChart`, `stackedBarChart`)

```json
"columnChart": {
    "*": {
        "stylePreset": [{ "name": "MyPreset" }],
        "legend": [{ "show": true, "position": "BottomCenter", "fontSize": 10 }],
        "categoryAxis": [{
            "show": true,
            "showAxisTitle": false,
            "gridlineStyle": "dotted",
            "gridlineColor": { "solid": { "color": "#E0E0E0" } }
        }],
        "valueAxis": [{
            "show": true,
            "showAxisTitle": false,
            "gridlineStyle": "solid",
            "gridlineColor": { "solid": { "color": "#E0E0E0" } },
            "labelColor": { "solid": { "color": "#605E5C" } }
        }],
        "dataLabels": [{ "show": false, "fontSize": 9 }],
        "plotArea": [{ "transparency": 0 }]
    }
}
```

---

## Line Chart (`lineChart`)

```json
"lineChart": {
    "*": {
        "legend": [{ "show": true, "position": "TopCenter" }],
        "categoryAxis": [{ "showAxisTitle": false }],
        "valueAxis": [{ "showAxisTitle": false, "gridlineStyle": "dashed" }],
        "lineStyles": [{ "strokeWidth": 2, "lineStyle": "solid", "showMarker": false }],
        "dataLabels": [{ "show": false }]
    }
}
```

---

## Card (`card`)

```json
"card": {
    "*": {
        "labels": [{
            "color": { "solid": { "color": "#252423" } },
            "fontSize": 40,
            "fontFamily": "DIN"
        }],
        "categoryLabels": [{
            "show": true,
            "color": { "solid": { "color": "#605E5C" } },
            "fontSize": 12
        }],
        "background": [{ "show": false }],
        "border": [{ "show": false }]
    }
}
```

---

## Table (`tableEx`)

```json
"tableEx": {
    "*": {
        "grid": [{
            "gridVertical": true,
            "gridHorizontal": true,
            "gridVerticalColor": { "solid": { "color": "#E0E0E0" } },
            "gridHorizontalColor": { "solid": { "color": "#E0E0E0" } },
            "rowPadding": 4,
            "outlineColor": { "solid": { "color": "#252423" } },
            "outlineWeight": 1
        }],
        "columnHeaders": [{
            "fontColor": { "solid": { "color": "#FFFFFF" } },
            "backColor": { "solid": { "color": "#118DFF" } },
            "fontSize": 11,
            "fontFamily": "Segoe UI Semibold"
        }],
        "values": [{
            "fontColor": { "solid": { "color": "#252423" } },
            "fontSize": 10,
            "urlIconPosition": "Right"
        }],
        "total": [{
            "fontColor": { "solid": { "color": "#252423" } },
            "backColor": { "solid": { "color": "#F3F2F1" } },
            "fontSize": 11
        }]
    }
}
```

---

## Matrix (`matrix`)

```json
"matrix": {
    "*": {
        "grid": [{
            "gridVertical": false,
            "gridHorizontal": true,
            "gridHorizontalColor": { "solid": { "color": "#E0E0E0" } },
            "rowPadding": 4
        }],
        "columnHeaders": [{
            "fontColor": { "solid": { "color": "#252423" } },
            "backColor": { "solid": { "color": "#F3F2F1" } },
            "fontSize": 11,
            "outline": "BottomOnly"
        }],
        "rowHeaders": [{
            "fontColor": { "solid": { "color": "#252423" } },
            "fontSize": 10,
            "outline": "RightOnly"
        }],
        "values": [{ "fontSize": 10 }],
        "subTotals": [{
            "rowSubtotals": true,
            "columnSubtotals": true,
            "fontColor": { "solid": { "color": "#252423" } },
            "backColor": { "solid": { "color": "#EAF2FF" } }
        }]
    }
}
```

---

## Slicer (`slicer`)

```json
"slicer": {
    "*": {
        "data": [{
            "fontColor": { "solid": { "color": "#252423" } },
            "fontSize": 11,
            "fontFamily": "Segoe UI"
        }],
        "header": [{
            "show": true,
            "fontColor": { "solid": { "color": "#252423" } },
            "background": { "solid": { "color": "#F3F2F1" } },
            "fontSize": 12,
            "outline": "BottomOnly"
        }],
        "items": [{ "outline": "Frame", "fontColor": { "solid": { "color": "#252423" } } }]
    }
}
```

---

## KPI (`kpi`)

```json
"kpi": {
    "*": {
        "indicator": [{
            "kpiIndicatorFontSize": 40,
            "kpiIndicatorText": { "solid": { "color": "#252423" } }
        }],
        "goals": [{ "show": true }],
        "trendline": [{ "show": true, "lineColor": { "solid": { "color": "#118DFF" } } }]
    }
}
```

---

## Scatter Chart (`scatterChart`)

```json
"scatterChart": {
    "*": {
        "bubbles": [{ "bubbleSize": 0 }],
        "categoryAxis": [{ "showAxisTitle": false }],
        "valueAxis": [{ "showAxisTitle": false }],
        "legend": [{ "show": true, "position": "BottomCenter" }]
    }
}
```

---

## Filter Card (special — uses `$id`)

```json
"*": {
    "*": {
        "filterCard": [
            {
                "$id": "Applied",
                "foregroundColor": { "solid": { "color": "#252423" } },
                "border": true,
                "borderColor": { "solid": { "color": "#118DFF" } }
            },
            {
                "$id": "Available",
                "border": false,
                "foregroundColor": { "solid": { "color": "#605E5C" } }
            }
        ]
    }
}
```

---

## Notes

- Card names shown here are common but not exhaustive — use the JSON schema or PBIR method for exact names
- Property enumerations (like `"position"` values) must match what Power BI accepts; common ones include:
  - Legend position: `"Top"`, `"Bottom"`, `"Left"`, `"Right"`, `"TopCenter"`, `"BottomCenter"`
  - Outline: `"None"`, `"BottomOnly"`, `"TopOnly"`, `"LeftOnly"`, `"RightOnly"`, `"Frame"`
  - Gridline style: `"solid"`, `"dashed"`, `"dotted"`