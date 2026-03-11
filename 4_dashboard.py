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
# CSS — Editorial / Sports-Magazine
# Deep navy base, crisp white cards, sharp red accent, condensed display font
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500&display=swap');

    :root {
        --navy:   #0b0f1a;
        --panel:  #111827;
        --card:   #1a2233;
        --border: #1e2d45;
        --red:    #e63946;
        --amber:  #f4a261;
        --teal:   #2ec4b6;
        --text:   #e8eaf0;
        --muted:  #6b7a99;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--text);
    }

    .stApp { background-color: var(--navy); }
    .main .block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1400px; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: var(--panel) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; }
    [data-testid="stSidebar"] .stSelectbox > div,
    [data-testid="stSidebar"] .stMultiSelect > div {
        background: var(--card) !important;
        border-color: var(--border) !important;
    }
    [data-testid="stSidebar"] .stSlider > div > div > div {
        background: var(--red) !important;
    }

    /* ── Header band ── */
    .site-header {
        display: flex;
        align-items: flex-end;
        gap: 1.5rem;
        border-bottom: 3px solid var(--red);
        padding-bottom: 1rem;
        margin-bottom: 1.8rem;
    }
    .site-header .badge {
        background: var(--red);
        color: #fff;
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 900;
        font-size: 0.75rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 2px;
        margin-bottom: 4px;
    }
    .site-header h1 {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 900;
        font-size: 3.2rem;
        letter-spacing: -1px;
        color: #fff;
        margin: 0;
        line-height: 1;
    }
    .site-header h1 span { color: var(--red); }
    .site-header p {
        color: var(--muted);
        font-size: 0.9rem;
        margin: 4px 0 0;
        font-weight: 300;
    }

    /* ── KPI strip ── */
    .kpi-strip {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1px;
        background: var(--border);
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 2rem;
    }
    .kpi-cell {
        background: var(--card);
        padding: 1.1rem 1.4rem;
    }
    .kpi-cell .kpi-val {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 800;
        font-size: 2.1rem;
        color: #fff;
        line-height: 1;
    }
    .kpi-cell .kpi-val.accent { color: var(--red); }
    .kpi-cell .kpi-label {
        font-size: 0.72rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 4px;
    }

    /* ── Section headings ── */
    .sec-head {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 800;
        font-size: 1.3rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #fff;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 2rem 0 1rem;
    }
    .sec-head::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border);
    }
    .sec-head .dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--red);
        flex-shrink: 0;
    }

    /* ── Chart cards ── */
    .chart-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
    }

    /* ── Events table ── */
    .ev-row {
        display: grid;
        grid-template-columns: 60px 60px 1fr 120px 100px;
        gap: 1rem;
        padding: 0.55rem 1rem;
        border-bottom: 1px solid var(--border);
        font-size: 0.875rem;
        align-items: center;
    }
    .ev-row:hover { background: var(--card); }
    .ev-header {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--muted);
        background: var(--panel);
        border-radius: 6px 6px 0 0;
        border-bottom: 2px solid var(--red);
    }
    .ev-year { color: var(--red); font-weight: 600; }
    .ev-league {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 1px;
        padding: 2px 6px;
        border-radius: 3px;
        background: var(--border);
        color: var(--muted);
        text-align: center;
    }
    .ev-league.AL { background: #1a2c45; color: #60a5fa; }
    .ev-league.NL { background: #1a2d1a; color: #4ade80; }
    .ev-val {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        color: var(--amber);
        text-align: right;
    }

    /* ── Sidebar label ── */
    .sidebar-logo {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 900;
        font-size: 1.4rem;
        letter-spacing: 1px;
        color: #fff;
        border-bottom: 2px solid var(--red);
        padding-bottom: 0.5rem;
        margin-bottom: 1.2rem;
    }
    .sidebar-logo span { color: var(--red); }

    hr { border-color: var(--border) !important; }

    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------

# Mapping from events.statistic -> players column name
STAT_TO_COL = {
    "Home Runs":       "home_runs",
    "Batting Average": "batting_avg",
    "Hits":            "hits",
    "Stolen Bases":    "stolen_bases",
    "ERA":             "era",
    "Earned Run Average": "era",
    "Wins":            "wins",
    "Strikeouts":      "so",
    "RBI":             "rbi",
    "Runs Batted In":  "rbi",
    "Runs":            "runs",
    "Doubles":         "doubles",
    "Triples":         "triples",
    "Saves":           "saves",
    "Slugging Average":     "slg",
    "On Base Percentage":   "obp",
    "Base on Balls":        "bb",
    "Total Bases":          "total_bases",
    "Winning Percentage":   "win_pct",
    "Complete Games":       "cg",
    "Shutouts":             "sho",
    "Games":                "games",
}


@st.cache_data
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Run 2_db_import.py first.")
        st.stop()

    conn = sqlite3.connect(DB_PATH)
    players = pd.read_sql("SELECT * FROM players", conn)
    events  = pd.read_sql("SELECT * FROM events",  conn)
    conn.close()

    # Coerce types
    players["year"] = pd.to_numeric(players["year"], errors="coerce")
    events["year"]  = pd.to_numeric(events["year"],  errors="coerce")
    if "value" in events.columns:
        events["value"] = pd.to_numeric(events["value"], errors="coerce")

    # ── Build a wide stats table from events ─────────────────────────────────
    # Pivot events into one row per player+year+league, stat categories as cols
    ev = events.copy()
    ev["col"] = ev["statistic"].map(STAT_TO_COL)
    ev = ev[ev["col"].notna()]   # drop stats we don't have a column mapping for

    ev_wide = ev.pivot_table(
        index=["year", "league", "player", "team"],
        columns="col",
        values="value",
        aggfunc="first",
    ).reset_index()
    ev_wide.columns.name = None
    ev_wide = ev_wide.rename(columns={"player": "player_name"})

    # ── Merge players (pivot) with ev_wide (events pivot) ────────────────────
    # players has one row per stat leader per year; ev_wide has the same but
    # wider. Outer-merge so we keep everyone, then fill missing values from
    # whichever side has them.
    merge_keys = ["year", "league", "player_name", "team"]
    # Only merge on keys that exist in both
    merge_keys = [k for k in merge_keys if k in players.columns and k in ev_wide.columns]

    merged = players.merge(ev_wide, on=merge_keys, how="outer", suffixes=("", "_ev"))

    # For each stat column, if the players version is null, fill from events version
    for col in ev_wide.columns:
        if col in merge_keys:
            continue
        ev_col = col + "_ev"
        if col in merged.columns and ev_col in merged.columns:
            merged[col] = merged[col].fillna(merged[ev_col])
            merged.drop(columns=[ev_col], inplace=True)
        elif ev_col in merged.columns:
            merged.rename(columns={ev_col: col}, inplace=True)

    # Coerce all stat columns to numeric
    stat_cols = [c for c in merged.columns if c not in merge_keys + ["decade"]]
    for col in stat_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged["decade"] = ((merged["year"] // 10) * 10).astype("Int64")

    return merged, events


players_df, events_df = load_data()

# -----------------------------------------------------------------------------
# PLOTLY THEME
# -----------------------------------------------------------------------------

PL = dict(
    paper_bgcolor="#1a2233",
    plot_bgcolor="#1a2233",
    font=dict(color="#9aa3b8", family="DM Sans", size=12),
    title_font=dict(color="#ffffff", family="Barlow Condensed", size=17),
    legend=dict(bgcolor="#111827", bordercolor="#1e2d45", borderwidth=1,
                font=dict(color="#e8eaf0")),
    xaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45",
               tickfont=dict(color="#6b7a99")),
    yaxis=dict(gridcolor="#1e2d45", zerolinecolor="#1e2d45",
               tickfont=dict(color="#6b7a99")),
    margin=dict(t=46, b=36, l=48, r=16),
)
RED   = "#e63946"
AMBER = "#f4a261"
TEAL  = "#2ec4b6"
BLUE  = "#60a5fa"
GREEN = "#4ade80"
COLORS = [RED, AMBER, TEAL, BLUE, GREEN, "#c084fc", "#fb923c"]

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="sidebar-logo">MLB<span>.</span>DATA</div>', unsafe_allow_html=True)

    all_years  = sorted(players_df["year"].dropna().unique().astype(int))
    year_range = st.slider("Season Range",
                           min_value=min(all_years), max_value=max(all_years),
                           value=(min(all_years), max(all_years)))

    leagues_available = sorted(players_df["league"].dropna().unique()) if "league" in players_df.columns else []
    sel_league = st.selectbox("League", ["Both"] + leagues_available)

    # Teams are already normalized to canonical names by the scraper
    available_canonical = sorted(players_df["team"].dropna().unique())
    sel_canonical = st.multiselect("Teams", available_canonical)
    sel_teams = sel_canonical

    st.markdown("---")

    all_stat_cols = [
        "home_runs","batting_avg","hits","rbi","runs","doubles","triples",
        "stolen_bases","total_bases","obp","slg","bb",
        "era","wins","so","saves","cg","sho","win_pct","games",
    ]
    numeric_cols = [c for c in all_stat_cols
                    if c in players_df.columns and players_df[c].notna().any()]
    stat_x = st.selectbox("Scatter X", numeric_cols, index=0)
    stat_y = st.selectbox("Scatter Y", numeric_cols, index=min(1, len(numeric_cols)-1))

    st.markdown("---")
    all_stats = sorted(events_df["statistic"].dropna().unique()) if "statistic" in events_df.columns else []
    sel_stat  = st.selectbox("Stat Category", ["All"] + list(all_stats))

# -----------------------------------------------------------------------------
# FILTERED DATA
# -----------------------------------------------------------------------------

p_mask = players_df["year"].between(year_range[0], year_range[1])
if sel_league != "Both" and "league" in players_df.columns:
    p_mask &= players_df["league"] == sel_league
if sel_canonical:
    p_mask &= players_df["team"].isin(sel_teams)
filtered = players_df[p_mask]

e_mask = events_df["year"].between(year_range[0], year_range[1])
if sel_stat != "All" and "statistic" in events_df.columns:
    e_mask &= events_df["statistic"] == sel_stat
filtered_events = events_df[e_mask]

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------

st.markdown(f"""
<div class="site-header">
    <div>
        <div class="badge">Season Analysis</div>
        <h1>MLB <span>Historical</span> Dashboard</h1>
        <p>Baseball Almanac data &nbsp;·&nbsp; {year_range[0]}–{year_range[1]} &nbsp;·&nbsp; {len(filtered):,} player seasons</p>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# KPI STRIP
# -----------------------------------------------------------------------------

hr_max  = int(filtered["home_runs"].max())  if filtered["home_runs"].notna().any()   else 0
ba_max  = filtered["batting_avg"].max()     if filtered["batting_avg"].notna().any() else 0
seasons = int(filtered["year"].nunique())
players = int(filtered["player_name"].nunique()) if "player_name" in filtered.columns else 0
ev_ct   = len(filtered_events)

st.markdown(f"""
<div class="kpi-strip">
    <div class="kpi-cell"><div class="kpi-val">{players:,}</div><div class="kpi-label">Unique Players</div></div>
    <div class="kpi-cell"><div class="kpi-val">{seasons}</div><div class="kpi-label">Seasons</div></div>
    <div class="kpi-cell"><div class="kpi-val accent">{hr_max}</div><div class="kpi-label">Top HR Season</div></div>
    <div class="kpi-cell"><div class="kpi-val">{ba_max:.3f}</div><div class="kpi-label">Top Batting Avg</div></div>
    <div class="kpi-cell"><div class="kpi-val">{ev_ct:,}</div><div class="kpi-label">Stat Entries</div></div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CHART ROW 1 — HR trend | BA distribution
# -----------------------------------------------------------------------------

st.markdown('<div class="sec-head"><span class="dot"></span>Offensive Trends</div>', unsafe_allow_html=True)
c1, c2 = st.columns([3, 2], gap="medium")

with c1:
    hr_year = (filtered.groupby("year")["home_runs"]
               .max().reset_index().sort_values("year"))
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=hr_year["year"], y=hr_year["home_runs"],
        mode="lines", name="Peak HR",
        line=dict(color=RED, width=2),
        fill="tozeroy", fillcolor="rgba(230,57,70,0.08)",
        hovertemplate="<b>%{x}</b><br>Peak HR: %{y}<extra></extra>",
    ))
    fig1.update_layout(**PL, title="Peak Home Runs per Season",
                       xaxis_title="Season", yaxis_title="HR", height=320)
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    ba_data = filtered["batting_avg"].dropna()
    if ba_data.empty:
        st.info("No batting average data.")
    else:
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=ba_data, nbinsx=20,
            marker_color=TEAL, opacity=0.9,
            hovertemplate="BA: %{x:.3f}<br>Count: %{y}<extra></extra>",
        ))
        fig2.add_vline(x=ba_data.mean(), line=dict(color=AMBER, dash="dash", width=1.5),
                       annotation_text=f"Mean {ba_data.mean():.3f}",
                       annotation_font_color=AMBER, annotation_font_size=11)
        fig2.update_layout(**PL, title="Batting Average Distribution",
                           xaxis_title="BA", yaxis_title="Count", height=320)
        st.plotly_chart(fig2, use_container_width=True)

