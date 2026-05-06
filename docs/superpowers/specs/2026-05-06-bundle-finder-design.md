# Bundle Finder — Design Spec
**Date:** 2026-05-06
**Status:** Approved

## Goal

Add a Bundle Finder section below the Top Products chart. The user picks a product from a selectbox, and the dashboard shows which other products are most frequently bought in the same order, ranked by co-occurrence count, filtered by the existing date range.

## Data Layer

### `get_products()`
- Decorator: `@st.cache_data(ttl=600)`
- Source: `basket_craft.raw.products`
- Returns: `pandas.DataFrame` with columns `product_id` (int), `product_name` (string)
- Used to populate the selectbox and map selected name → product ID

**SQL:**
```sql
SELECT product_id, product_name
FROM basket_craft.raw.products
ORDER BY product_name ASC
```

### `get_bundle_pairs(product_id)`
- Decorator: `@st.cache_data(ttl=600)`
- Parameter: `product_id` (int) — cache key, one entry per product (4 max)
- Source: self-join `basket_craft.raw.order_items` on `order_id`, filtered to rows where `oi_a.product_id = %s`, joined to `basket_craft.raw.products` for co-product name
- Date conversion: `TO_TIMESTAMP(oi_a.created_at / 1000000000)` (nanoseconds → seconds, same pattern as existing functions)
- Returns: `pandas.DataFrame` with columns:
  - `month` — string `YYYY-MM`
  - `month_date` — Python `datetime.date`, first of month (derived in Python: `pd.to_datetime(df["month"] + "-01").dt.date`)
  - `co_product` — string, name of the co-purchased product
  - `order_count` — int, number of orders containing both products in that month

**SQL:**
```sql
SELECT
    TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(oi_a.created_at / 1000000000)), 'YYYY-MM') AS month,
    p.product_name AS co_product,
    COUNT(DISTINCT oi_a.order_id)::INT AS order_count
FROM basket_craft.raw.order_items oi_a
JOIN basket_craft.raw.order_items oi_b
  ON oi_a.order_id = oi_b.order_id AND oi_b.product_id != oi_a.product_id
JOIN basket_craft.raw.products p ON oi_b.product_id = p.product_id
WHERE oi_a.product_id = %s
GROUP BY 1, 2
ORDER BY 1 ASC
```

## Filter Logic

- Reads `st.session_state.trend_start` and `st.session_state.trend_end` (Python `datetime.date` objects set by the existing date filter)
- If either is `None`, show `st.info("Set a date range above to see bundle data.")`
- Filter applied in Python: slice DataFrame by `month_date`, then `groupby("co_product")["order_count"].sum()`, sort descending

## UI

- **Product selector**: `st.selectbox("Select a product", options=product_names)` where `product_names` comes from `get_products()["product_name"].tolist()`
- **Result**: `st.dataframe` with columns renamed to "Product" and "Orders Together"; index hidden
- **Empty guard**: if filtered result is empty, show `st.info("No bundle data in the selected date range.")`

## Layout (appended below Top Products section)

```
st.divider()
st.subheader("Bundle Finder")
try:
    ... get_products(), selectbox, get_bundle_pairs(product_id), filter, table ...
except Exception as e:
    st.error(f"Failed to load bundle finder: {e}")
```

## Error Handling

Wrapped in its own `try/except` block — failures are isolated from all other sections.

## Out of Scope

- Color-coding or highlighting the strongest co-purchase pair
- Showing co-occurrence as a percentage of total orders
- Filtering the KPI cards or trend chart from the bundle finder
- Drill-down into individual orders containing both products
