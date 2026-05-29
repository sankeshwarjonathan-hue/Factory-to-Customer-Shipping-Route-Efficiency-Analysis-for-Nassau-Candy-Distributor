import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Nassau Candy — Shipping Dashboard", layout="wide")

#Load & Prepare Data
@st.cache_data
def load_data():
    df = pd.read_csv('Nassau Candy Distributor.csv')
    df.columns = [col.strip() for col in df.columns]
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d-%m-%Y', errors='coerce')
    df['Ship Date']  = pd.to_datetime(df['Ship Date'],  format='%d-%m-%Y', errors='coerce')
    df['Lead Time']  = (df['Ship Date'] - df['Order Date']).dt.days
    df['Sales']        = pd.to_numeric(df['Sales'],        errors='coerce')
    df['Gross Profit'] = pd.to_numeric(df['Gross Profit'], errors='coerce')
    df['Cost']         = pd.to_numeric(df['Cost'],         errors='coerce')
    df.dropna(subset=['Lead Time', 'Order Date', 'Ship Date'], inplace=True)
    df['Lead Time'] = df['Lead Time'].astype(int)
    return df

df = load_data()

#Sidebar Filters 
st.sidebar.header("Filters")

all_regions = ["All"] + sorted(df['Region'].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Region", all_regions)

all_modes = ["All"] + sorted(df['Ship Mode'].dropna().unique().tolist())
selected_mode = st.sidebar.selectbox("Ship Mode", all_modes)

lt_min     = int(df['Lead Time'].min())
lt_max     = int(df['Lead Time'].max())
lt_default = int(df['Lead Time'].median())
lead_threshold = st.sidebar.slider("Lead Time Threshold (days)", lt_min, lt_max, lt_default)

st.sidebar.markdown("---")
date_min = df['Order Date'].min().date()
date_max = df['Order Date'].max().date()
start_date = st.sidebar.date_input("Order Date — From", value=date_min, min_value=date_min, max_value=date_max)
end_date   = st.sidebar.date_input("Order Date — To",   value=date_max, min_value=date_min, max_value=date_max)

if start_date > end_date:
    st.sidebar.error("'From' date must be before 'To' date.")
    st.stop()

#Apply Filters
fdf = df.copy()
fdf = fdf[(fdf['Order Date'].dt.date >= start_date) & (fdf['Order Date'].dt.date <= end_date)]
if selected_region != "All":
    fdf = fdf[fdf['Region'] == selected_region]
if selected_mode != "All":
    fdf = fdf[fdf['Ship Mode'] == selected_mode]

if fdf.empty:
    st.warning("No data matches the selected filters. Please adjust your selections.")
    st.stop()

#Page Title & KPIs 
st.title("Nassau Candy Distributor — Shipping Dashboard")

delay_pct = (fdf['Lead Time'] > lead_threshold).mean() * 100
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Orders",           f"{len(fdf):,}")
k2.metric("Avg Lead Time (days)",   f"{fdf['Lead Time'].mean():.1f}")
k3.metric("Delay Frequency",        f"{delay_pct:.1f} %")
k4.metric("Total Sales",            f"${fdf['Sales'].sum():,.0f}")

st.markdown("---")


# MODULE 1 — Route Efficiency Overview
st.header("📦 Module 1 — Route Efficiency Overview")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Average Lead Time by Route")
    route_avg = (
        fdf.groupby(['Region', 'Ship Mode'])['Lead Time']
        .mean()
        .reset_index()
        .rename(columns={'Lead Time': 'Avg Lead Time'})
        .sort_values('Avg Lead Time')
    )
    fig_route = px.bar(
        route_avg,
        x='Avg Lead Time',
        y='Region',
        color='Ship Mode',
        orientation='h',
        barmode='group',
        title='Avg Lead Time by Region & Ship Mode',
        labels={'Avg Lead Time': 'Avg Lead Time (days)'}
    )
    st.plotly_chart(fig_route, use_container_width=True)

with col_b:
    st.subheader("Route Performance Leaderboard")
    leaderboard = (
        fdf.groupby(['Region', 'Ship Mode'])
        .agg(
            Avg_Lead_Time=('Lead Time', 'mean'),
            Total_Orders=('Order ID', 'count'),
            Delay_Pct=('Lead Time', lambda x: (x > lead_threshold).mean() * 100)
        )
        .reset_index()
        .rename(columns={
            'Avg_Lead_Time': 'Avg Lead Time (days)',
            'Total_Orders':  'Orders',
            'Delay_Pct':     'Delay %'
        })
        .sort_values('Avg Lead Time (days)')
    )
    leaderboard['Avg Lead Time (days)'] = leaderboard['Avg Lead Time (days)'].round(1)
    leaderboard['Delay %'] = leaderboard['Delay %'].round(1)
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)

st.markdown("---")


# MODULE 2 — Geographic Shipping Map
st.header("🗺️ Module 2 — Geographic Shipping Map")

state_data = (
    fdf.groupby('State/Province')
    .agg(
        Avg_Lead_Time=('Lead Time', 'mean'),
        Total_Orders=('Order ID', 'count'),
        Delay_Pct=('Lead Time', lambda x: (x > lead_threshold).mean() * 100)
    )
    .reset_index()
    .rename(columns={'State/Province': 'State'})
)
state_data['Avg_Lead_Time'] = state_data['Avg_Lead_Time'].round(1)
state_data['Delay_Pct']     = state_data['Delay_Pct'].round(1)

