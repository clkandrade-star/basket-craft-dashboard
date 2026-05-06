# Top Products Bar Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a vertical Altair bar chart below the trend chart showing total revenue by product, filtered by the existing `trend_start`/`trend_end` session state.

**Architecture:** One new cached query function (`get_product_revenue`) returns all month×product rows. The chart section reads the existing session state date keys set by the trend filter, aggregates in Python, and renders with Altair — no new UI widgets. Follows every pattern already established in `app.py`.

**Tech Stack:** Streamlit, Snowflake connector, pandas, Altair

---

### Task 1: Add `get_product_revenue()` data function

**Files:**
- Modify: `app.py` (insert after `get_revenue_trend()`, before line 101)

- [ ] **Step 1: Write and run a standalone verification script**

Create `_test_products.py` in the project root to confirm the query and join work before touching `app.py`:

```python
# _test_products.py  (delete after verifying)
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
            TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(o.created_at / 1000000000)), 'YYYY-MM') AS month,
            p.product_name,
            SUM(o.price_usd)::FLOAT AS revenue
        FROM basket_craft.raw.orders o
        JOIN basket_craft.raw.products p ON o.primary_product_id = p.product_id
        GROUP BY 1, 2
        ORDER BY 1 ASC
    """)
    rows = cur.fetchall()
finally:
    cur.close()
conn.close()

df = pd.DataFrame(rows, columns=["month", "product_name", "revenue"])
df["month_date"] = pd.to_datetime(df["month"] + "-01").dt.date
print(df.head(8))
print(f"\nRows: {len(df)}, Products: {df['product_name'].nunique()}, Months: {df['month'].nunique()}")
```

Run: `python _test_products.py`

Expected output (values will vary):
```
      month              product_name     revenue  month_date
0   2023-03  The Original Gift Basket  79482.95  2023-03-01
...
Rows: 148, Products: 4, Months: 37
```

- [ ] **Step 2: Delete the test script**

```powershell
Remove-Item _test_products.py
```

- [ ] **Step 3: Add `get_product_revenue()` to `app.py`**

Insert this function after `get_revenue_trend()` (after its closing `finally` block) and before the `try:` block that renders KPI cards:

```python
@st.cache_data(ttl=600)
def get_product_revenue():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(o.created_at / 1000000000)), 'YYYY-MM') AS month,
                p.product_name,
                SUM(o.price_usd)::FLOAT AS revenue
            FROM basket_craft.raw.orders o
            JOIN basket_craft.raw.products p ON o.primary_product_id = p.product_id
            GROUP BY 1, 2
            ORDER BY 1 ASC
        """)
        rows = cur.fetchall()
    finally:
        cur.close()
    df = pd.DataFrame(rows, columns=["month", "product_name", "revenue"])
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
git commit -m "feat: add get_product_revenue() cached query"
```

---

### Task 2: Add product chart section

**Files:**
- Modify: `app.py` (append after the trend `except` block — currently the last line of the file)

- [ ] **Step 1: Append the product chart section to the end of `app.py`**

After the final `except Exception as e: st.error(f"Failed to load revenue trend: {e}")` line, add:

```python
st.divider()
st.subheader("Top Products by Revenue")

try:
    prod_df = get_product_revenue()

    start_date = st.session_state.get("trend_start")
    end_date   = st.session_state.get("trend_end")

    if start_date is None or end_date is None:
        st.info("Set a date range above to see product revenue.")
    else:
        filtered_prod = prod_df[
            (prod_df["month_date"] >= start_date) &
            (prod_df["month_date"] <= end_date)
        ]
        by_product = (
            filtered_prod
            .groupby("product_name")["revenue"]
            .sum()
            .reset_index()
            .sort_values("revenue", ascending=False)
        )

        if by_product.empty:
            st.info("No data in the selected date range.")
        else:
            chart = (
                alt.Chart(by_product)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "product_name:N",
                        title="Product",
                        sort=alt.EncodingSortField(field="revenue", order="descending"),
                    ),
                    y=alt.Y(
                        "revenue:Q",
                        title="Revenue ($)",
                        axis=alt.Axis(format="$,.0f"),
                    ),
                    tooltip=[
                        alt.Tooltip("product_name:N", title="Product"),
                        alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
                    ],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)

except Exception as e:
    st.error(f"Failed to load product chart: {e}")
```

- [ ] **Step 2: Verify syntax**

```powershell
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```powershell
git add app.py
git commit -m "feat: add top products bar chart with date filter"
```

---

### Task 3: Final check, restart, and push

- [ ] **Step 1: Review final `app.py` structure**

Confirm the file reads top-to-bottom as:
1. Imports (streamlit, snowflake.connector, dotenv, os, pandas, altair)
2. `load_dotenv()`
3. `st.title("BasketCraft Dashboard")`
4. `get_connection()` — `@st.cache_resource`
5. `get_kpi_metrics()` — `@st.cache_data(ttl=600)`
6. `get_revenue_trend()` — `@st.cache_data(ttl=600)`
7. `get_product_revenue()` — `@st.cache_data(ttl=600)`
8. KPI `try/except` — four `st.metric` cards
9. `st.divider()` + `st.subheader("Monthly Revenue")` + trend `try/except`
10. `st.divider()` + `st.subheader("Top Products by Revenue")` + product `try/except`

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
- [ ] Bars are sorted by revenue descending (The Original Gift Basket tallest)
- [ ] Hovering a bar shows product name + revenue tooltip
- [ ] Switching to "Last 6M" updates both the trend line and the bar chart heights
- [ ] Switching to "All Time" updates both charts

- [ ] **Step 4: Push to GitHub**

```powershell
git push origin main
```
