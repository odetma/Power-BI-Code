# Design standard

Team branding is optional configuration, not an installation prerequisite. Preserve an existing report's theme and layout conventions. For a new report, agree the business story and use the defaults below unless the user supplies a team standard.

## Template and theme
- **Existing report:** follow the template and theme it already has, so pages never mix styles. If it doesn't match the team standard, **flag it to the developer and change nothing about it without approval.**
- **New report:** use a supplied team template/theme when available. Otherwise use native visuals and a consistent built-in theme; do not invent a corporate brand.

### Theme
Optional team choices: card/background colors, fonts, borders, spacing, primary colors, comparison colors, and status semantics. Sensible new-page defaults are Segoe UI, a light neutral canvas, white content surfaces, blue actuals, and a muted dashed prior-period line. Preserve an existing report's configured equivalents. Use status color with text or symbols, not color alone.

**To apply a theme file to a new report:**
1. Copy the theme JSON to `<name>.Report/StaticResources/RegisteredResources/`.
2. In `definition/report.json`, set `themeCollection.customTheme.name` to the file name.
3. In `resourcePackages` -> `RegisteredResources`, add or replace an item with `name`/`path` = the file name and `type` `CustomTheme`.

Visuals that carry their own formatting keep it. The theme only fills properties a visual doesn't set. Power BI colors come from the theme, not from per-visual hex values: if a report is off-theme, fix the theme.

### Page template
A practical new-page starting point is a 1280 by 800 canvas in FitToPage mode, a question-led header, visible period context, compact filters, a KPI row, two to four analysis visuals, and a short takeaway. Keep freshness/definitions legible. Agree any logo or navigation requirements with the user rather than adding placeholders.

Copy template elements from an existing report that already follows it, rather than recreating them.

## Principles
1. **Tell a story, not a sequence of pages.** One question per page, ordered by flow. Name pages after their question.
2. **Lead to action.** Don't only show the number; ask what it should make someone do, and make that step easy: who to contact (owner), links out to the source systems, a "needs attention" list and a details table, risk colors that point the eye.
3. **No TMI.** Working memory is small: a KPI row plus 2-4 visuals per page. Move detail to a drill page, a tooltip page or the details table.
4. **Uniform colors.** The same meaning uses the exact same hex on every page. No decorative color.
5. **Every number has context:** vs the previous period, vs a target, or a status. A bare number is noise.
6. **Same metric = same name, format and definition everywhere.**
7. **Scope and freshness on every page:** a period title ("Showing Aug 10 - Oct 4 - 8 complete weeks"), refresh date, and scope notes.
8. **Titles say something:** prefer dynamic titles/subtitles that state the point. A subtitle explains what's shown whenever it isn't straightforward (scope, definition, data lag).
9. **No hardcoded text or thresholds:** texts and thresholds come from measures and a targets table, so they never drift from the logic.

## Visual conventions
- Data labels instead of a value axis, no gridlines.
- **Comparison lines** (last year, previous period, target): dashed, no markers, no labels.
- **Combo charts:** color the line's labels like the line, so it's clear which number belongs to which series.
- **Tooltips:** short FYI text in an info button. A report-page tooltip (more than FYI) gets a visible hint icon in the visual's corner.
- **Slicers:**
  - show only values that exist in the fact table
  - hierarchies open collapsed (explicit `expansionStates`)
  - meaningful defaults (e.g. last 8 complete weeks)
  - pane filters are dropdowns; a checkbox list or tiles need a visual reason
  - a filter whose meaning isn't obvious gets an info button with a one-line definition
- **Two charts with the same axis and a different breakdown:** one chart with a field parameter and view buttons in its corner, not two charts.
- **Legends with long names** go on the right, without the legend title, so names aren't cut.
- **Accessibility:** red/green always together with an arrow or icon, readable font sizes, text contrast of at least 4.5:1.
- **Placeholders** for data that isn't ready: a muted "Coming soon" card that says what's missing, not an empty visual.
- **Sensitive data** (HR, finance): aggregate level only, object/row-level security, and a note on the page saying who can see it. OLS/RLS applies only to workspace Viewers and app/share users; Admin, Member and Contributor bypass it.