# -----------------------------------------------------------------------------
# CHART ROW 2 — Scatter | Team leader count
# -----------------------------------------------------------------------------

st.markdown('<div class="sec-head"><span class="dot"></span>Player Performance</div>', unsafe_allow_html=True)
c3, c4 = st.columns([3, 2], gap="medium")

with c3:
    req = [c for c in [stat_x, stat_y, "player_name", "team", "year"] if c in filtered.columns]
    sc_data = filtered[req].dropna(subset=[stat_x, stat_y])
    color_col = "league" if (sel_league == "Both" and "league" in sc_data.columns) else "team"
    fig3 = px.scatter(
        sc_data, x=stat_x, y=stat_y,
        color=color_col if color_col in sc_data.columns else None,
        hover_data=[c for c in ["player_name","year","team"] if c in sc_data.columns],
        color_discrete_sequence=COLORS,
        title=f"{stat_y.replace('_',' ').title()} vs {stat_x.replace('_',' ').title()}",
    )
    fig3.update_traces(marker=dict(size=8, opacity=0.75,
                                   line=dict(width=0.5, color="#0b0f1a")))
    fig3.update_layout(**PL, height=340)
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    if "team" in filtered_events.columns and not filtered_events.empty:
        team_leads = (filtered_events.groupby("team").size()
                      .reset_index(name="count")
                      .sort_values("count", ascending=True).tail(14))
        fig4 = go.Figure(go.Bar(
            y=team_leads["team"], x=team_leads["count"],
            orientation="h",
            marker=dict(color=team_leads["count"],
                        colorscale=[[0, "#1a2233"],[0.5, TEAL],[1.0, RED]],
                        showscale=False),
            text=team_leads["count"], textposition="outside",
            textfont=dict(color="#e8eaf0", size=11),
            hovertemplate="%{y}: %{x}<extra></extra>",
        ))
        fig4.update_layout(**PL, title="Stat Leader Appearances by Team",
                           xaxis_title="Count", height=340)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No team data available for selected filters.")

