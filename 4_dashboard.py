# Program 4 - Streamlit Dashboard
# Loads data from mlb.db and shows 5 interactive charts.
# Run with: streamlit run 4_dashboard.py

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

# Page styling - dark navy theme with red accent

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

    /* ── Chart descriptions ── */
    .chart-desc {
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 300;
        line-height: 1.5;
        margin: -0.4rem 0 0.8rem;
    }
    .chart-desc b { color: #8ab8c8; font-weight: 500; }

    /* ── Sidebar section labels ── */
    .sb-section {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 800;
        font-size: 0.7rem;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: var(--red);
        margin: 0.8rem 0 0.2rem;
    }
    .sb-desc {
        font-size: 0.75rem;
        color: var(--muted);
        line-height: 1.4;
        margin-bottom: 0.6rem;
    }
    .sb-affects {
        font-size: 0.72rem;
        color: #4a7a8a;
        font-style: italic;
        margin: 0.1rem 0 0.8rem;
    }

    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Maps event statistic names to column names used in the players table
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

    # Pivot events into one wide row per player so we can merge with players table
        ev = events.copy()
    ev["col"] = ev["statistic"].map(STAT_TO_COL)
    ev = ev[ev["col"].notna()]

    ev_wide = ev.pivot_table(
        index=["year", "league", "player", "team"],
        columns="col",
        values="value",
        aggfunc="first",
    ).reset_index()
    ev_wide.columns.name = None
    ev_wide = ev_wide.rename(columns={"player": "player_name"})

    # Merge both tables - outer join so we keep all rows, fill gaps from each side
    merge_keys = ["year", "league", "player_name", "team"]
    merge_keys = [k for k in merge_keys if k in players.columns and k in ev_wide.columns]

    merged = players.merge(ev_wide, on=merge_keys, how="outer", suffixes=("", "_ev"))

    for col in ev_wide.columns:
        if col in merge_keys:
            continue
        ev_col = col + "_ev"
        if col in merged.columns and ev_col in merged.columns:
            merged[col] = merged[col].fillna(merged[ev_col])
            merged.drop(columns=[ev_col], inplace=True)
        elif ev_col in merged.columns:
            merged.rename(columns={ev_col: col}, inplace=True)

    stat_cols = [c for c in merged.columns if c not in merge_keys + ["decade"]]
    for col in stat_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged["decade"] = ((merged["year"] // 10) * 10).astype("Int64")

    return merged, events


players_df, events_df = load_data()

# Shared Plotly layout settings so all charts look consistent

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

# Sidebar filters

with st.sidebar:
    st.markdown('<div class="sidebar-logo">MLB<span>.</span>DATA</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="sb-section">GLOBAL FILTERS</div>
    <div class="sb-desc">Apply to every chart and table on the page.</div>
    """, unsafe_allow_html=True)

    all_years  = sorted(players_df["year"].dropna().unique().astype(int))
    year_range = st.slider("Season Range",
                           min_value=min(all_years), max_value=max(all_years),
                           value=(min(all_years), max(all_years)))
    st.markdown('<div class="sb-affects">↳ All charts · KPI strip · Stat Leaders table</div>', unsafe_allow_html=True)

    leagues_available = sorted(players_df["league"].dropna().unique()) if "league" in players_df.columns else []
    sel_league = st.selectbox("League", ["Both"] + leagues_available)
    st.markdown('<div class="sb-affects">↳ All charts · Stat Leaders table</div>', unsafe_allow_html=True)

    available_canonical = sorted(players_df["team"].dropna().unique())
    sel_canonical = st.multiselect("Teams", available_canonical)
    sel_teams = sel_canonical
    st.markdown('<div class="sb-affects">↳ HR Trend · BA Distribution · Heatmap · Decade Summary</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Decade chart controls
    st.markdown("""
    <div class="sb-section">DECADE CHART</div>
    <div class="sb-desc">Choose which two stats to compare by decade.
    Bars use the left axis, line uses the right axis.</div>
    """, unsafe_allow_html=True)

    decade_stat_options = [
        "home_runs", "batting_avg", "hits", "rbi", "runs", "doubles",
        "triples", "stolen_bases", "total_bases", "obp", "slg", "bb",
        "era", "wins", "so", "saves", "cg", "sho", "win_pct", "games",
    ]
    decade_stat_options = [c for c in decade_stat_options
                           if c in players_df.columns and players_df[c].notna().any()]

    STAT_LABELS = {
        "home_runs": "Home Runs", "batting_avg": "Batting Average",
        "hits": "Hits", "rbi": "RBI", "runs": "Runs",
        "doubles": "Doubles", "triples": "Triples",
        "stolen_bases": "Stolen Bases", "total_bases": "Total Bases",
        "obp": "On-Base %", "slg": "Slugging %", "bb": "Walks",
        "era": "ERA", "wins": "Wins", "so": "Strikeouts",
        "saves": "Saves", "cg": "Complete Games", "sho": "Shutouts",
        "win_pct": "Win %", "games": "Games",
    }
    decade_bar_stat = st.selectbox(
        "Bar stat (left axis)",
        decade_stat_options,
        index=0,
        format_func=lambda c: STAT_LABELS.get(c, c),
    )

    # Don't let the user pick the same stat for both axes
    line_stat_options = [c for c in decade_stat_options if c != decade_bar_stat]
    decade_line_stat = st.selectbox(
        "Line stat (right axis)",
        line_stat_options,
        index=0,
        format_func=lambda c: STAT_LABELS.get(c, c),
    )
    st.markdown('<div class="sb-affects">↳ Stats by Decade chart only</div>', unsafe_allow_html=True)

    st.markdown("---")

    #Stat Leaders filter
    st.markdown("""
    <div class="sb-section">STAT LEADERS TABLE</div>
    <div class="sb-desc">Narrows the leaders table to one stat category.
    Does not affect any charts.</div>
    """, unsafe_allow_html=True)

    all_stats = sorted(events_df["statistic"].dropna().unique()) if "statistic" in events_df.columns else []
    sel_stat  = st.selectbox("Stat Category", ["All"] + list(all_stats))
    st.markdown('<div class="sb-affects">↳ Stat Leaders table only</div>', unsafe_allow_html=True)

# Apply sidebar filters to both dataframes

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

# Page header

st.markdown(f"""
<div class="site-header">
    <div>
        <div class="badge">Season Analysis</div>
        <h1>MLB <span>Historical</span> Dashboard</h1>
        <p>Baseball Almanac data &nbsp;·&nbsp; {year_range[0]}–{year_range[1]} &nbsp;·&nbsp; {len(filtered):,} player seasons</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Top-level stats strip

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

# Chart row 1: HR trend and BA distribution

st.markdown('<div class="sec-head"><span class="dot"></span>Offensive Trends</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-desc">The peak single-season home run total and batting average distribution across all league leaders in the selected year range and filters.</p>', unsafe_allow_html=True)
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

# Chart row 2: Player dominance heatmap

st.markdown('<div class="sec-head"><span class="dot"></span>Player Dominance Heatmap</div>', unsafe_allow_html=True)
st.markdown("<p class=\"chart-desc\">Each cell shows a player's best recorded value for a stat category across the selected season range. Only players who led in <b>2+ categories</b> are shown. Darker red = higher value relative to that stat's range. Hover for exact values.</p>", unsafe_allow_html=True)

# Build wide pivot: one row per player, one col per stat category
hm_ev = filtered_events.copy()
hm_ev["col"] = hm_ev["statistic"].map(STAT_TO_COL)
hm_ev = hm_ev[hm_ev["col"].notna()]

if hm_ev.empty:
    st.info("No data for heatmap with selected filters.")
else:
    hm_wide = hm_ev.pivot_table(
        index="player",
        columns="col",
        values="value",
        aggfunc="max",
    )
    hm_wide.index.name = "player"

    # Only keep players who led in at least 2 categories
    hm_wide = hm_wide[hm_wide.notna().sum(axis=1) >= 2]

    # Sort players by how many categories they led (most dominant first)
    hm_wide = hm_wide.loc[hm_wide.notna().sum(axis=1).sort_values(ascending=False).index]

    # Cap at top 30 players so the chart stays readable
    hm_wide = hm_wide.head(30)

    # Normalize each column 0–1 for coloring (so HR scale doesn't dwarf BA)
    hm_norm = hm_wide.copy()
    for col in hm_norm.columns:
        col_min = hm_norm[col].min()
        col_max = hm_norm[col].max()
        if col_max > col_min:
            hm_norm[col] = (hm_norm[col] - col_min) / (col_max - col_min)
        else:
            hm_norm[col] = 0.5

    # Friendly column labels (stat col name -> display name)
    COL_DISPLAY = {v: k for k, v in STAT_TO_COL.items()}
    display_cols = [COL_DISPLAY.get(c, c).replace("_", " ").title() for c in hm_norm.columns]

    # Build custom hover text showing actual values
    hover_text = []
    for player in hm_wide.index:
        row_hover = []
        for col in hm_wide.columns:
            val = hm_wide.loc[player, col]
            display_name = COL_DISPLAY.get(col, col)
            if pd.notna(val):
                fmt = f"{val:.3f}" if val < 10 else str(int(val))
                row_hover.append(f"{display_name}: {fmt}")
            else:
                row_hover.append("")
        hover_text.append(row_hover)

    fig_hm = go.Figure(go.Heatmap(
        z=hm_norm.values,
        x=display_cols,
        y=list(hm_wide.index),
        text=hover_text,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        colorscale=[
            [0.0,  "#0b0f1a"],
            [0.25, "#1a2d45"],
            [0.5,  "#1a4a6e"],
            [0.75, "#e63946"],
            [1.0,  "#f4a261"],
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text="Relative<br>Value", font=dict(color="#6b7a99", size=11)),
            tickfont=dict(color="#6b7a99"),
            bgcolor="#111827",
            bordercolor="#1e2d45",
            thickness=12,
        ),
        xgap=2,
        ygap=2,
    ))

    hm_height = max(380, len(hm_wide) * 22 + 80)
    fig_hm.update_layout(
        **{k: v for k, v in PL.items() if k not in ("xaxis", "yaxis", "margin")},
        title=f"Player × Stat Category Dominance  ({len(hm_wide)} players)",
        xaxis=dict(side="bottom", tickangle=-35, tickfont=dict(color="#9aa3b8", size=11),
                   gridcolor="#1e2d45"),
        yaxis=dict(autorange="reversed", tickfont=dict(color="#e8eaf0", size=11),
                   gridcolor="#1e2d45"),
        height=hm_height,
        margin=dict(t=50, b=100, l=140, r=60),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

# Chart row 3: Stats by decade

st.markdown('<div class="sec-head"><span class="dot"></span>Stats by Decade</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-desc">Average stat values among league leaders grouped by decade. Choose any two stats in the sidebar — bars on the left axis, line on the right. Shows how production has shifted over time.</p>', unsafe_allow_html=True)

bar_col  = decade_bar_stat  if decade_bar_stat  in filtered.columns else None
line_col = decade_line_stat if decade_line_stat in filtered.columns else None

valid_decade_cols = [c for c in [bar_col, line_col] if c is not None]
decade_stats = (
    filtered.groupby("decade")[valid_decade_cols]
    .mean().round(3).reset_index().dropna(subset=["decade"])
) if valid_decade_cols else pd.DataFrame()
decade_stats["decade_label"] = decade_stats["decade"].astype(str) + "s"

bar_label  = STAT_LABELS.get(bar_col,  bar_col  or "")
line_label = STAT_LABELS.get(line_col, line_col or "")

if not decade_stats.empty:
    fig5 = go.Figure()

    if bar_col and bar_col in decade_stats.columns:
        # Detect whether bar stat is a decimal (avg/rate) or integer (count)
        is_bar_decimal = decade_stats[bar_col].max() < 10
        bar_fmt = ".3f" if is_bar_decimal else ".1f"
        fig5.add_trace(go.Bar(
            x=decade_stats["decade_label"], y=decade_stats[bar_col],
            name=f"Avg {bar_label}", marker_color=RED, opacity=0.85,
            hovertemplate=f"Decade: %{{x}}<br>Avg {bar_label}: %{{y:{bar_fmt}}}<extra></extra>",
        ))

    if line_col and line_col in decade_stats.columns:
        is_line_decimal = decade_stats[line_col].max() < 10
        line_fmt = ".3f" if is_line_decimal else ".1f"
        fig5.add_trace(go.Scatter(
            x=decade_stats["decade_label"], y=decade_stats[line_col],
            name=f"Avg {line_label}", mode="lines+markers",
            line=dict(color=TEAL, width=2.5),
            marker=dict(size=7, color=TEAL),
            yaxis="y2",
            hovertemplate=f"Decade: %{{x}}<br>Avg {line_label}: %{{y:{line_fmt}}}<extra></extra>",
        ))

    fig5.update_layout(
        **{k: v for k, v in PL.items() if k != "yaxis"},
        title=f"Avg {bar_label} (bars) and Avg {line_label} (line) by Decade",
        barmode="group",
        height=320,
        yaxis=dict(title=f"Avg {bar_label}", gridcolor="#1e2d45",
                   zerolinecolor="#1e2d45", tickfont=dict(color="#6b7a99")),
        yaxis2=dict(title=f"Avg {line_label}", overlaying="y", side="right",
                    tickfont=dict(color=TEAL), showgrid=False),
    )
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("Not enough data to show decade summary.")

# Stat leaders table

st.markdown('<div class="sec-head"><span class="dot"></span>Stat Leaders</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-desc">Every league leader entry from the scraped events table. Use the <b>Stat Category</b> filter in the sidebar to narrow to one stat. Use <b>Season Range</b> and <b>League</b> to further refine.</p>', unsafe_allow_html=True)

if filtered_events.empty:
    st.info("No stat leader data for selected filters.")
else:
    show_cols = [c for c in ["year","league","statistic","player","team","value"]
                 if c in filtered_events.columns]
    ev_sorted = filtered_events[show_cols].sort_values("year", ascending=False)

    # Filter out any junk rows that slipped through cleaning
    JUNK_STATS = {"East", "West", "Central", "A.L.", "N.L."}
    JUNK_PLAYERS = {"Team | Roster"}
    if "statistic" in ev_sorted.columns:
        ev_sorted = ev_sorted[~ev_sorted["statistic"].isin(JUNK_STATS)]
    if "player" in ev_sorted.columns:
        ev_sorted = ev_sorted[~ev_sorted["player"].isin(JUNK_PLAYERS)]
        ev_sorted = ev_sorted[~ev_sorted["player"].str.match(r"^\d+$", na=False)]
    if "value" in ev_sorted.columns:
        ev_sorted = ev_sorted[ev_sorted["value"].notna() & (ev_sorted["value"] != 0)]

    ev_sorted = ev_sorted.head(200)

    def fmt_val(val):
        try:
            f = float(val)
            return str(int(f)) if f == int(f) else f"{f:.3f}"
        except (TypeError, ValueError):
            return str(val)

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

# Raw data explorer at the bottom of the page

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