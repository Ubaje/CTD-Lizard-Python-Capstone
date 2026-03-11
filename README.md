# MLB Historical Dashboard

This is my Lesson 14 capstone project. It scrapes historical MLB stat leader data from Baseball Almanac, stores it in a SQLite database, and displays it in an interactive Streamlit dashboard. There are four separate programs that need to be run in order.

---

## Setup

You'll need Python 3.10+ and Google Chrome installed. Make sure your ChromeDriver version matches your Chrome version — you can download it at [chromedriver.chromium.org](https://chromedriver.chromium.org/).

```bash
pip install -r requirements.txt
```

---

## How to run it

The four programs build on each other, so run them in order.

### 1. Scrape the data

```bash
python 1_scraper.py
python 1_scraper.py --start 2010 --end 2023   # optional: pick a year range
```

This opens a headless Chrome browser and scrapes the AL and NL yearly review pages from Baseball Almanac for each season. It saves two files:

- `data/events.csv` — one row per stat leader (long format)
- `data/players.csv` — one row per player per year (pivoted)

The scraper filters out junk rows like division headers and team win totals, normalizes franchise names so "Anaheim Angels" and "Los Angeles Angels" both show up as "Angels", and retries automatically if there's a connection error.

### 2. Import to the database

```bash
python 2_db_import.py --data-dir ./data --db ./db/mlb.db
```

Loads the CSVs into SQLite. Each CSV becomes its own table. Column types are inferred from the data so there's no hardcoded schema. It also runs another round of cleaning as a safety net in case anything slipped through the scraper.

### 3. Query the database

```bash
python 3_query.py              # opens the interactive menu
python 3_query.py --query top_hr
python 3_query.py --year 2015
python 3_query.py --player "Trout"
python 3_query.py --statistic "Home Runs"
python 3_query.py --sql "SELECT * FROM events WHERE year = 2001;"
python 3_query.py --list-queries
```

The interactive menu lets you pick from 10 preset queries or type your own SQL. Most presets use JOINs between the `events` and `players` tables. In the menu, type a number to run a preset, `s` for custom SQL, `y`/`p`/`a` to filter by year/player/stat, or `q` to quit.

Preset queries:

| Name | What it shows |
|---|---|
| `top_hr` | Top 20 home run seasons |
| `top_avg` | Top 20 batting average seasons |
| `hr_by_league` | Average HR per season by league (JOIN) |
| `stat_leaders_by_year` | All stat leaders for each year (JOIN) |
| `team_stat_leaders` | Which teams show up most in the leaders table (JOIN) |
| `player_dominance` | Players who led the most categories (JOIN) |
| `decade_summary` | Average stats grouped by decade |
| `events_by_year` | Raw events table sorted by year |
| `al_vs_nl_hr` | AL vs NL HR leader each year, side by side (self-JOIN) |
| `top_hitters_per_team` | Best batting average ever for each franchise |

### 4. Launch the dashboard

```bash
streamlit run 4_dashboard.py
```

Opens at `http://localhost:8501`. There are 5 charts:

- **Peak HR per Season** — line chart of the highest HR total each year
- **Batting Average Distribution** — histogram with a mean line
- **Player Dominance Heatmap** — shows which players led which stat categories, color-coded by how dominant they were relative to other leaders in that stat
- **Stat Leader Appearances by Team** — horizontal bar showing which franchises dominate the leaders table
- **Stats by Decade** — compare any two stats averaged by decade (pick them in the sidebar)

The sidebar has filters for season range, league, and teams. The decade chart has its own dropdowns to pick which two stats to compare — the bar stat and line stat can't be the same. The stat category dropdown at the bottom only affects the Stat Leaders table, not the charts.


## Project structure

```
mlb_capstone/
├── 1_scraper.py       # Selenium scraper
├── 2_db_import.py     # CSV to SQLite importer
├── 3_query.py         # CLI query tool
├── 4_dashboard.py     # Streamlit dashboard
├── data/
│   ├── events.csv     # scraped stat leaders (long format)
│   └── players.csv    # one row per player per year
├── db/
│   └── mlb.db         # SQLite database
├── requirements.txt
└── README.md
```

---

## Data cleaning

Cleaning happens twice — once in the scraper and again in the importer. This way the data is clean even if someone edits the CSVs manually before importing.

The main things being cleaned:
- Division headers and section labels (things like "East", "A.L.", "Hitting Leaders") get filtered out
- Rows where the player is just a number or says "Team | Roster" get dropped
- Only known stat categories are kept (home runs, ERA, etc.) — anything else is structural noise from the page
- All historical franchise name variants get normalized to one name (e.g. "Cleveland Indians" → "Guardians")
- Numeric columns are type-cast properly so SQLite stores them as INTEGER or REAL

---

## Database tables

The schema is inferred from the CSV, but this is what it usually looks like:

**events** — one row per stat leader entry
```
year        INTEGER
league      TEXT
statistic   TEXT
player      TEXT
team        TEXT
value       REAL
```

**players** — one row per player per year (pivoted from events)
```
year          INTEGER
league        TEXT
player_name   TEXT
team          TEXT
batting_avg   REAL
home_runs     REAL
hits          REAL
stolen_bases  REAL
era           REAL
wins          REAL
so            REAL
```

---

## Tools used

- **Selenium** — browser automation for scraping
- **Pandas** — data cleaning and transformation
- **SQLite** — local database storage
- **Streamlit** — dashboard framework
- **Plotly** — interactive charts