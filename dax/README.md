# DAX

Reusable DAX snippets and query functions.

## Contents

| File | Purpose |
| --- | --- |
| [`time-intelligence/prior-period-dates.dax`](time-intelligence/prior-period-dates.dax) | Returns a prior-period date table based on a selected YoY/QoQ/MoM parameter. |
| [`time-intelligence/same-period-last-year-safe.dax`](time-intelligence/same-period-last-year-safe.dax) | Safer same-period-last-year logic for incomplete month selections and leap-year edge cases. |

## Usage Notes

- These are DAX query functions. Add or adapt them in a query/function context that supports `DEFINE FUNCTION`.
- Replace sample table and column names such as `DIM_DATE[Date]` or `DW_DIM_DATE_VW[DATE_ID]` with your own date table.
- Test with month-end, February, and leap-year selections before using in production reports.
