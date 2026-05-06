# Bundle Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Bundle Finder section to the BasketCraft dashboard where the user picks a product and sees which other products are most frequently co-purchased, filtered by the existing date range.

**Architecture:** Two new cached query functions (`get_products` and `get_bundle_pairs`) follow the established `try/finally cur.close()` cursor pattern. `get_bundle_pairs` is parameterized by product ID so each of the 4 products gets its own cache entry. The UI section reads `st.session_state.trend_start`/`trend_end` set by the existing date filter, aggregates in Python, and renders with `st.dataframe` — no new date UI widgets.

**Tech Stack:** Streamlit, Snowflake connector, pandas

---

### Task 1: Add `get_products()` data function

**Files:**
- Modify: `app.py` (insert after `get_product_revenue()`, before the `try:` block that renders KPI cards)

- [ ] **Step 1: Write and run a standalone verification script**

Create `_test_products_lookup.py` in the project root to confirm the query works:

```python
# _test_products_lookup.py  (delete after verifying)
import snowflake.connector, os, pandas as pd
from dotenv import load_dotenv
load_dotenv(override=True)
conn = snowflake.connector.connect(
    account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.environ['SNOWFLAKE_USER'],
    password=os.environ['SNOWFLAKE_PASSWORD'], role=os.environ['SNOWFLAKE_ROLE'],
    warehouse=os.environ['SNOWFLAKE_WAREHOUSE'], database=os.environ['SNOWFLAKE_DATABASE'],
    schema=os.environ['SNOWFLAKE_SCHEMA'],
)
cur = conn.cursor()
try:
    cur.execute("""
        SELECT product_id, product_name
        FROM basket_craft.raw.products
        ORDER BY product_name ASC
    """)
    rows = cur.fetchall()
finally:
    cur.close()
conn.close()
df = pd.DataFrame(rows, columns=["product_id", "product_name"])
print(df)
print(f"\nProducts: {len(df)}")
```

Run: `python _test_products_lookup.py`

Expected output (names may vary):
```
   product_id              product_name
0           2  Forever Bloom Gift Set
1           3  Mini Basket
2           1  The Original Gift Basket
3           4  ...

Products: 4
```

- [ ] **Step 2: Delete the test script**

```powershell
Remove-Item _test_products_lookup.py
```

- [ ] **Step 3: Add `get_products()` to `app.py`**

Insert this function after `get_product_revenue()` (after its `return df` line) and before the `try:` block that renders KPI cards:

```python
@st.cache_data(ttl=600)
def get_products():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT product_id, product_name
            FROM basket_craft.raw.products
            ORDER BY product_name ASC
        """)
        rows = cur.fetchall()
    finally:
        cur.close()
    return pd.DataFrame(rows, columns=["product_id", "product_name"])
```

- [ ] **Step 4: Verify syntax**

```powershell
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```powershell
git add app.py
git commit -m "feat: add get_products() cached query"
```

---

### Task 2: Add `get_bundle_pairs()` data function

**Files:**
- Modify: `app.py` (insert after `get_products()`)

- [ ] **Step 1: Write and run a standalone verification script**

Create `_test_bundle_pairs.py` in the project root to confirm the self-join and parameterization work:

```python
# _test_bundle_pairs.py  (delete after verifying)
import snowflake.connector, os, pandas as pd
from dotenv import load_dotenv
load_dotenv(override=True)
conn = snowflake.connector.connect(
    account=os.environ['SNOWFLAKE_ACCOUNT'], user=os.environ['SNOWFLAKE_USER'],
    password=os.environ['SNOWFLAKE_PASSWORD'], role=os.environ['SNOWFLAKE_ROLE'],
    warehouse=os.environ['SNOWFLAKE_WAREHOUSE'], database=os.environ['SNOWFLAKE_DATABASE'],
    schema=os.environ['SNOWFLAKE_SCHEMA'],
)
cur = conn.cursor()
try:
    cur.execute("""
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
    """, (1,))
    rows = cur.fetchall()
finally:
    cur.close()
conn.close()
df = pd.DataFrame(rows, columns=["month", "co_product", "order_count"])
df["month_date"] = pd.to_datetime(df["month"] + "-01").dt.date
print(df.head(10))
print(f"\nRows: {len(df)}, Co-products: {df['co_product'].nunique()}, Months: {df['month'].nunique()}")
```

Run: `python _test_bundle_pairs.py`

Expected output (values will vary, product_id=1 has 3 co-products):
```
      month          co_product  order_count  month_date
