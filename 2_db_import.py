# Program 2 - Database Import
# Reads events.csv and players.csv and loads them into a SQLite database.
# Each CSV becomes its own table. Column types are inferred from the data.
#
# Usage:
#   python 2_db_import.py --data-dir ./data --db ./db/mlb.db

import argparse
import os
import sqlite3
import pandas as pd

VALID_STATS = {
    "Batting Average", "Home Runs", "Runs Batted In", "RBI", "Hits",
    "Stolen Bases", "Strikeouts", "Earned Run Average", "ERA", "Wins",
    "Runs", "Doubles", "Triples", "Total Bases", "Slugging Average",
    "On Base Percentage", "Base on Balls", "Saves", "Complete Games",
    "Shutouts", "Games", "Winning Percentage", "Games Pitched",
    "Innings Pitched",
}

JUNK_STATS = {
    "East", "West", "Central", "A.L.", "N.L.",
    "American League", "National League",
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


def normalize_team(t):
    if pd.isna(t):
        return t
    return TEAM_NORM.get(str(t).strip(), str(t).strip())


def clean_events_df(df):
    before = len(df)
    df = df.dropna(subset=["year", "statistic", "player"])
    df = df[df["statistic"].isin(VALID_STATS)]
    df = df[~df["statistic"].isin(JUNK_STATS)]
    df = df[~df["player"].astype(str).str.match(r"^\d+$", na=False)]
    df = df[~df["player"].isin(["Team | Roster", ""])]
    if "value" in df.columns:
        df["value"] = pd.to_numeric(
            df["value"].astype(str).str.replace(",", ""), errors="coerce"
        )
        df = df[df["value"].notna() & (df["value"] != 0)]
    if "team" in df.columns:
        df["team"] = df["team"].apply(normalize_team)
    df = df.drop_duplicates()
    print(f"  events:  {before} -> {len(df)} rows ({before - len(df)} removed)")
    return df.reset_index(drop=True)


def clean_players_df(df):
    before = len(df)
    df = df.dropna(subset=["year", "player_name"])
    df = df[~df["player_name"].astype(str).str.match(r"^\d+$", na=False)]
    df = df[~df["player_name"].isin(["Team | Roster", ""])]
    if "team" in df.columns:
        df["team"] = df["team"].apply(normalize_team)
    # coerce all stat columns to numeric
    id_cols = {"year", "league", "player_name", "team"}
    for col in df.columns:
        if col not in id_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates(subset=["year", "league", "player_name"])
    print(f"  players: {before} -> {len(df)} rows ({before - len(df)} removed)")
    return df.reset_index(drop=True)

TABLE_CLEANERS = {
    "events":  clean_events_df,
    "players": clean_players_df,
}


def infer_and_cast(df):
    """Try to cast each column to a sensible numeric type."""
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        n_orig = df[col].notna().sum()
        n_conv = converted.notna().sum()
        if n_conv == 0 or n_conv < n_orig * 0.5:
            continue  # mostly text, leave it alone
        if (converted.dropna() % 1 == 0).all():
            df[col] = converted.astype("Int64")
        else:
            df[col] = converted
    return df


def sqlite_type(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    return "TEXT"


def import_csv(conn, csv_path, table):
    df = pd.read_csv(csv_path, dtype=str)
    print(f"\n[{table}] loaded {len(df)} rows, columns: {list(df.columns)}")

    if table in TABLE_CLEANERS:
        df = TABLE_CLEANERS[table](df)

    df = infer_and_cast(df)

    col_defs = [f'"{c}" {sqlite_type(df[c].dtype)}' for c in df.columns]
    create_sql = (
        f'CREATE TABLE IF NOT EXISTS "{table}" (\n    '
        + ",\n    ".join(col_defs)
        + "\n);"
    )

    conn.execute(f'DROP TABLE IF EXISTS "{table}";')
    conn.execute(create_sql)
    df.to_sql(table, conn, if_exists="append", index=False)

    count = conn.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
    if count != len(df):
        raise ValueError(f"Row count mismatch for {table}: expected {len(df)}, got {count}")

    print(f"  {count} rows inserted ok")
    return count


def build_indexes(conn):
    """Add indexes on the columns we filter and join on most often."""
    index_cols = {"year", "player", "player_name", "team", "statistic", "league"}
    for (tbl,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table';"):
        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{tbl}");')}
        for col in cols & index_cols:
            try:
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS idx_{tbl}_{col} ON "{tbl}"("{col}");'
                )
            except sqlite3.OperationalError:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="folder with CSV files")
    parser.add_argument("--db",       required=True, help="output SQLite file path")
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"Error: data directory not found: {args.data_dir}")
        raise SystemExit(1)

    csvs = sorted(f for f in os.listdir(args.data_dir) if f.endswith(".csv"))
    if not csvs:
        print(f"Error: no CSV files found in {args.data_dir}")
        raise SystemExit(1)

    for required in ("events.csv", "players.csv"):
        if required not in csvs:
            print(f"Error: required file missing: {required}")
            raise SystemExit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode = WAL;")

    total = 0
    errors = []
    for csv_file in csvs:
        table = csv_file[:-4]
        path  = os.path.join(args.data_dir, csv_file)
        try:
            total += import_csv(conn, path, table)
        except Exception as e:
            errors.append((table, str(e)))
            print(f"  error on {table}: {e}")

    print("\nBuilding indexes...")
    build_indexes(conn)
    conn.commit()

    print(f"\nDatabase saved to {args.db}")
    print(f"  {total} total rows across {len(csvs) - len(errors)} tables")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for t, msg in errors:
            print(f"  {t}: {msg}")

    print("\nTables:")
    for (tbl,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table';"):
        count = conn.execute(f'SELECT COUNT(*) FROM "{tbl}";').fetchone()[0]
        cols  = [r[1] for r in conn.execute(f'PRAGMA table_info("{tbl}");')]
        print(f"  {tbl:<14} {count:>5} rows  |  {', '.join(cols)}")

    conn.close()


if __name__ == "__main__":
    main()