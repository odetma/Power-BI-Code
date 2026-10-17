# Chart choice and the 19-rule Definition of Done

## Chart choice
Match on the **comparison being made**, not on the data type.

| The question | Use | Notes |
|---|---|---|
| How did X move over time? | Line (12+ points) or column (12 or fewer periods) | |
| Time trend + a rate on top | Combo (column + line) | Avoid a second labeled axis; label the line's points |
| How do categories compare? | Horizontal bar, sorted descending | Horizontal when labels are long names |
| Which parts make up the whole? | Stacked bar, or 100% stacked for share | Pie only at 3 slices or fewer; no donuts |
| Where does volume drop off in a process? | Funnel | Exempt from the axis/label rules |
| What's the distribution? | Histogram or box plot | A banded bar is often easier for stakeholders |
| Does A relate to B? | Scatter | Add a reference line or it's decorative |
| One number vs a target | KPI card + sparkline | A card alone hides direction |
| Retention by cohort age | Small-multiples stacked bar, or heatmap matrix | Watch right-censoring |
| Actionable list of entities | Table/matrix with data bars | |
| Composition changing over time | Stacked area only with 4 series or fewer | Otherwise small multiples |
| Geographic spread | Usually a bar by country | Maps rarely answer the question |

Never draw a line across categories: it invents a trend that doesn't exist.

**Cardinality limits**

| Visual | Comfortable | Hard stop |
|---|---|---|
| Bar / column categories | 12 | more than 25 -> Top N + "Other", or a table |
| Line series | 5 | more than 7 -> small multiples |
| Stacked segments | 5 | more than 6 -> group the tail |
| Pie slices | 3 | 3 |
| Legend entries | 5 | more than 6 -> direct labels |

**Formatting defaults:** 0 decimals unless a decimal changes a decision. Negative currency in parentheses. Abbreviate K/M/B consistently across the page. Time axis defaults to one granularity. Sort bars by value unless the category has a natural order (then use a sort-order column).

**Native vs HTML:** native visuals by default (cross-filtering, drill). An HTML Content visual from a DAX measure only when the layout itself is the requirement.

**Writing insights:** lead with the movement and its cause, not the value. Compare like with like (month-to-date vs the same days of last month). Name the entities people act on. Flag low-denominator percentage spikes. No internal column names in stakeholder-facing text.

## How to review
1. Confirm the input is a Power BI report page.
2. **Sweep all visuals for one rule at a time,** then write a single consolidated finding for that rule listing every affected visual. Each rule ID appears at most once per page.
3. **Only report what is visible or in the files.** Never infer a formatting-pane setting you can't see.
4. **Single page -> skip cross-page rules.**
5. **Prefer the PBIR JSON over screenshots.** Screenshot judgment is inconsistent run to run; config properties are deterministic.

Severity is binary: **Must Fix** (misleads the reader, breaks usability, or violates a core standard) / **Nice to Have** (polish).

## The rules

| # | Rule | Severity | How to check (PBIR) |
|---|---|---|---|
| 1 | Consistent number formatting (same K/M/B style and decimals on the page; 0 preferred, 2 max) | Must | format strings on `labels`, `valueAxis`, measures |
| 2 | Value axis OR data labels, not both | Nice | `labels.show` (default off) + `valueAxis.show` (default on) |
| 3 | No dual Y-axis | Must | `secValueAxis.show` / `y2Axis.show` |
| 4 | Y-axis starts at zero on bar/column | Must | `valueAxis.start` set and not 0 |
| 5 | Hide the Y-axis title | Nice | flag only when the title is actually visible: `valueAxis.show` (default on) **and** `valueAxis.showAxisTitle` true. A leftover `titleText` with the title or axis off is not a finding |
| 6 | Stacked charts show a total per bar | Nice | `totalLabels.show` on plain stacked bar/column; 100% stacked exempt |
| 7 | Spacious layout (no overlaps, colliding labels, squeezed elements) | Must; truncated table columns Nice | container `x/y/width/height`; table `autoSizeColumnWidth` |
| 8 | Consistent color: same meaning = same color | Nice | `dataPoint.fill` / `defaultColor` across visuals |
| 9 | No decorative elements | Nice | shapes/images/textboxes with no data purpose |
| 10 | Aligned and grouped | Nice | edges that differ by 2-10 px |
| 11 | Consistent typography | Nice | `title.fontFamily` / `fontSize`; treat "Segoe UI" and "Segoe UI Semibold" as one family |
| 12 | *(Optional)* Brand logo on every page | Must if your standard has one | detect **by position**: any `image` in the top-left header corner (y <= 120 px, x <= 15% of page width). File names of logos are random, so don't rely on them |
| 13 | Drill / action buttons not obscured | Must if unreachable | overlapping coordinates with a button |
| 14 | Titles help the reader | Nice; Must if the title contradicts the data | `title.show` / `title.text`; tables/matrices exempt |
| 15 | Subheader stating the active filter/period context | Nice | text boxes on dense pages |
| 16 | Info buttons for non-obvious metrics | Nice | `actionButton` info icons on complex pages |
| 17 | No in-canvas navigation to pages in the tab bar | **Must, always** | see below |
| 18 | Time axis defaults to one granularity | Nice | `HierarchyLevel` projections: exactly one `active` |
| 19 | Cross-page consistency (slicer placement, fonts, color meanings) | Nice | compare the above across pages; multi-page only |

### Rule 17 in detail
Flag:
- native `pageNavigator` visuals
- buttons with `visualLink.type` PageNavigation whose `navigationSection` is a different **visible** page, or a measure-driven (conditional) target
- buttons with `visualLink.type` Bookmark, and `bookmarkNavigator` visuals, whose bookmark opens a different visible page. Read `definition/bookmarks/` (`explorationState.activeSection`, bookmark groups) to tell.

Allowed:
- navigation to hidden pages (the only way in)
- Drillthrough, Back, WebUrl, ClearAllSlicers
- PageNavigation buttons with no target (info icons used for their tooltip)
- bookmark navigators that stay on the same page (view toggles)

Approved exceptions (e.g. a diagram whose shapes open pages) should be noted in the PR, since a tool can't know them.

## Exemptions learned from false positives
1. Combo chart -> Rule 2 does not apply.
2. Funnel chart -> Rules 2 and 5 exempt.
3. Data bars in a table/matrix -> not a Rule 8 color issue.
4. Toggle buttons (% / Total) -> not Rule 6 stacked segments.
5. Table with a scrollbar -> Rule 7 truncation exempt.
6. Gridlines without numbers -> not a visible axis for Rule 2.
7. A date hierarchy is fine; Rule 18 is about the default level.

## Output format
```
Must Fix
Rule 3 - No dual Y-axis charts
Location: <page> - "<visual title>"
Problem:  <what's wrong>
Fix:      <specific action in the formatting pane / model>
```
Group Must Fix before Nice to Have. Cross-page findings in their own section, only for multi-page reviews. Close with a one-line verdict.

As a sheet: tab-separated columns `Page, Severity, Rule ID, Rule, Location, Problem, Fix`.
