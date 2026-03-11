"""
MLB Capstone -- Program 2: Database Import
==========================================
Loads all CSV files from a given directory into a SQLite database.
Each CSV becomes a separate table. Column names and types are inferred
directly from the CSV -- no hardcoded schema.

Usage:
    python 2_db_import.py --data-dir ./data --db ./db/mlb.db
"""

import argparse
import os
import re
import sqlite3
import pandas as pd

# ── Domain constants (mirrors 1_scraper.py) ──────────────────────────────────

VALID_STATS = {
    "Batting Average", "Home Runs", "Runs Batted In", "RBI", "Hits",
    "Stolen Bases", "Strikeouts", "Earned Run Average", "ERA", "Wins",
    "Runs", "Doubles", "Triples", "Total Bases", "Slugging Average",
    "On Base Percentage", "Base on Balls", "Saves", "Complete Games",
    "Shutouts", "Games", "Winning Percentage", "Games Pitched",
    "Innings Pitched",
}

JUNK_STATS = {"East", "West", "Central", "A.L.", "N.L.",
              "American League", "National League"}

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
    "Oakland A's":                   "Athletics",
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


def _normalize_team(t):
    """Return canonical franchise name, or the original if not in map."""
    return TEAM_NORM.get(str(t).strip(), str(t).strip()) if pd.notna(t) else t


def _is_numeric_str(s):
    """Return True if string represents a number."""
    try:
        float(str(s).replace(",", ""))
        return True
    except (ValueError, TypeError):
        return False


# ── Table-specific cleaners ───────────────────────────────────────────────────

