# ⚾ MLB Historical Dashboard — Capstone Project

A complete data pipeline that scrapes MLB historical data, stores it in SQLite, supports command-line querying, and presents an interactive dashboard built with Streamlit and Plotly.

---

## 📸 Dashboard Preview

![MLB Dashboard](https://i.imgur.com/placeholder-screenshot.png)

> *Dark stadium-green theme with 5 interactive visualizations, sidebar filters, and a historical events timeline.*

---

## 🗂️ Project Structure

```
mlb_capstone/
├── 1_scraper.py        # Program 1 — Selenium web scraper
├── 2_db_import.py      # Program 2 — CSV → SQLite importer
├── 3_query.py          # Program 3 — Interactive CLI query tool
├── 4_dashboard.py      # Program 4 — Streamlit dashboard
├── data/               # Output CSVs (generated)
│   ├── events.csv
│   ├── players.csv
│   ├── teams.csv
│   └── awards.csv
├── db/
│   └── mlb.db          # SQLite database (generated)
├── requirements.txt
└── README.md
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- Google Chrome + matching [ChromeDriver](https://chromedriver.chromium.org/) (for live scraping only)

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔄 Running the Full Pipeline

### Step 1 — Scrape Data

**Live scrape** (requires Selenium + ChromeDriver):
```bash
python 1_scraper.py --start 2000 --end 2023
```

**Offline seed data** (no browser needed):
```bash
python 1_scraper.py --seed
```

Outputs: `data/events.csv`, `data/players.csv`, `data/teams.csv`, `data/awards.csv`

---

### Step 2 — Import to Database

```bash
python 2_db_import.py
```

Automatically runs `1_scraper.py --seed` if CSVs are missing.

Outputs: `db/mlb.db`

---

### Step 3 — Query the Database

**Interactive menu:**
```bash
python 3_query.py
```

**Named preset queries:**
```bash
python 3_query.py --query top_hr
python 3_query.py --query mvp_stats
python 3_query.py --query team_success
python 3_query.py --list-queries        # show all available queries
```

**Filter by year, player, or award:**
```bash
python 3_query.py --year 2001
python 3_query.py --player "Bonds"
python 3_query.py --award MVP
```

**Raw SQL:**
```bash
python 3_query.py --sql "SELECT player_name, home_runs FROM players ORDER BY home_runs DESC LIMIT 10;"
```

**Available named queries:**

| Query            | Description                                              |
|------------------|----------------------------------------------------------|
| `top_hr`         | Top 20 single-season home run totals                     |
| `mvp_stats`      | MVP winners joined with their season stats               |
| `cy_young_stats` | Cy Young winners with season stats                       |
| `events_with_awards` | Historical events joined with awards by year         |
| `team_success`   | Teams ranked by World Series titles + award winners      |
| `best_avg`       | Top 20 single-season batting averages                    |
| `best_war`       | Top 20 single-season WAR                                 |
| `player_awards`  | Most decorated players (multi-award winners)             |
| `yankees_history`| All Yankees players with full stats                      |
| `decade_summary` | Average stats grouped by decade                          |

---

### Step 4 — Launch the Dashboard

```bash
streamlit run 4_dashboard.py
```

Opens at `http://localhost:8501`

**Dashboard features:**
- 5 interactive visualizations:
  1. **Peak HR & RBI over time** — line chart with record-year markers
  2. **Batting average distribution** — histogram with mean line
  3. **Stat vs Stat scatter** — configurable axes, color-coded by league/team
  4. **World Series titles** — horizontal bar chart
  5. **Stats by decade** — grouped bar + WAR line (dual axis)
- **Sidebar filters:** year range slider, league selector, team multi-select, award filter, custom scatter axes
- **Historical events timeline** — filtered by selected year range
- **KPI metrics row** — player seasons, HR record, best BA, best WAR, awards count
- **Raw data explorer** — tabbed view of all four tables

---

## ☁️ Deployment (Streamlit Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `4_dashboard.py`
5. Click **Deploy**

> **Note:** The dashboard auto-runs the pipeline with seed data on first deployment.

---

## 🗃️ Database Schema

```sql
CREATE TABLE events (
    year   INTEGER,
    date   TEXT,
    event  TEXT
);

CREATE TABLE players (
    year         INTEGER,
    player_name  TEXT,
    team         TEXT,
    position     TEXT,
    home_runs    INTEGER,
    rbi          INTEGER,
    batting_avg  REAL,
    war          REAL
);

CREATE TABLE teams (
    team                 TEXT,
    league               TEXT,
    world_series_titles  INTEGER,
    city                 TEXT
);

CREATE TABLE awards (
    year         INTEGER,
    player_name  TEXT,
    team         TEXT,
    league       TEXT,
    award        TEXT
);
```

---

## 🧹 Data Cleaning

Each CSV goes through cleaning before database import:
- Null rows dropped on key fields (`year`, `player_name`, `event`)
- Duplicates removed on meaningful composite keys
- Numeric columns cast using `pd.to_numeric(errors='coerce')`
- Integer years stored as `Int64` (nullable) in pandas, `INTEGER` in SQLite
- String fields `.strip()`-ped of whitespace

---

## 📚 Technologies Used

| Tool           | Purpose                        |
|----------------|--------------------------------|
| Selenium       | Browser automation / scraping  |
| Pandas         | Data loading, cleaning, transforms |
| SQLite3        | Relational data storage        |
| Streamlit      | Dashboard framework            |
| Plotly         | Interactive visualizations     |

---

## 📝 Notes

- Live scraping targets [Baseball Almanac](https://www.baseball-almanac.com) yearly review pages
- A `--seed` flag is provided for offline / demo use with 100+ rows of curated historical data
- `User-Agent` spoofing and polite random delays (1.5–3s) are built into the scraper to avoid rate limiting