0   2023-03  Forever Bloom ...           42  2023-03-01
...
Rows: ~111, Co-products: 3, Months: 37
```

- [ ] **Step 2: Delete the test script**

```powershell
Remove-Item _test_bundle_pairs.py
```

- [ ] **Step 3: Add `get_bundle_pairs()` to `app.py`**

Insert this function after `get_products()` (after its `return pd.DataFrame(...)` line) and before the `try:` block that renders KPI cards:

```python
@st.cache_data(ttl=600)
def get_bundle_pairs(product_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
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
        """, (product_id,))
        rows = cur.fetchall()
    finally:
        cur.close()
    df = pd.DataFrame(rows, columns=["month", "co_product", "order_count"])
    df["month_date"] = pd.to_datetime(df["month"] + "-01").dt.date
    return df
```

- [ ] **Step 4: Verify syntax**

```powershell
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```powershell
git add app.py
git commit -m "feat: add get_bundle_pairs() cached query"
```

---

### Task 3: Add bundle finder UI section

**Files:**
- Modify: `app.py` (append after the final `except Exception as e: st.error(f"Failed to load product chart: {e}")` line)

- [ ] **Step 1: Append the bundle finder section to the end of `app.py`**

After the last line of the file, add:

```python
st.divider()
st.subheader("Bundle Finder")

try:
    products_df = get_products()
    product_names = products_df["product_name"].tolist()
    selected_name = st.selectbox("Select a product", options=product_names)
    selected_id = int(products_df.loc[products_df["product_name"] == selected_name, "product_id"].iloc[0])

    start_date = st.session_state.get("trend_start")
    end_date   = st.session_state.get("trend_end")

    if start_date is None or end_date is None:
        st.info("Set a date range above to see bundle data.")
    else:
        pairs_df = get_bundle_pairs(selected_id)
        filtered = pairs_df[
            (pairs_df["month_date"] >= start_date) &
            (pairs_df["month_date"] <= end_date)
        ]
        by_product = (
            filtered
            .groupby("co_product")["order_count"]
            .sum()
            .reset_index()
            .sort_values("order_count", ascending=False)
        )
        by_product.columns = ["Product", "Orders Together"]

        if by_product.empty:
            st.info("No bundle data in the selected date range.")
        else:
            st.dataframe(by_product, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"Failed to load bundle finder: {e}")
```

- [ ] **Step 2: Verify syntax**

```powershell
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```powershell
git add app.py
git commit -m "feat: add bundle finder section with product selectbox and co-occurrence table"
```

---

### Task 4: Final check, restart, and push

- [ ] **Step 1: Review final `app.py` structure**

Confirm the file reads top-to-bottom as:
1. Imports (streamlit, snowflake.connector, dotenv, os, pandas, altair)
2. `load_dotenv()`
3. `st.title("BasketCraft Dashboard")`
4. `get_connection()` — `@st.cache_resource`
5. `get_kpi_metrics()` — `@st.cache_data(ttl=600)`
6. `get_revenue_trend()` — `@st.cache_data(ttl=600)`
7. `get_product_revenue()` — `@st.cache_data(ttl=600)`
8. `get_products()` — `@st.cache_data(ttl=600)`
9. `get_bundle_pairs(product_id)` — `@st.cache_data(ttl=600)`
10. KPI `try/except` — four `st.metric` cards
11. `st.divider()` + `st.subheader("Monthly Revenue")` + trend `try/except`
12. `st.divider()` + `st.subheader("Top Products by Revenue")` + product `try/except`
13. `st.divider()` + `st.subheader("Bundle Finder")` + bundle `try/except`

- [ ] **Step 2: Hard-restart Streamlit to clear cache**

```powershell
Stop-Process -Name streamlit -Force -ErrorAction SilentlyContinue
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*streamlit*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process -FilePath "streamlit" -ArgumentList "run", "app.py" -NoNewWindow -WorkingDirectory (Get-Location)
Start-Sleep -Seconds 5
netstat -an | Select-String "8501"
```

Expected: one or more lines showing `0.0.0.0:8501` in `LISTENING` state.

- [ ] **Step 3: Smoke test**

Open `http://localhost:8501` and verify:
- [ ] KPI cards load
- [ ] Trend chart loads with "Last 12M" selected by default
- [ ] Product bar chart appears below the trend chart
- [ ] Bundle Finder section appears below the product chart
- [ ] Selectbox shows all 4 product names
- [ ] Selecting a product shows a table with "Product" and "Orders Together" columns
- [ ] Rows are sorted by "Orders Together" descending
- [ ] Switching date range (e.g. "Last 6M" vs "All Time") updates the bundle table counts
- [ ] Selecting each of the 4 products returns a different set of co-purchase rows

- [ ] **Step 4: Push to GitHub**

```powershell
git push origin main
```
