"""
MLB Capstone -- Program 4: Interactive Streamlit Dashboard
=========================================================
Visualizes MLB historical data from mlb.db using Plotly.
Uses only the `events` and `players` tables produced by the scraper.

Run locally:
    streamlit run 4_dashboard.py

Deploy to Streamlit Cloud:
    Push repo to GitHub, then connect at share.streamlit.io
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "mlb.db")

st.set_page_config(
    page_title="MLB Historical Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# CSS
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Source+Sans+3:wght@300;400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; }
    .stApp { background-color: #0d1b0f; }
    .main .block-container { padding-top: 1.5rem; }

    .dashboard-header {
        background: linear-gradient(135deg, #1a3c1e 0%, #0d1b0f 60%, #1a1a0a 100%);
        border: 1px solid #2d5c32;
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .dashboard-header::before {
        content: "⚾";
        position: absolute;
        right: 2rem; top: 50%;
        transform: translateY(-50%);
        font-size: 5rem;
        opacity: 0.08;
    }
    .dashboard-header h1 {
        font-family: 'Playfair Display', serif;
        color: #e8c96a;
        font-size: 2.6rem;
        font-weight: 900;
        margin: 0 0 0.3rem 0;
    }
    .dashboard-header p { color: #8ab890; font-size: 1rem; margin: 0; }

    .metric-card {
        background: #1a3c1e;
        border: 1px solid #2d5c32;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card .metric-value {
        font-family: 'Playfair Display', serif;
        font-size: 2.2rem;
        color: #e8c96a;
        font-weight: 700;
    }
    .metric-card .metric-label {
        font-size: 0.8rem;
        color: #8ab890;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .section-title {
        font-family: 'Playfair Display', serif;
        color: #e8c96a;
        font-size: 1.4rem;
        font-weight: 700;
        border-bottom: 1px solid #2d5c32;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    [data-testid="stSidebar"] { background-color: #111d12 !important; border-right: 1px solid #2d5c32; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stSlider label { color: #8ab890 !important; }
    hr { border-color: #2d5c32; }
    .event-item {
        background: #1a3c1e;
        border-left: 3px solid #e8c96a;
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
        border-radius: 0 6px 6px 0;
        color: #d4e8d4;
        font-size: 0.9rem;
    }
    .event-year { color: #e8c96a; font-weight: 600; margin-right: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------

@st.cache_data
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Run 2_db_import.py first.")
        st.stop()

    conn = sqlite3.connect(DB_PATH)
    players = pd.read_sql("SELECT * FROM players", conn)
    events  = pd.read_sql("SELECT * FROM events",  conn)
    conn.close()

    # Coerce numeric columns
    for col in ["home_runs", "batting_avg", "hits", "stolen_bases", "era", "wins", "so"]:
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors="coerce")

    players["year"] = pd.to_numeric(players["year"], errors="coerce")
    events["year"]  = pd.to_numeric(events["year"],  errors="coerce")

    if "value" in events.columns:
        events["value"] = pd.to_numeric(events["value"], errors="coerce")

    players["decade"] = ((players["year"] // 10) * 10).astype("Int64")

    return players, events


players_df, events_df = load_data()

# -----------------------------------------------------------------------------
# PLOTLY THEME
# -----------------------------------------------------------------------------

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0d1b0f",
    plot_bgcolor="#111d12",
    font=dict(color="#d4e8d4", family="Source Sans 3"),
    title_font=dict(color="#e8c96a", family="Playfair Display", size=16),
    legend=dict(bgcolor="#1a3c1e", bordercolor="#2d5c32", borderwidth=1),
    xaxis=dict(gridcolor="#1e3a22", zerolinecolor="#2d5c32"),
    yaxis=dict(gridcolor="#1e3a22", zerolinecolor="#2d5c32"),
    margin=dict(t=50, b=40, l=50, r=20),
)
GOLD   = "#e8c96a"
GREEN  = "#4caf70"
RED    = "#e87070"
TEAL   = "#5abcb4"
COLORS = [GOLD, GREEN, RED, TEAL, "#b07de8", "#e8a87d", "#7db0e8"]

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚾ Filters")
    st.markdown("---")

    all_years  = sorted(players_df["year"].dropna().unique().astype(int))
    year_range = st.slider("Season Range",
                           min_value=min(all_years), max_value=max(all_years),
                           value=(min(all_years), max(all_years)))

    leagues_available = sorted(players_df["league"].dropna().unique()) if "league" in players_df.columns else []
    all_leagues = ["Both"] + leagues_available
    sel_league  = st.selectbox("League", all_leagues)

    all_teams  = sorted(players_df["team"].dropna().unique())
    sel_teams  = st.multiselect("Teams (optional)", all_teams)

    st.markdown("---")

    # Scatter axis options: only columns that exist and have numeric data
    numeric_cols = [c for c in ["home_runs","batting_avg","hits","stolen_bases","era","wins","so"]
                    if c in players_df.columns and players_df[c].notna().any()]
    stat_x = st.selectbox("Scatter X-axis", numeric_cols, index=0)
    stat_y = st.selectbox("Scatter Y-axis", numeric_cols, index=min(1, len(numeric_cols)-1))

    st.markdown("---")
    all_stats = sorted(events_df["statistic"].dropna().unique()) if "statistic" in events_df.columns else []
    sel_stat  = st.selectbox("Stat Category (events)", ["All"] + list(all_stats))

    st.markdown("<small style='color:#8ab890'>Data sourced from Baseball Almanac via Selenium scraper.</small>",
                unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FILTERED DATA
# -----------------------------------------------------------------------------

p_mask = players_df["year"].between(year_range[0], year_range[1])
if sel_league != "Both" and "league" in players_df.columns:
    p_mask &= players_df["league"] == sel_league
if sel_teams:
    p_mask &= players_df["team"].isin(sel_teams)
filtered = players_df[p_mask]

e_mask = events_df["year"].between(year_range[0], year_range[1])
if sel_stat != "All" and "statistic" in events_df.columns:
    e_mask &= events_df["statistic"] == sel_stat
filtered_events = events_df[e_mask]

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------

st.markdown("""
<div class="dashboard-header">
    <h1>MLB Historical Dashboard</h1>
    <p>Explore baseball statistics and league leaders from Baseball Almanac</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# KPI METRICS
