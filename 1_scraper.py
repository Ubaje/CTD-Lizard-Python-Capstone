# Program 1 - Web Scraper
# Scrapes yearly AL/NL stat leader pages from Baseball Almanac
# and saves them as events.csv and players.csv
#
# Usage:
#   python 1_scraper.py
#   python 1_scraper.py --start 2010 --end 2023

import argparse
import os
import random
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

URL_AL = "https://www.baseball-almanac.com/yearly/yr{year}a.shtml"
URL_NL = "https://www.baseball-almanac.com/yearly/yr{year}n.shtml"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

VALID_STATS = {
    "Batting Average", "Home Runs", "Runs Batted In", "RBI", "Hits",
    "Stolen Bases", "Strikeouts", "Earned Run Average", "ERA", "Wins",
    "Runs", "Doubles", "Triples", "Total Bases", "Slugging Average",
    "On Base Percentage", "Base on Balls", "Saves", "Complete Games",
    "Shutouts", "Games", "Winning Percentage", "Games Pitched",
    "Innings Pitched",
}

TEAM_NORM = {
    "California Angels":              "Angels",
    "Anaheim Angels":                 "Angels",
    "Los Angeles Angels of Anaheim":  "Angels",
    "Los Angeles Angels":             "Angels",
    "Houston Colt .45s":              "Astros",
    "Houston Astros":                 "Astros",
    "Philadelphia Athletics":         "Athletics",
    "Kansas City Athletics":          "Athletics",
    "Oakland Athletics":              "Athletics",
    "Oakland A's":                    "Athletics",
    "Boston Braves":                  "Braves",
    "Milwaukee Braves":               "Braves",
    "Atlanta Braves":                 "Braves",
    "Seattle Pilots":                 "Brewers",
    "Milwaukee Brewers":              "Brewers",
    "St. Louis Cardinals":            "Cardinals",
    "Chicago Cubs":                   "Cubs",
    "Arizona Diamondbacks":           "Diamondbacks",
    "Brooklyn Dodgers":               "Dodgers",
    "Los Angeles Dodgers":            "Dodgers",
    "New York Giants":                "Giants",
    "San Francisco Giants":           "Giants",
    "Cleveland Blues":                "Guardians",
    "Cleveland Naps":                 "Guardians",
    "Cleveland Indians":              "Guardians",
    "Cleveland Guardians":            "Guardians",
    "Florida Marlins":                "Marlins",
    "Miami Marlins":                  "Marlins",
    "New York Mets":                  "Mets",
    "Montreal Expos":                 "Nationals",
    "Washington Nationals":           "Nationals",
    "St. Louis Browns":               "Orioles",
    "Baltimore Orioles":              "Orioles",
    "San Diego Padres":               "Padres",
    "Philadelphia Phillies":          "Phillies",
    "Pittsburgh Pirates":             "Pirates",
    "Washington Senators":            "Rangers",
    "Texas Rangers":                  "Rangers",
    "Tampa Bay Devil Rays":           "Rays",
    "Tampa Bay Rays":                 "Rays",
    "Boston Red Sox":                 "Red Sox",
    "Colorado Rockies":               "Rockies",
    "Kansas City Royals":             "Royals",
    "Detroit Tigers":                 "Tigers",
    "Minnesota Twins":                "Twins",
    "Chicago White Sox":              "White Sox",
    "New York Yankees":               "Yankees",
    "Seattle Mariners":               "Mariners",
    "Toronto Blue Jays":              "Blue Jays",
}


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def scrape_page(driver, url, year, league, retries=3):
    """Load one page and pull out all the stat rows. Retries on network errors."""
    for attempt in range(1, retries + 1):
        try:
            print(f"  [{league}] {year}" + (f" (attempt {attempt})" if attempt > 1 else ""))
            driver.get(url)
            time.sleep(random.uniform(2.0, 4.0))
            break
        except WebDriverException as e:
            msg = e.msg.splitlines()[0] if e.msg else str(e)
            print(f"    warning: {msg}")
            if attempt == retries:
                print(f"    giving up on {url}")
                return []
            wait = 5 * attempt
            print(f"    waiting {wait}s...")
            time.sleep(wait)

    records = []
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            for row in table.find_elements(By.TAG_NAME, "tr"):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 4:
                    continue

                statistic = cells[0].text.strip()
                player    = cells[1].text.strip()
                team      = cells[2].text.strip()
                value     = cells[3].text.strip()

                if not statistic or not player or not value:
                    continue
                if statistic.lower() in ("statistic", "stat", "category"):
                    continue
                if any(x in statistic for x in ["<-", "->", "Review", "Hitting", "Pitching"]):
                    continue
                if statistic in ("East", "West", "Central", "A.L.", "N.L.",
                                 "American League", "National League"):
                    continue
                if player.isdigit() or player == "Team | Roster":
                    continue

                try:
                    fval = float(value.replace(",", ""))
                except ValueError:
                    continue
                if fval == 0:
                    continue

                records.append({
                    "year":      year,
                    "league":    league,
                    "statistic": statistic,
                    "player":    player,
                    "team":      team,
                    "value":     value,
                })

    except (NoSuchElementException, TimeoutException) as e:
        print(f"    parse error on {url}: {e}")

    print(f"    {len(records)} rows found")
    return records


