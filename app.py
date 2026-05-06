import streamlit as st
import snowflake.connector
from dotenv import load_dotenv
import os
import pandas as pd
import altair as alt

load_dotenv()

st.title("BasketCraft Dashboard")


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


@st.cache_data(ttl=600)
def get_kpi_metrics():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            WITH monthly AS (
                SELECT
                    DATE_TRUNC('month', TO_TIMESTAMP(created_at / 1000000000)) AS mo,
                    COUNT(DISTINCT order_id)  AS orders,
                    SUM(price_usd)            AS revenue,
                    SUM(items_purchased)      AS items
                FROM basket_craft.raw.orders
                GROUP BY 1
            ),
            ranked AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY mo DESC) AS rn
                FROM monthly
            )
            SELECT
                MAX(CASE WHEN rn = 1 THEN TO_CHAR(mo, 'Mon YYYY') END) AS cur_label,
                MAX(CASE WHEN rn = 1 THEN revenue END)::FLOAT           AS cur_revenue,
                MAX(CASE WHEN rn = 2 THEN revenue END)::FLOAT           AS prev_revenue,
                MAX(CASE WHEN rn = 1 THEN orders  END)::INT             AS cur_orders,
                MAX(CASE WHEN rn = 2 THEN orders  END)::INT             AS prev_orders,
                MAX(CASE WHEN rn = 1 THEN items   END)::INT             AS cur_items,
                MAX(CASE WHEN rn = 2 THEN items   END)::INT             AS prev_items
            FROM ranked
            WHERE rn <= 2
        """)
        row = cur.fetchone()
        cur_label, cur_rev, prev_rev, cur_ord, prev_ord, cur_items, prev_items = row

        cur_aov  = cur_rev  / cur_ord  if cur_ord  else 0
        prev_aov = prev_rev / prev_ord if prev_ord else 0

        def pct_delta(cur, prev):
            return (cur - prev) / prev * 100 if prev else 0

        return {
            "label":       cur_label,
            "revenue":     cur_rev,
            "orders":      cur_ord,
            "aov":         cur_aov,
            "items":       cur_items,
            "d_revenue":   pct_delta(cur_rev,   prev_rev),
            "d_orders":    pct_delta(cur_ord,   prev_ord),
            "d_aov":       pct_delta(cur_aov,   prev_aov),
            "d_items":     pct_delta(cur_items, prev_items),
        }
    finally:
        cur.close()


@st.cache_data(ttl=600)
def get_revenue_trend():
    conn = get_connection()
    cur = conn.cursor()
    try:
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
    finally:
        cur.close()


try:
    m = get_kpi_metrics()
    st.subheader(f"Key Metrics — {m['label']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue",      f"${m['revenue']:,.0f}",  f"{m['d_revenue']:+.1f}% vs prior month")
    c2.metric("Total Orders",       f"{m['orders']:,}",       f"{m['d_orders']:+.1f}% vs prior month")
    c3.metric("Avg Order Value",    f"${m['aov']:,.2f}",      f"{m['d_aov']:+.1f}% vs prior month")
    c4.metric("Total Items Sold",   f"{m['items']:,}",        f"{m['d_items']:+.1f}% vs prior month")
except Exception as e:
    st.error(f"Failed to load metrics: {e}")

st.divider()
st.subheader("Monthly Revenue")

try:
    trend_df = get_revenue_trend()
    if trend_df.empty:
        raise ValueError("Revenue trend query returned no rows")

    min_date = trend_df["month_date"].min()
    max_date = trend_df["month_date"].max()
    max_ts   = pd.Timestamp(max_date)
    last_6m_start  = (max_ts - pd.DateOffset(months=5)).date()
    last_12m_start = (max_ts - pd.DateOffset(months=11)).date()

    if "trend_preset" not in st.session_state:
        st.session_state.trend_preset = "Last 12M"
    if "trend_start" not in st.session_state:
        st.session_state.trend_start = last_12m_start
    if "trend_end" not in st.session_state:
        st.session_state.trend_end = max_date

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

    filtered = trend_df[
        (trend_df["month_date"] >= start_date) &
        (trend_df["month_date"] <= end_date)
    ].copy()
    filtered["month_dt"] = pd.to_datetime(filtered["month"] + "-01")

    if filtered.empty:
        st.info("No data in the selected date range.")
    else:
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

except Exception as e:
    st.error(f"Failed to load revenue trend: {e}")
