# Top Products Bar Chart — Design Spec
**Date:** 2026-05-06
**Status:** Approved

## Goal

Add a vertical bar chart below the revenue trend chart showing total revenue by product, filtered by the existing date range selection (`st.session_state.trend_start` / `trend_end`).

## Data Layer

**Function:** `get_product_revenue()`
- Decorator: `@st.cache_data(ttl=600)`
- Source: `basket_craft.raw.orders` JOIN `basket_craft.raw.products` ON `primary_product_id = product_id`
- Date conversion: `TO_TIMESTAMP(created_at / 1000000000)` (nanoseconds → seconds, same as existing functions)
- Returns: `pandas.DataFrame` with columns `month` (string `YYYY-MM`), `month_date` (Python `datetime.date`, first of month), `product_name` (string), `revenue` (float)
- SQL groups by month string and product, ordered ascending by month
- `month_date` derived in Python: `pd.to_datetime(df["month"] + "-01").dt.date` — same pattern as `get_revenue_trend()`
- Expected size: ~148 rows (4 products × 37 months)

**SQL pattern:**
```sql
SELECT
    TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(o.created_at / 1000000000)), 'YYYY-MM') AS month,
    p.product_name,
    SUM(o.price_usd)::FLOAT AS revenue
FROM basket_craft.raw.orders o
JOIN basket_craft.raw.products p ON o.primary_product_id = p.product_id
GROUP BY 1, 2
ORDER BY 1 ASC
```

## Filter Logic

- Reads `st.session_state.trend_start` and `st.session_state.trend_end` (Python `datetime.date` objects set by the existing date filter)
- No new UI widgets — the chart automatically respects the existing preset/date-picker controls
- Filtering applied in Python: slice DataFrame by `month_date`, then `groupby("product_name")["revenue"].sum()`, sort descending by revenue

## Chart

- Library: **Altair** (already imported)
- Mark: `mark_bar()`
- X axis: `product_name:N`, title "Product", axis labels not angled (names are short enough)
- Y axis: `revenue:Q`, title "Revenue ($)", formatted `$,.0f`
- Tooltip: product name + revenue (`$,.0f`)
- Height: 300px
- `st.altair_chart(chart, use_container_width=True)`
- Empty-filter guard: if filtered DataFrame is empty, show `st.info("No data in the selected date range.")`

## Layout (appended below trend chart section)

```
st.divider()
st.subheader("Top Products by Revenue")
try:
    ... query, filter, chart ...
except Exception as e:
    st.error(f"Failed to load product chart: {e}")
```

## Error Handling

Wrapped in its own `try/except` block — failures are isolated from the trend chart and KPI cards above.

## Out of Scope

- Filtering the KPI cards or trend chart from this chart
- Drill-down into individual orders by product
- Showing more than 4 products (only 4 exist in the catalog)
- Color-coding bars by product