# -----------------------------------------------------------------------------

hr_max   = int(filtered["home_runs"].max())  if filtered["home_runs"].notna().any()   else 0
ba_max   = filtered["batting_avg"].max()     if filtered["batting_avg"].notna().any() else 0
seasons  = int(filtered["year"].nunique())
players  = int(filtered["player_name"].nunique()) if "player_name" in filtered.columns else 0
ev_count = len(filtered_events)

col1, col2, col3, col4, col5 = st.columns(5)
for col, val, label in [
    (col1, str(players),              "Unique Players"),
    (col2, str(seasons),              "Seasons"),
    (col3, str(hr_max),               "Top HR in Range"),
    (col4, f"{ba_max:.3f}",           "Top Batting Avg"),
    (col5, str(ev_count),             "Stat Leader Entries"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# CHART 1 + 2: HR over time | Batting Avg distribution
# -----------------------------------------------------------------------------

st.markdown('<div class="section-title">📈 Offensive Trends Over Time</div>', unsafe_allow_html=True)
col_l, col_r = st.columns([3, 2])

with col_l:
    hr_year = (
        filtered.groupby("year")["home_runs"]
        .max().reset_index().sort_values("year")
    )
    fig_hr = go.Figure()
    fig_hr.add_trace(go.Scatter(
        x=hr_year["year"], y=hr_year["home_runs"],
        mode="lines+markers", name="Peak HR",
        line=dict(color=GOLD, width=2.5),
        marker=dict(size=6, color=GOLD),
        hovertemplate="<b>%{x}</b><br>Peak HR: %{y}<extra></extra>",
    ))
    fig_hr.update_layout(**PLOTLY_LAYOUT,
                         title="Peak Home Runs per Season",
                         xaxis_title="Season", yaxis_title="Home Runs",
                         height=340)
    st.plotly_chart(fig_hr, use_container_width=True)

with col_r:
    ba_data = filtered["batting_avg"].dropna()
    if ba_data.empty:
        st.info("No batting average data for selected filters.")
    else:
        fig_ba = go.Figure()
        fig_ba.add_trace(go.Histogram(
            x=ba_data, nbinsx=20,
            marker_color=TEAL, opacity=0.85,
            hovertemplate="BA: %{x:.3f}<br>Count: %{y}<extra></extra>",
        ))
        fig_ba.add_vline(x=ba_data.mean(), line=dict(color=GOLD, dash="dash"),
                         annotation_text=f"Mean: {ba_data.mean():.3f}",
                         annotation_font_color=GOLD)
        fig_ba.update_layout(**PLOTLY_LAYOUT,
                             title="Batting Average Distribution",
                             xaxis_title="Batting Average", yaxis_title="Frequency",
                             height=340)
        st.plotly_chart(fig_ba, use_container_width=True)

# -----------------------------------------------------------------------------
# CHART 3 + 4: Scatter | Stat leaders by team
# -----------------------------------------------------------------------------

st.markdown('<div class="section-title">🔍 Player Performance Explorer</div>', unsafe_allow_html=True)
col_l2, col_r2 = st.columns([3, 2])

with col_l2:
    req_cols = [c for c in [stat_x, stat_y, "player_name", "team", "year"] if c in filtered.columns]
    scatter_data = filtered[req_cols].dropna(subset=[stat_x, stat_y])
    color_col = "league" if (sel_league == "Both" and "league" in scatter_data.columns) else "team"
    fig_sc = px.scatter(
        scatter_data, x=stat_x, y=stat_y,
        color=color_col if color_col in scatter_data.columns else None,
        hover_data=[c for c in ["player_name","year","team"] if c in scatter_data.columns],
        color_discrete_sequence=COLORS,
        title=f"{stat_y.replace('_',' ').title()} vs {stat_x.replace('_',' ').title()}",
    )
    fig_sc.update_traces(marker=dict(size=9, opacity=0.8))
    fig_sc.update_layout(**PLOTLY_LAYOUT, height=360)
    st.plotly_chart(fig_sc, use_container_width=True)

with col_r2:
    if "statistic" in events_df.columns and "team" in events_df.columns:
        team_leads = (
            filtered_events.groupby("team").size()
            .reset_index(name="leader_appearances")
            .sort_values("leader_appearances", ascending=True)
            .tail(15)
        )
        fig_team = go.Figure(go.Bar(
            y=team_leads["team"],
            x=team_leads["leader_appearances"],
            orientation="h",
            marker=dict(color=team_leads["leader_appearances"],
                        colorscale=[[0,"#1a3c1e"],[0.5,GREEN],[1.0,GOLD]],
                        showscale=False),
            text=team_leads["leader_appearances"],
            textposition="outside",
            textfont=dict(color=GOLD),
            hovertemplate="%{y}: %{x} appearances<extra></extra>",
        ))
        fig_team.update_layout(**PLOTLY_LAYOUT,
                               title="Stat Leader Appearances by Team",
                               xaxis_title="Times Led a Category",
                               height=360)
        st.plotly_chart(fig_team, use_container_width=True)

# -----------------------------------------------------------------------------
# CHART 5: Stats by decade
# -----------------------------------------------------------------------------

st.markdown('<div class="section-title">📊 Stats by Decade</div>', unsafe_allow_html=True)

decade_stats = (
    filtered.groupby("decade")[["home_runs","batting_avg"]]
    .mean().round(3).reset_index().dropna(subset=["decade"])
)
decade_stats["decade_label"] = decade_stats["decade"].astype(str) + "s"

fig_dec = go.Figure()
fig_dec.add_trace(go.Bar(
    x=decade_stats["decade_label"], y=decade_stats["home_runs"],
    name="Avg HR", marker_color=GOLD,
    hovertemplate="Decade: %{x}<br>Avg HR: %{y:.1f}<extra></extra>",
))
fig_dec.add_trace(go.Scatter(
    x=decade_stats["decade_label"], y=decade_stats["batting_avg"],
    name="Avg BA", mode="lines+markers",
    line=dict(color=TEAL, width=2.5),
    yaxis="y2",
    hovertemplate="Decade: %{x}<br>Avg BA: %{y:.3f}<extra></extra>",
))
fig_dec.update_layout(**{k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"},
    title="Average Home Runs and Batting Average by Decade",
    barmode="group",
    height=340,
    yaxis=dict(title="Avg HR", gridcolor="#1e3a22", zerolinecolor="#2d5c32"),
    yaxis2=dict(title="Avg BA", overlaying="y", side="right",
                tickfont=dict(color=TEAL), showgrid=False),
)
st.plotly_chart(fig_dec, use_container_width=True)

# -----------------------------------------------------------------------------
# STAT LEADERS TIMELINE (events table)
# -----------------------------------------------------------------------------

st.markdown('<div class="section-title">📅 Stat Leaders Timeline</div>', unsafe_allow_html=True)

if filtered_events.empty:
    st.info("No events found for selected filters.")
else:
    display_cols = [c for c in ["year","league","statistic","player","team","value"]
                    if c in filtered_events.columns]
    st.dataframe(
        filtered_events[display_cols].sort_values("year", ascending=False),
        use_container_width=True,
        height=350,
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# RAW DATA EXPLORER
# -----------------------------------------------------------------------------

with st.expander("🗃️ Raw Data Explorer", expanded=False):
    tab1, tab2 = st.tabs(["Players", "Events"])
    with tab1:
        st.dataframe(filtered.sort_values("year", ascending=False),
                     use_container_width=True, height=350)
    with tab2:
        st.dataframe(filtered_events.sort_values("year", ascending=False),
                     use_container_width=True, height=350)

st.markdown("""
<div style='text-align:center; color:#4a7a4e; font-size:0.8rem; padding:1rem 0 0.5rem'>
    MLB Historical Dashboard &nbsp;|&nbsp; Data sourced from Baseball Almanac &nbsp;|&nbsp; Built with Streamlit + Plotly
</div>
""", unsafe_allow_html=True)