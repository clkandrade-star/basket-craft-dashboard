# BasketCraft Dashboard

**Live app:** https://clkandrade-star-basket-craft-dashboard-app-k2r35y.streamlit.app/

A Streamlit dashboard connected to a Snowflake data warehouse, built for the BasketCraft e-commerce dataset.

## Features

- **KPI Metrics** — Total revenue, orders, average order value, and items sold for the most recent month, each with a month-over-month delta
- **Monthly Revenue Trend** — Line chart with preset (Last 6M / Last 12M / All Time) and custom date range filtering
- **Top Products by Revenue** — Bar chart of revenue by product, filtered by the selected date range
- **Bundle Finder** — Pick any product and see which other products are most frequently purchased together, ranked by co-occurrence count and filtered by date range

## Tech Stack

- [Streamlit](https://streamlit.io/) — dashboard framework
- [Snowflake](https://www.snowflake.com/) — data warehouse
- [pandas](https://pandas.pydata.org/) — data manipulation
- [Altair](https://altair-viz.github.io/) — charts

## Local Setup

1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root:
   ```
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_ROLE=your_role
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```