# -----------------------------------------------------------------------------
# CHART ROW 3 — Decade summary (full width)
# -----------------------------------------------------------------------------

st.markdown('<div class="sec-head"><span class="dot"></span>Stats by Decade</div>', unsafe_allow_html=True)

decade_stats = (
    filtered.groupby("decade")[["home_runs","batting_avg"]]
    .mean().round(3).reset_index().dropna(subset=["decade"])
)
decade_stats["decade_label"] = decade_stats["decade"].astype(str) + "s"

if not decade_stats.empty:
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        x=decade_stats["decade_label"], y=decade_stats["home_runs"],
        name="Avg HR", marker_color=RED, opacity=0.85,
        hovertemplate="Decade: %{x}<br>Avg HR: %{y:.1f}<extra></extra>",
    ))
    fig5.add_trace(go.Scatter(
        x=decade_stats["decade_label"], y=decade_stats["batting_avg"],
        name="Avg BA", mode="lines+markers",
        line=dict(color=TEAL, width=2.5),
        marker=dict(size=7, color=TEAL),
        yaxis="y2",
        hovertemplate="Decade: %{x}<br>Avg BA: %{y:.3f}<extra></extra>",
    ))
    fig5.update_layout(
        **{k: v for k, v in PL.items() if k != "yaxis"},
        title="Average Home Runs and Batting Average by Decade",
        barmode="group",
        height=320,
        yaxis=dict(title="Avg HR", gridcolor="#1e2d45", zerolinecolor="#1e2d45",
                   tickfont=dict(color="#6b7a99")),
        yaxis2=dict(title="Avg BA", overlaying="y", side="right",
                    tickfont=dict(color=TEAL), showgrid=False),
    )
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("Not enough data to show decade summary.")