def clean_events_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove junk rows and normalize the events table."""
    before = len(df)

    # Drop rows missing key fields
    df = df.dropna(subset=["year", "statistic", "player"])

    # Keep only known real stat categories
    if "statistic" in df.columns:
        df = df[df["statistic"].isin(VALID_STATS)]

    # Drop division header / section label rows
    if "statistic" in df.columns:
        df = df[~df["statistic"].isin(JUNK_STATS)]

    # Drop rows where player is a bare number or known junk label
    if "player" in df.columns:
        df = df[~df["player"].astype(str).str.match(r"^\d+$", na=False)]
        df = df[~df["player"].isin(["Team | Roster", ""])]

    # Drop zero or non-numeric values
    if "value" in df.columns:
        df["value"] = pd.to_numeric(
            df["value"].astype(str).str.replace(",", ""), errors="coerce"
        )
        df = df[df["value"].notna() & (df["value"] != 0)]

    # Normalize team names
    if "team" in df.columns:
        df["team"] = df["team"].apply(_normalize_team)

    df = df.drop_duplicates()
    after = len(df)
    print(f"  [events] cleaned: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def clean_players_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove junk rows and normalize the players table."""
    before = len(df)

    # Drop rows missing key identity fields
    df = df.dropna(subset=["year", "player_name"])

    # Drop rows where player_name is a number or junk label
    if "player_name" in df.columns:
        df = df[~df["player_name"].astype(str).str.match(r"^\d+$", na=False)]
        df = df[~df["player_name"].isin(["Team | Roster", ""])]

    # Normalize team names
    if "team" in df.columns:
        df["team"] = df["team"].apply(_normalize_team)

    # Coerce all stat columns to numeric
    stat_cols = [c for c in df.columns
                 if c not in ("year", "league", "player_name", "team")]
    for col in stat_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates(subset=["year", "league", "player_name"])
    after = len(df)
    print(f"  [players] cleaned: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


TABLE_CLEANERS = {
    "events":  clean_events_df,
    "players": clean_players_df,
}


def infer_and_cast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Try to cast each column to a numeric type.
    Columns where all non-null values are whole numbers become INTEGER.
    Columns with decimals become REAL.
    Everything else stays TEXT.
    """
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        non_null_original  = df[col].notna().sum()
        non_null_converted = converted.notna().sum()

        # Only cast if at least some values converted successfully
        if non_null_converted == 0:
            continue

        # If conversion lost too many values it is probably a text column
        if non_null_converted < non_null_original * 0.5:
            continue

        # Whole numbers -> INTEGER, decimals -> REAL
        whole = (converted.dropna() % 1 == 0).all()
        if whole:
            df[col] = converted.astype("Int64")
        else:
            df[col] = converted

    return df


def sqlite_type(dtype) -> str:
    """Map a pandas dtype to a SQLite type affinity."""
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    return "TEXT"


def import_csv(conn: sqlite3.Connection, csv_path: str, table: str) -> int:
    """
    Read a CSV, cast numeric columns, create a matching table,
    insert all rows, and verify the count. Returns number of rows inserted.
    """
    df = pd.read_csv(csv_path, dtype=str)   # read everything as str first
    print(f"\n  [{table}] loaded {len(df)} rows | columns: {list(df.columns)}")

    # Apply table-specific cleaning before type inference
    if table in TABLE_CLEANERS:
        df = TABLE_CLEANERS[table](df)

    df = infer_and_cast(df)

    # Build DDL from actual dtypes
    col_defs  = [f'"{c}" {sqlite_type(df[c].dtype)}' for c in df.columns]
    create_sql = (
        f'CREATE TABLE IF NOT EXISTS "{table}" (\n    '
        + ",\n    ".join(col_defs)
        + "\n);"
    )

    conn.execute(f'DROP TABLE IF EXISTS "{table}";')
    print(f"  [{table}] DDL:\n{create_sql}")
    conn.execute(create_sql)

    df.to_sql(table, conn, if_exists="append", index=False)

    db_count = conn.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
    if db_count != len(df):
        raise ValueError(f"Row count mismatch: CSV={len(df)}, DB={db_count}")

    print(f"  [{table}] OK  {db_count} rows inserted and verified")
    return db_count


def build_indexes(conn: sqlite3.Connection):
    """Create indexes on common filter columns for any table that has them."""
    index_cols = {"year", "player", "player_name", "team", "statistic", "league", "award"}
    for (tbl,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{tbl}");')}
        for col in cols & index_cols:
            idx = f"idx_{tbl}_{col}"
            try:
                conn.execute(f'CREATE INDEX IF NOT EXISTS {idx} ON "{tbl}"("{col}");')
            except sqlite3.OperationalError as e:
                print(f"  [WARN] Index skipped ({tbl}.{col}): {e}")


def main():
    parser = argparse.ArgumentParser(description="MLB CSV -> SQLite Importer")
    parser.add_argument("--data-dir", required=True, help="Directory containing CSV files")
    parser.add_argument("--db",       required=True, help="Path to output SQLite database")
    args = parser.parse_args()

    # Validate data directory
    if not os.path.isdir(args.data_dir):
        print(f"[ERROR] Data directory not found: {args.data_dir}")
        raise SystemExit(1)

    # Find all CSVs
    all_csvs = sorted(f for f in os.listdir(args.data_dir) if f.endswith(".csv"))
    if not all_csvs:
        print(f"[ERROR] No CSV files found in {args.data_dir}")
        raise SystemExit(1)

    # Ensure required files are present
    for required in ("events.csv", "players.csv"):
        if required not in all_csvs:
            print(f"[ERROR] Required file missing: {required}")
            raise SystemExit(1)

    # Create output directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode = WAL;")

    total_rows = 0
    errors     = []

    for csv_file in all_csvs:
        table = csv_file[:-4]   # strip .csv
        path  = os.path.join(args.data_dir, csv_file)
        try:
            total_rows += import_csv(conn, path, table)
        except Exception as e:
            errors.append((table, str(e)))
            print(f"  [ERROR] {table}: {e}")

    print("\n  Building indexes...")
    build_indexes(conn)
    conn.commit()

    # Summary
    print("\n" + "=" * 50)
    print(f"[OK] Database saved to: {args.db}")
    print(f"     Total rows imported : {total_rows}")
    print(f"     Tables created      : {len(all_csvs) - len(errors)}")
    if errors:
        print(f"     Errors              : {len(errors)}")
        for t, msg in errors:
            print(f"       - {t}: {msg}")
    print("=" * 50)

    print("\nDatabase tables:")
    for (tbl,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall():
        count = conn.execute(f'SELECT COUNT(*) FROM "{tbl}";').fetchone()[0]
        cols  = [r[1] for r in conn.execute(f'PRAGMA table_info("{tbl}");')]
        print(f"  {tbl:<14} {count:>5} rows  |  {', '.join(cols)}")

    conn.close()


if __name__ == "__main__":
    main()