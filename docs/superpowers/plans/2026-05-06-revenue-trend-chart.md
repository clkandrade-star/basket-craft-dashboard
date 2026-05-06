# Revenue Trend Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a monthly revenue trend line chart with preset + custom date range filtering to `app.py`.

**Architecture:** A single new cached query function (`get_revenue_trend`) returns all monthly revenue as a pandas DataFrame. Filter state is held in `st.session_state` so preset buttons can sync the date pickers without a re-query. The DataFrame is sliced in Python and rendered with Altair.

**Tech Stack:** Streamlit, Snowflake connector, pandas, Altair (pre-installed with Streamlit)

---

### Task 1: Add `get_revenue_trend()` data function

**Files:**
- Modify: `app.py` (after `get_kpi_metrics`, before the `try` block at line 75)

- [ ] **Step 1: Add imports**

At the top of `app.py`, add `pandas` and `altair` to the existing imports:

```python
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv
import os
import pandas as pd
import altair as alt
```

- [ ] **Step 2: Add `get_revenue_trend()` after `get_kpi_metrics()`**

Insert this function between `get_kpi_metrics` and the `try` block:

```python
@st.cache_data(ttl=600)
def get_revenue_trend():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(created_at / 1000000000)), 'YYYY-MM') AS month,
            SUM(price_usd)::FLOAT AS revenue
        FROM basket_craft.raw.orders
        GROUP BY 1
        ORDER BY 1 ASC
    """)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["month", "revenue"])
    df["month_date"] = pd.to_datetime(df["month"] + "-01").dt.date
    return df
```

- [ ] **Step 3: Verify the function returns data**

Run this standalone test script to confirm the query works before touching the UI:

```python
# _test_trend.py  (delete after verifying)
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
cur.execute("""
    SELECT
        TO_CHAR(DATE_TRUNC('month', TO_TIMESTAMP(created_at / 1000000000)), 'YYYY-MM') AS month,
        SUM(price_usd)::FLOAT AS revenue
    FROM basket_craft.raw.orders
    GROUP BY 1 ORDER BY 1 ASC
""")
df = pd.DataFrame(cur.fetchall(), columns=["month", "revenue"])
df["month_date"] = pd.to_datetime(df["month"] + "-01").dt.date
print(df.head())
print(f"\nTotal months: {len(df)}, range: {df['month'].min()} to {df['month'].max()}")
conn.close()
```

Run: `python _test_trend.py`

Expected output (values will vary):
```
    month    revenue  month_date
0  2023-03  79482.95  2023-03-01
...
Total months: 37, range: 2023-03 to 2026-03
```

- [ ] **Step 4: Delete the test script**

```bash
del _test_trend.py
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add get_revenue_trend() cached query"
```

---

### Task 2: Add session state initialisation and preset date logic

**Files:**
- Modify: `app.py` (add section after KPI `try/except` block, before chart rendering)

- [ ] **Step 1: Add the trend section with session state init**

After the closing `except` of the KPI block (line 84), append:

```python
st.divider()
st.subheader("Monthly Revenue")

try:
    trend_df = get_revenue_trend()

    min_date = trend_df["month_date"].min()
    max_date = trend_df["month_date"].max()
    max_ts   = pd.Timestamp(max_date)
    last_6m_start  = (max_ts - pd.DateOffset(months=5)).date()
    last_12m_start = (max_ts - pd.DateOffset(months=11)).date()

    def _apply_preset():
        p = st.session_state.trend_preset
        if p == "Last 6M":
            st.session_state.trend_start = last_6m_start
            st.session_state.trend_end   = max_date
        elif p == "Last 12M":
            st.session_state.trend_start = last_12m_start
            st.session_state.trend_end   = max_date
        else:
            st.session_state.trend_start = min_date
            st.session_state.trend_end   = max_date

    if "trend_preset" not in st.session_state:
        st.session_state.trend_preset = "Last 12M"
    if "trend_start" not in st.session_state:
        st.session_state.trend_start = last_12m_start
    if "trend_end" not in st.session_state:
        st.session_state.trend_end = max_date

except Exception as e:
    st.error(f"Failed to load revenue trend: {e}")
```