# -----------------------------------------------------------------------------
# STAT LEADERS TABLE
# -----------------------------------------------------------------------------

st.markdown('<div class="sec-head"><span class="dot"></span>Stat Leaders</div>', unsafe_allow_html=True)

if filtered_events.empty:
    st.info("No stat leader data for selected filters.")
else:
    show_cols = [c for c in ["year","league","statistic","player","team","value"]
                 if c in filtered_events.columns]
    ev_sorted = filtered_events[show_cols].sort_values("year", ascending=False)

    # Known junk: division headers, team win-total rows, section labels
    JUNK_STATS = {"East", "West", "Central", "A.L.", "N.L."}
    JUNK_PLAYERS = {"Team | Roster"}
    if "statistic" in ev_sorted.columns:
        ev_sorted = ev_sorted[~ev_sorted["statistic"].isin(JUNK_STATS)]
    if "player" in ev_sorted.columns:
        ev_sorted = ev_sorted[~ev_sorted["player"].isin(JUNK_PLAYERS)]
        # Drop rows where player is a number (team win-total rows)
        ev_sorted = ev_sorted[~ev_sorted["player"].str.match(r"^\d+$", na=False)]
    # Drop rows with null/zero value that slipped through
    if "value" in ev_sorted.columns:
        ev_sorted = ev_sorted[ev_sorted["value"].notna() & (ev_sorted["value"] != 0)]

    ev_sorted = ev_sorted.head(200)

    def fmt_val(val):
        try:
            f = float(val)
            # Show as integer if it is a whole number (e.g. 44.0 -> 44)
            return str(int(f)) if f == int(f) else f"{f:.3f}"
        except (TypeError, ValueError):
            return str(val)

    # Render as styled HTML table
    rows_html = ""
    for _, r in ev_sorted.iterrows():
        league = str(r.get("league",""))
        league_cls = "AL" if league == "AL" else ("NL" if league == "NL" else "")
        val_str = fmt_val(r.get("value",""))
        rows_html += f"""
        <div class="ev-row">
            <span class="ev-year">{int(r['year']) if pd.notna(r['year']) else ''}</span>
            <span class="ev-league {league_cls}">{league}</span>
            <span>{r.get('statistic','')}</span>
            <span>{r.get('player', r.get('player_name',''))}</span>
            <span class="ev-val">{val_str}</span>
        </div>"""

    header = (
        '<div class="ev-row ev-header">'
        '<span>Year</span><span>League</span><span>Statistic</span>'
        '<span>Player</span><span style="text-align:right">Value</span>'
        '</div>'
    )
    full_html = (
        '<div style="border:1px solid #1e2d45; border-radius:8px; overflow:hidden;">'
        + header
        + rows_html
        + '</div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# RAW DATA EXPLORER
# -----------------------------------------------------------------------------

with st.expander("Raw Data Explorer", expanded=False):
    tab1, tab2 = st.tabs(["Players", "Events"])
    with tab1:
        st.dataframe(filtered.sort_values("year", ascending=False),
                     use_container_width=True, height=320)
    with tab2:
        st.dataframe(filtered_events.sort_values("year", ascending=False),
                     use_container_width=True, height=320)

st.markdown("""
<div style='text-align:center; color:#2a3a55; font-size:0.78rem; padding:1.2rem 0 0.5rem;
            font-family: "Barlow Condensed", sans-serif; letter-spacing:2px; text-transform:uppercase;'>
    MLB Historical Dashboard &nbsp;·&nbsp; Baseball Almanac &nbsp;·&nbsp; Streamlit + Plotly
</div>
""", unsafe_allow_html=True)