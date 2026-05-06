# Revenue Trend Chart — Design Spec
**Date:** 2026-05-06
**Status:** Approved

## Goal
Add a monthly revenue trend line chart to the BasketCraft dashboard with preset + custom date range filtering, implemented entirely in `app.py`.

## Data Layer

**Function:** `get_revenue_trend()`
- Decorator: `@st.cache_data(ttl=600)`
- Source: `basket_craft.raw.orders`
- Date conversion: `TO_TIMESTAMP(created_at / 1000000000)` (nanoseconds → seconds epoch)
- Returns: `pandas.DataFrame` with columns `month` (string, `YYYY-MM`) and `revenue` (float), ordered ascending by month
- SQL pattern: GROUP BY `DATE_TRUNC('month', ...)`, aggregate `SUM(price_usd)`, cast month to `TO_CHAR(..., 'YYYY-MM')`

## Filter UI

Placed inline between the KPI row and the chart, in a single `st.columns(3)` row:

| Column 1 | Column 2 | Column 3 |
|---|---|---|
| Preset radio (horizontal): Last 6M / Last 12M / All Time | Start date picker (`st.date_input`) | End date picker (`st.date_input`) |

**Preset behaviour:**
- Selecting a preset sets start/end pickers to match (Last 6M = 6 months before max month in data; Last 12M = 12 months before; All Time = full range)
- Editing either picker does not change the preset selection (user is now in "custom" mode)
- Default on load: Last 12M

**Filtering:** Applied in Python against the cached DataFrame — no re-query to Snowflake.

## Chart

- Library: **Altair** (bundled with Streamlit, no new dependency)
- Mark: line + point overlay
- X axis: `month` (ordinal), label every 3 months to avoid crowding
- Y axis: `revenue` (quantitative), formatted as `$,.0f`
- Tooltip: month + revenue (`$,.0f`)
- Rendered with `st.altair_chart(chart, use_container_width=True)`

## Layout (full page, top to bottom)

1. `st.title` — "BasketCraft Dashboard"
2. KPI row — four `st.metric` cards (existing)
3. `st.divider`
4. `st.subheader` — "Monthly Revenue"
5. Filter row — presets + date pickers
6. Altair chart — full width

## Error Handling

The chart section is wrapped in the existing `try/except` block. If `get_revenue_trend()` fails, `st.error` displays the message; the KPI cards are unaffected.

## Out of Scope

- Filtering the KPI cards by the selected date range
- Adding other metrics (orders, AOV) to the trend chart
- Sidebar navigation