col_m1, col_m2 = st.columns(2)

with col_m1:
    st.subheader("US Heatmap — Shipping Efficiency")
    fig_map = px.choropleth(
        state_data,
        locations='State',
        locationmode='USA-states',
        color='Avg_Lead_Time',
        scope='usa',
        color_continuous_scale='RdYlGn_r',
        title='Avg Lead Time by State (darker = slower)',
        labels={'Avg_Lead_Time': 'Avg Lead Time (days)'},
        hover_data={'State': True, 'Total_Orders': True, 'Delay_Pct': True}
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with col_m2:
    st.subheader("Regional Bottleneck Visualization")
    fig_bottle = px.choropleth(
        state_data,
        locations='State',
        locationmode='USA-states',
        color='Delay_Pct',
        scope='usa',
        color_continuous_scale='Reds',
        title='Delay % by State (darker = more delays)',
        labels={'Delay_Pct': 'Delay %'},
        hover_data={'State': True, 'Total_Orders': True, 'Avg_Lead_Time': True}
    )
    fig_bottle.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_bottle, use_container_width=True)

st.markdown("---")


# MODULE 3 — Ship Mode Comparison
st.header("🚚 Module 3 — Ship Mode Comparison")

col_s1, col_s2 = st.columns(2)

with col_s1:
    st.subheader("Lead Time Distribution by Ship Mode")
    fig_box = px.box(
        fdf,
        x='Ship Mode',
        y='Lead Time',
        color='Ship Mode',
        title='Lead Time Distribution by Ship Mode',
        labels={'Lead Time': 'Lead Time (days)'}
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

with col_s2:
    st.subheader("Avg Lead Time & Delay % by Ship Mode")
    mode_stats = (
        fdf.groupby('Ship Mode')
        .agg(
            Avg_Lead_Time=('Lead Time', 'mean'),
            Delay_Pct=('Lead Time', lambda x: (x > lead_threshold).mean() * 100)
        )
        .reset_index()
    )
    fig_mode = px.scatter(
        mode_stats,
        x='Avg_Lead_Time',
        y='Delay_Pct',
        text='Ship Mode',
        size='Avg_Lead_Time',
        color='Ship Mode',
        title='Ship Mode: Speed vs Reliability',
        labels={'Avg_Lead_Time': 'Avg Lead Time (days)', 'Delay_Pct': 'Delay %'}
    )
    fig_mode.update_traces(textposition='top center')
    st.plotly_chart(fig_mode, use_container_width=True)

st.markdown("---")


# MODULE 4 — Route Drill-Down
st.header("🔍 Module 4 — Route Drill-Down")

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.subheader("State-Level Performance Insights")
    state_perf = (
        fdf.groupby(['State/Province', 'Region'])
        .agg(
            Avg_Lead_Time=('Lead Time', 'mean'),
            Orders=('Order ID', 'count'),
            Delay_Pct=('Lead Time', lambda x: (x > lead_threshold).mean() * 100),
            Avg_Sales=('Sales', 'mean')
        )
        .reset_index()
        .sort_values('Avg_Lead_Time', ascending=False)
    )
    state_perf['Avg_Lead_Time'] = state_perf['Avg_Lead_Time'].round(1)
    state_perf['Delay_Pct']     = state_perf['Delay_Pct'].round(1)
    state_perf['Avg_Sales']     = state_perf['Avg_Sales'].round(2)

    fig_state = px.bar(
        state_perf.head(15),
        x='Avg_Lead_Time',
        y='State/Province',
        color='Region',
        orientation='h',
        title='Top 15 Slowest States by Avg Lead Time',
        labels={'Avg_Lead_Time': 'Avg Lead Time (days)', 'State/Province': 'State'}
    )
    fig_state.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_state, use_container_width=True)

with col_d2:
    st.subheader("Order-Level Shipment Timelines")
# Show a sample of individual orders as a timeline (Gantt-style)
    sample_orders = fdf.nlargest(30, 'Lead Time')[
        ['Order ID', 'Order Date', 'Ship Date', 'Lead Time', 'Ship Mode', 'State/Province']
    ].copy()
    sample_orders = sample_orders.sort_values('Lead Time', ascending=False)

    fig_timeline = px.timeline(
        sample_orders,
        x_start='Order Date',
        x_end='Ship Date',
        y='Order ID',
        color='Ship Mode',
        title='Top 30 Longest Shipment Timelines',
        hover_data={'Lead Time': True, 'State/Province': True}
    )
    fig_timeline.update_yaxes(autorange='reversed')
    fig_timeline.update_layout(showlegend=True, height=500)
    st.plotly_chart(fig_timeline, use_container_width=True)

# State-level detail table
st.subheader("State Performance Detail Table")
st.dataframe(
    state_perf.rename(columns={
        'State/Province': 'State',
        'Avg_Lead_Time':  'Avg Lead Time (days)',
        'Delay_Pct':      'Delay %',
        'Avg_Sales':      'Avg Sales ($)'
    }),
    use_container_width=True,
    hide_index=True
)