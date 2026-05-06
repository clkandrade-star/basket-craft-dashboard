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