def scrape_year(driver, year):
    records = []
    for league, url_tpl in [("AL", URL_AL), ("NL", URL_NL)]:
        records.extend(scrape_page(driver, url_tpl.format(year=year), year, league))
        time.sleep(random.uniform(1.5, 3.0))
    return records


def reshape_to_players(df):
    """Pivot the long events table into one wide row per player per year."""
    df["statistic"] = (
        df["statistic"]
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    keep = {
        "batting_average":    "batting_avg",
        "home_runs":          "home_runs",
        "runs_batted_in":     "rbi",
        "hits":               "hits",
        "stolen_bases":       "stolen_bases",
        "strikeouts":         "so",
        "earned_run_average": "era",
        "wins":               "wins",
    }

    df = df[df["statistic"].isin(keep)].copy()
    df["statistic"] = df["statistic"].map(keep)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    pivoted = df.pivot_table(
        index=["year", "league", "player", "team"],
        columns="statistic",
        values="value",
        aggfunc="first",
    ).reset_index()

    pivoted.columns.name = None
    pivoted = pivoted.rename(columns={"player": "player_name"})
    return pivoted


def clean_events(df):
    print(f"  events before cleaning: {len(df)} rows")
    df = df.dropna(subset=["year", "player", "statistic"])
    df = df[df["statistic"].isin(VALID_STATS)]
    df = df[~df["player"].str.match(r"^\d+$", na=False)]
    df = df[~df["player"].isin(["Team | Roster", ""])]
    df["team"] = df["team"].map(lambda t: TEAM_NORM.get(t, t))
    df["value"] = pd.to_numeric(df["value"].astype(str).str.replace(",", ""), errors="coerce")
    df = df[df["value"].notna() & (df["value"] != 0)]
    df = df.drop_duplicates()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.sort_values(["year", "league", "statistic"]).reset_index(drop=True)
    print(f"  events after cleaning:  {len(df)} rows")
    return df


def clean_players(df):
    print(f"  players before cleaning: {len(df)} rows")
    df = df.dropna(subset=["year", "player_name"])
    df["team"] = df["team"].map(lambda t: TEAM_NORM.get(t, t))
    df = df.drop_duplicates(subset=["year", "league", "player_name"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.sort_values(["year", "player_name"]).reset_index(drop=True)
    print(f"  players after cleaning:  {len(df)} rows")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2000)
    parser.add_argument("--end",   type=int, default=2023)
    args = parser.parse_args()

    print(f"Scraping {args.start} to {args.end}...")
    driver = build_driver()
    all_records = []

    try:
        for year in range(args.start, args.end + 1):
            all_records.extend(scrape_year(driver, year))
    finally:
        driver.quit()

    if not all_records:
        print("No data scraped. Check your internet connection and ChromeDriver.")
        return

    raw = pd.DataFrame(all_records)

    events_df = clean_events(raw.copy())
    events_df.to_csv(f"{DATA_DIR}/events.csv", index=False)

    players_df = clean_players(reshape_to_players(raw))
    players_df.to_csv(f"{DATA_DIR}/players.csv", index=False)

    print(f"\nDone. Saved to ./data/")
    print(f"  events.csv  -> {len(events_df)} rows")
    print(f"  players.csv -> {len(players_df)} rows")
    print()
    print(players_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()