
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="RetailPulse | Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

BG = "#07111F"
PANEL = "#0D1B2A"
CYAN = "#00D9FF"
PINK = "#FF3D81"
YELLOW = "#FFC857"
GREEN = "#00E5A8"
MUTED = "#8EA5BC"

# --------------------------------------------------
# CUSTOM DARK THEME
# --------------------------------------------------
st.markdown(
    f"""
    <style>
    .stApp {{
        background: {BG};
        color: #F1F5F9;
    }}
    [data-testid="stSidebar"] {{
        background: #0A1625;
        border-right: 1px solid #1B3045;
    }}
    h1, h2, h3 {{
        color: #F1F5F9 !important;
    }}
    .dashboard-subtitle {{
        color: {MUTED};
        margin-top: -12px;
        margin-bottom: 24px;
    }}
    .kpi-card {{
        background: linear-gradient(135deg, #10243A, #0B1929);
        border: 1px solid #1D354C;
        border-radius: 13px;
        padding: 17px 19px;
        min-height: 115px;
    }}
    .kpi-label {{
        color: {MUTED};
        font-size: 13px;
        margin-bottom: 9px;
    }}
    .kpi-value {{
        color: #F8FAFC;
        font-size: 27px;
        font-weight: 750;
    }}
    .kpi-note {{
        color: {GREEN};
        font-size: 11px;
        margin-top: 7px;
    }}
    div[data-testid="stPlotlyChart"] {{
        background: transparent;
    }}
    div[data-testid="stMetric"] {{
        background: {PANEL};
        border: 1px solid #1D354C;
        padding: 12px;
        border-radius: 10px;
    }}
    hr {{
        border-color: #203348;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# LOAD DATA
# Supports the original Excel file or a CSV version
# --------------------------------------------------
@st.cache_data(show_spinner="Loading retail transactions...")
def load_data(file_path, modified_time):
    path = Path(file_path)

    if path.suffix.lower() == ".xlsx":
        data = pd.read_excel(path, engine="openpyxl")
    else:
        data = pd.read_csv(path, low_memory=False)

    data.columns = data.columns.str.strip()

    required = {
        "InvoiceNo", "StockCode", "Description",
        "Quantity", "InvoiceDate", "UnitPrice",
        "CustomerID", "Country",
    }

    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data["InvoiceDate"] = pd.to_datetime(
        data["InvoiceDate"], errors="coerce"
    )
    data["Quantity"] = pd.to_numeric(
        data["Quantity"], errors="coerce"
    )
    data["UnitPrice"] = pd.to_numeric(
        data["UnitPrice"], errors="coerce"
    )
    data["CustomerID"] = data["CustomerID"].astype("string").str.strip()
    data["Country"] = data["Country"].astype("string").str.strip()
    data["Description"] = data["Description"].fillna("Unknown product")

    data = data.dropna(
        subset=["InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice", "Country"]
    )

    data["InvoiceNo"] = data["InvoiceNo"].astype(str).str.strip()
    data["IsCancellation"] = data["InvoiceNo"].str.upper().str.startswith("C")
    data["Revenue"] = data["Quantity"] * data["UnitPrice"]

    data["Month"] = data["InvoiceDate"].dt.to_period("M").astype(str)
    data["Hour"] = data["InvoiceDate"].dt.hour
    data["Weekday"] = data["InvoiceDate"].dt.day_name()
    data["Date"] = data["InvoiceDate"].dt.date

    return data


# --------------------------------------------------
# FIND DATA FILE
# --------------------------------------------------
possible_files = [
    DATA_DIR / "Online Retail.xlsx",
    DATA_DIR / "online_retail.xlsx",
    DATA_DIR / "Online Retail.csv",
    DATA_DIR / "online_retail.csv",
]

data_path = next((p for p in possible_files if p.exists()), None)

if data_path is None:
    st.title("📊 RetailPulse Analytics")
    st.warning(
        "Dataset not found. Download Online Retail.xlsx from the UCI "
        "Machine Learning Repository and place it inside the data folder."
    )
    st.code(
        "online-retail-dashboard/\n"
        "├── dashboard.py\n"
        "├── requirements.txt\n"
        "└── data/\n"
        "    └── Online Retail.xlsx"
    )
    st.stop()

try:
    raw = load_data(str(data_path), data_path.stat().st_mtime)
except Exception as exc:
    st.error(f"Could not load the dataset: {exc}")
    st.stop()

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.title("⚡ RETAILPULSE")
st.sidebar.caption("BUSINESS INTELLIGENCE PLATFORM")
st.sidebar.divider()

st.sidebar.subheader("Dashboard Filters")

min_date = raw["InvoiceDate"].min().date()
max_date = raw["InvoiceDate"].max().date()

date_range = st.sidebar.date_input(
    "Invoice date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

countries = sorted(raw["Country"].dropna().unique().tolist())
selected_countries = st.sidebar.multiselect(
    "Countries",
    countries,
    default=["United Kingdom"] if "United Kingdom" in countries else countries[:5],
)

top_n = st.sidebar.slider("Top products to display", 5, 20, 10)

# --------------------------------------------------
# FILTERED DATA
# --------------------------------------------------
date_mask = (
    (raw["InvoiceDate"].dt.date >= start_date)
    & (raw["InvoiceDate"].dt.date <= end_date)
)

filtered = raw.loc[
    date_mask & raw["Country"].isin(selected_countries)
].copy()

# Cancelled invoices and invalid sales are excluded from sales KPIs.
# Negative quantity / price records should be examined separately.
sales = filtered.loc[
    (~filtered["IsCancellation"])
    & (filtered["Quantity"] > 0)
    & (filtered["UnitPrice"] > 0)
].copy()

cancelled = filtered.loc[filtered["IsCancellation"]].copy()

if sales.empty:
    st.title("📊 RetailPulse Analytics")
    st.warning("No valid sales match these filters. Select a wider date range or more countries.")
    st.stop()

sales["Revenue"] = sales["Quantity"] * sales["UnitPrice"]

# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("📊 RetailPulse")
st.markdown(
    '<p class="dashboard-subtitle">'
    'ONLINE RETAIL PERFORMANCE & CUSTOMER INTELLIGENCE'
    '</p>',
    unsafe_allow_html=True,
)

st.caption(
    f"Reporting period: {start_date:%d %b %Y} — {end_date:%d %b %Y}"
    f"  |  Currency: GBP (£)"
)

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
total_revenue = sales["Revenue"].sum()
total_orders = sales["InvoiceNo"].nunique()
total_customers = sales["CustomerID"].nunique()
total_products = sales["StockCode"].nunique()
average_order = total_revenue / total_orders if total_orders else 0
units_sold = sales["Quantity"].sum()

def kpi_card(label, value, note, color):
    st.markdown(
        f"""
        <div class="kpi-card" style="border-top: 3px solid {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    kpi_card("TOTAL REVENUE", f"£{total_revenue:,.0f}", "Valid sales value", CYAN)
with k2:
    kpi_card("ORDERS", f"{total_orders:,}", "Unique sales invoices", PINK)
with k3:
    kpi_card("CUSTOMERS", f"{total_customers:,}", "Identified customers", GREEN)
with k4:
    kpi_card("PRODUCTS", f"{total_products:,}", "Unique stock codes", YELLOW)
with k5:
    kpi_card("AVG. ORDER VALUE", f"£{average_order:,.2f}", "Revenue ÷ orders", CYAN)

st.write("")

# --------------------------------------------------
# CHART THEME
# --------------------------------------------------
def style_chart(fig, height=330):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D7E3F0", family="Arial"),
        margin=dict(l=15, r=15, t=45, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        xaxis=dict(
            gridcolor="#1D3044",
            zerolinecolor="#1D3044",
            linecolor="#243A50",
        ),
        yaxis=dict(
            gridcolor="#1D3044",
            zerolinecolor="#1D3044",
            linecolor="#243A50",
        ),
    )
    return fig

# --------------------------------------------------
# ROW 1: REVENUE TREND + SALES BY HOUR
# --------------------------------------------------
left, right = st.columns([1.6, 1])

with left:
    st.subheader("Revenue Performance")
    monthly = (
        sales.groupby("Month", as_index=False)
        .agg(Revenue=("Revenue", "sum"))
        .sort_values("Month")
    )

    fig = px.area(
        monthly,
        x="Month",
        y="Revenue",
        markers=True,
        color_discrete_sequence=[CYAN],
        title="Monthly revenue (£)",
    )
    fig.update_traces(
        line=dict(width=3),
        fillcolor="rgba(0,217,255,0.12)",
        hovertemplate="%{x}<br>Revenue: £%{y:,.2f}<extra></extra>",
    )
    fig.update_yaxes(title="Revenue (£)", tickprefix="£", tickformat=",.0f")
    st.plotly_chart(style_chart(fig), use_container_width=True)

with right:
    st.subheader("Purchase Activity")
    hourly = (
        sales.groupby("Hour", as_index=False)
        .agg(Orders=("InvoiceNo", "nunique"))
    )

    fig = px.bar(
        hourly,
        x="Hour",
        y="Orders",
        color="Orders",
        color_continuous_scale=["#123B56", CYAN],
        title="Orders by hour of day",
    )
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(dtick=2, title="Hour (24-hour clock)")
    fig.update_yaxes(title="Unique orders")
    st.plotly_chart(style_chart(fig), use_container_width=True)

# --------------------------------------------------
# ROW 2: TOP PRODUCTS + COUNTRY SALES
# --------------------------------------------------
left, right = st.columns([1.15, 1])

with left:
    st.subheader("Top-Selling Products")
    products = (
        sales.groupby("Description", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Units=("Quantity", "sum"),
        )
        .sort_values("Revenue", ascending=False)
        .head(top_n)
        .sort_values("Revenue")
    )

    fig = px.bar(
        products,
        x="Revenue",
        y="Description",
        orientation="h",
        color="Revenue",
        color_continuous_scale=["#164E63", CYAN],
        title=f"Top {top_n} products by revenue",
    )
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(title="Revenue (£)", tickprefix="£")
    fig.update_yaxes(title="")
    st.plotly_chart(style_chart(fig, 400), use_container_width=True)

with right:
    st.subheader("Geographic Performance")
    country_sales = (
        sales.groupby("Country", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Orders=("InvoiceNo", "nunique"),
        )
        .sort_values("Revenue", ascending=False)
    )

    fig = px.choropleth(
        country_sales,
        locations="Country",
        locationmode="country names",
        color="Revenue",
        hover_name="Country",
        hover_data={"Revenue": ":,.2f", "Orders": ":,"},
        color_continuous_scale=["#153C55", CYAN, PINK],
        title="Revenue by country",
    )
    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#30485D",
        landcolor="#102338",
        showland=True,
    )
    fig.update_layout(
        coloraxis_colorbar=dict(title="Revenue (£)"),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(style_chart(fig, 400), use_container_width=True)

# --------------------------------------------------
# ROW 3: ORDER MIX + WEEKDAY ACTIVITY
# --------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Revenue Concentration")
    country_mix = (
        country_sales.sort_values("Revenue", ascending=False)
        .head(8)
    )

    fig = px.pie(
        country_mix,
        names="Country",
        values="Revenue",
        hole=0.68,
        title="Top 8 countries by revenue",
        color_discrete_sequence=[
            CYAN, PINK, YELLOW, GREEN,
            "#8B7CFF", "#FF914D", "#4DD0E1", "#A3E635",
        ],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate="%{label}<br>£%{value:,.2f}<extra></extra>",
    )
    fig.update_layout(showlegend=True)
    st.plotly_chart(style_chart(fig), use_container_width=True)

with right:
    st.subheader("Weekly Buying Pattern")
    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    weekday_data = (
        sales.groupby("Weekday", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Orders=("InvoiceNo", "nunique"),
        )
    )
    weekday_data["Weekday"] = pd.Categorical(
        weekday_data["Weekday"],
        categories=weekday_order,
        ordered=True,
    )
    weekday_data = weekday_data.sort_values("Weekday")

    fig = px.bar(
        weekday_data,
        x="Weekday",
        y="Revenue",
        color="Revenue",
        color_continuous_scale=["#15445B", PINK],
        title="Revenue by day of week",
    )
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Revenue (£)", tickprefix="£")
    st.plotly_chart(style_chart(fig), use_container_width=True)

# --------------------------------------------------
# ROW 4: CUSTOMER SEGMENTATION + QUANTITY DISTRIBUTION
# --------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Customer Segmentation (RFM)")
    identified = sales.dropna(subset=["CustomerID"]).copy()

    if not identified.empty:
        reference_date = identified["InvoiceDate"].max() + pd.Timedelta(days=1)

        rfm = identified.groupby("CustomerID").agg(
            Recency=("InvoiceDate", lambda x: (reference_date - x.max()).days),
            Frequency=("InvoiceNo", "nunique"),
            Monetary=("Revenue", "sum"),
        )

        rfm = rfm[
            (rfm["Monetary"] > 0)
            & (rfm["Frequency"] > 0)
        ].copy()

        if len(rfm) >= 4:
            # Rank-based scoring is robust when many customers
            # have the same number of orders.
            rfm["R_score"] = pd.qcut(
                rfm["Recency"].rank(method="first"),
                4,
                labels=[4, 3, 2, 1],
            ).astype(int)

            rfm["F_score"] = pd.qcut(
                rfm["Frequency"].rank(method="first"),
                4,
                labels=[1, 2, 3, 4],
            ).astype(int)

            rfm["M_score"] = pd.qcut(
                rfm["Monetary"].rank(method="first"),
                4,
                labels=[1, 2, 3, 4],
            ).astype(int)

            rfm["Segment"] = np.select(
                [
                    (rfm["R_score"] >= 3) & (rfm["F_score"] >= 3),
                    (rfm["F_score"] >= 3) & (rfm["M_score"] >= 3),
                    (rfm["R_score"] <= 2) & (rfm["F_score"] <= 2),
                ],
                [
                    "Loyal / Active",
                    "High Value",
                    "At Risk",
                ],
                default="Regular",
            )

            segment_data = (
                rfm.groupby("Segment", as_index=False, observed=True)
                .agg(Customers=("Monetary", "size"))
                .sort_values("Customers", ascending=False)
            )

            fig = px.bar(
                segment_data,
                x="Segment",
                y="Customers",
                color="Segment",
                color_discrete_map={
                    "Loyal / Active": GREEN,
                    "High Value": CYAN,
                    "At Risk": PINK,
                    "Regular": YELLOW,
                },
                title="Customers by RFM segment",
            )
            fig.update_layout(showlegend=False)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Customers")
            st.plotly_chart(style_chart(fig), use_container_width=True)
        else:
            st.info("Not enough identified customers for RFM segmentation.")
    else:
        st.info("Customer IDs are unavailable for this selection.")

with right:
    st.subheader("Order Size Distribution")
    order_sizes = (
        sales.groupby("InvoiceNo", as_index=False)
        .agg(Units=("Quantity", "sum"))
    )

    fig = px.histogram(
        order_sizes.loc[order_sizes["Units"] <= order_sizes["Units"].quantile(0.99)],
        x="Units",
        nbins=35,
        color_discrete_sequence=[PINK],
        title="Units per order (up to 99th percentile)",
    )
    fig.update_xaxes(title="Units per invoice")
    fig.update_yaxes(title="Number of orders")
    st.plotly_chart(style_chart(fig), use_container_width=True)

# --------------------------------------------------
# BUSINESS INSIGHTS
# --------------------------------------------------
st.divider()
st.subheader("🔎 Key Business Insights")

best_month = monthly.loc[monthly["Revenue"].idxmax()]
best_country = country_sales.iloc[0]
best_product = products.sort_values("Revenue", ascending=False).iloc[0]

i1, i2, i3 = st.columns(3)

with i1:
    st.markdown("**🏆 Best Revenue Month**")
    st.write(f"{best_month['Month']}")
    st.write(f"Revenue: £{best_month['Revenue']:,.2f}")

with i2:
    st.markdown("**🌍 Leading Country**")
    st.write(str(best_country["Country"]))
    st.write(f"Revenue: £{best_country['Revenue']:,.2f}")

with i3:
    st.markdown("**🛍️ Leading Product**")
    st.write(str(best_product["Description"])[:80])
    st.write(f"Revenue: £{best_product['Revenue']:,.2f}")

# --------------------------------------------------
# DATA QUALITY & TRANSACTION DETAILS
# --------------------------------------------------
with st.expander("Data quality and cancellations"):
    q1, q2, q3 = st.columns(3)
    q1.metric("Rows in filtered source", f"{len(filtered):,}")
    q2.metric("Cancellation invoice rows", f"{len(cancelled):,}")
    q3.metric(
        "Rows with missing customer IDs",
        f"{filtered['CustomerID'].isna().sum():,}",
    )

    st.caption(
        "Sales KPIs exclude cancellation invoices, non-positive quantities, "
        "and non-positive unit prices. Cancellation rows are shown separately. "
        "This is a sales analysis, not a complete accounting reconciliation."
    )

with st.expander("Explore transaction records"):
    st.caption("Showing the first 500 matching valid sales records.")
    display_columns = [
        "InvoiceNo", "InvoiceDate", "Description",
        "Quantity", "UnitPrice", "Revenue", "CustomerID", "Country",
    ]
    st.dataframe(
        sales[display_columns].head(500),
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = sales[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download filtered sales as CSV",
        data=csv_bytes,
        file_name="filtered_retail_sales.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "RetailPulse Analytics | Built with Python, Pandas, Streamlit and Plotly"
)