- [ ] **Step 2: Verify app still loads without error**

Reload `http://localhost:8501`. The KPI cards and the "Monthly Revenue" subheader should appear; no error messages.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add session state and preset date logic for trend filter"
```

---

### Task 3: Add filter row UI

**Files:**
- Modify: `app.py` (inside the `try` block added in Task 2, after session state init)

- [ ] **Step 1: Add the three-column filter row**

Inside the `try` block from Task 2, after the session state initialisation block, add:

```python
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    f_col1.radio(
        "Date range",
        ["Last 6M", "Last 12M", "All Time"],
        key="trend_preset",
        on_change=_apply_preset,
        horizontal=True,
    )
    start_date = f_col2.date_input(
        "Start", key="trend_start", min_value=min_date, max_value=max_date
    )
    end_date = f_col3.date_input(
        "End", key="trend_end", min_value=min_date, max_value=max_date
    )
```

- [ ] **Step 2: Verify filter row renders**

Reload the app. You should see a horizontal radio ("Last 6M / Last 12M / All Time") and two date pickers. Clicking a preset should update the date picker values. Editing a date picker directly should leave the radio unchanged.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add date range filter row for revenue trend"
```

---

### Task 4: Add Altair chart

**Files:**
- Modify: `app.py` (inside the `try` block, after the filter row)

- [ ] **Step 1: Add filtering and chart rendering**

After the filter row code from Task 3, add:

```python
    filtered = trend_df[
        (trend_df["month_date"] >= start_date) &
        (trend_df["month_date"] <= end_date)
    ].copy()
    filtered["month_dt"] = pd.to_datetime(filtered["month"] + "-01")

    chart = (
        alt.Chart(filtered)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "month_dt:T",
                title="Month",
                axis=alt.Axis(format="%b %Y", labelAngle=-45),
            ),
            y=alt.Y(
                "revenue:Q",
                title="Revenue ($)",
                axis=alt.Axis(format="$,.0f"),
            ),
            tooltip=[
                alt.Tooltip("month_dt:T", title="Month", format="%b %Y"),
                alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)
```

- [ ] **Step 2: Verify chart renders correctly**

Reload the app. Confirm:
- Chart appears below the filter row
- X axis shows month labels (e.g. "Mar 2023")
- Y axis shows dollar-formatted values
- Hovering a point shows a tooltip with month + revenue
- Changing the preset updates the chart range
- Editing the date pickers manually updates the chart

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Altair monthly revenue trend chart with date filter"
```

---

### Task 5: Final check and restart

- [ ] **Step 1: Review final `app.py` structure**

Confirm the file reads top-to-bottom as:
1. Imports (`streamlit`, `snowflake.connector`, `dotenv`, `os`, `pandas`, `altair`)
2. `load_dotenv()`
3. `st.title("BasketCraft Dashboard")`
4. `get_connection()` — `@st.cache_resource`
5. `get_kpi_metrics()` — `@st.cache_data(ttl=600)`
6. `get_revenue_trend()` — `@st.cache_data(ttl=600)`
7. KPI `try/except` block — four `st.metric` cards
8. `st.divider()` + `st.subheader("Monthly Revenue")`
9. Trend `try/except` block — session state, filter row, chart

- [ ] **Step 2: Hard-restart Streamlit to clear cache**

```bash
# Kill existing process, then:
streamlit run app.py
```

- [ ] **Step 3: Smoke test all interactions**

- [ ] KPI cards load with values and deltas
- [ ] "Last 12M" is selected by default; chart shows ~12 months
- [ ] Clicking "Last 6M" updates both pickers and shrinks the chart
- [ ] Clicking "All Time" expands the chart to the full date range
- [ ] Manually editing the start date picker filters the chart without changing the radio
- [ ] Hovering a data point shows the tooltip

- [ ] **Step 4: Final commit**

```bash
git add app.py
git commit -m "feat: revenue trend chart complete — line chart with preset/custom date filter"
```
