"""
MLB Capstone — Program 3: Database Query CLI
============================================
Interactive command-line tool for querying the mlb.db database.
Supports preset queries (with JOINs) and free-form SQL.

Usage:
    python 3_query.py                        # interactive menu
    python 3_query.py --query "top_hr"       # run named query
    python 3_query.py --sql "SELECT ..."     # raw SQL
    python 3_query.py --year 2001            # filter by year
    python 3_query.py --player "Bonds"       # filter by player
    python 3_query.py --award "MVP"          # filter by award
    python 3_query.py --list-queries         # show all named queries
"""

import argparse
import os
import sqlite3
import sys
import textwrap

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "mlb.db")

# ─────────────────────────────────────────────────────────────────────────────
# NAMED QUERIES (all use JOINs where applicable)
# ─────────────────────────────────────────────────────────────────────────────

NAMED_QUERIES = {

    "top_hr": {
        "desc": "Top 20 single-season home run totals",
        "sql": """
            SELECT year, player_name, team, league, home_runs, batting_avg
            FROM   players
            WHERE  home_runs IS NOT NULL
            ORDER  BY CAST(home_runs AS REAL) DESC
            LIMIT  20;
        """,
    },

    "top_avg": {
        "desc": "Top 20 single-season batting averages",
        "sql": """
            SELECT year, player_name, team, league, batting_avg, home_runs
            FROM   players
            WHERE  batting_avg IS NOT NULL
            ORDER  BY CAST(batting_avg AS REAL) DESC
            LIMIT  20;
        """,
    },

    "hr_by_league": {
        "desc": "Average home runs per season grouped by league (JOIN: players x events)",
        "sql": """
            SELECT p.league,
                   p.year,
                   ROUND(AVG(CAST(p.home_runs AS REAL)), 2) AS avg_hr,
                   COUNT(DISTINCT p.player_name)            AS players,
                   COUNT(DISTINCT e.statistic)              AS event_types
            FROM   players p
            JOIN   events  e ON p.year = e.year AND p.league = e.league
            WHERE  p.home_runs IS NOT NULL
            GROUP  BY p.league, p.year
            ORDER  BY p.year, p.league;
        """,
    },

    "stat_leaders_by_year": {
        "desc": "All stat leaders for a given year (JOIN: events x players)",
        "sql": """
            SELECT e.year, e.league, e.statistic, e.player, e.team, e.value,
                   p.home_runs, p.batting_avg
            FROM   events  e
            LEFT JOIN players p
                   ON e.player = p.player_name AND e.year = p.year
            ORDER  BY e.year DESC, e.league, e.statistic
            LIMIT  50;
        """,
    },

    "team_stat_leaders": {
        "desc": "Teams with the most stat leader appearances (JOIN: events x players)",
        "sql": """
            SELECT e.team,
                   e.league,
                   COUNT(*)                            AS leader_appearances,
                   COUNT(DISTINCT e.statistic)         AS unique_stats_led,
                   COUNT(DISTINCT e.player)            AS unique_players,
                   ROUND(AVG(CAST(p.home_runs AS REAL)), 1) AS avg_hr
            FROM   events  e
            LEFT JOIN players p
                   ON e.player = p.player_name AND e.year = p.year
            GROUP  BY e.team
            ORDER  BY leader_appearances DESC
            LIMIT  20;
        """,
    },

    "player_dominance": {
        "desc": "Players who led the most statistical categories (JOIN: events x players)",
        "sql": """
            SELECT e.player,
                   e.team,
                   e.league,
                   COUNT(*)                    AS times_led_category,
                   COUNT(DISTINCT e.statistic) AS categories_led,
                   MIN(e.year)                 AS first_year,
                   MAX(e.year)                 AS last_year,
                   p.home_runs,
                   p.batting_avg
            FROM   events e
            LEFT JOIN players p
                   ON e.player = p.player_name AND e.year = p.year
            GROUP  BY e.player
            HAVING COUNT(*) >= 2
            ORDER  BY times_led_category DESC
            LIMIT  20;
        """,
    },

    "decade_summary": {
        "desc": "Average offensive stats grouped by decade",
        "sql": """
            SELECT (CAST(year AS INTEGER) / 10) * 10  AS decade,
                   COUNT(*)                           AS player_seasons,
                   ROUND(AVG(CAST(home_runs   AS REAL)), 1) AS avg_hr,
                   ROUND(AVG(CAST(batting_avg AS REAL)), 3) AS avg_ba
            FROM   players
            WHERE  year IS NOT NULL
            GROUP  BY decade
            ORDER  BY decade;
        """,
    },

    "events_by_year": {
        "desc": "All stat leaders for a specific year from the events table",
        "sql": """
            SELECT year, league, statistic, player, team, value
            FROM   events
            ORDER  BY year DESC, league, statistic
            LIMIT  50;
        """,
    },

    "al_vs_nl_hr": {
        "desc": "AL vs NL home run leader comparison by year (self-JOIN on players)",
        "sql": """
            SELECT al.year,
                   al.player_name AS al_leader, al.team AS al_team, al.home_runs AS al_hr,
                   nl.player_name AS nl_leader, nl.team AS nl_team, nl.home_runs AS nl_hr
            FROM   players al
            JOIN   players nl
                   ON al.year = nl.year AND al.league = 'AL' AND nl.league = 'NL'
            WHERE  al.home_runs = (
                       SELECT MAX(CAST(home_runs AS REAL)) FROM players
                       WHERE year = al.year AND league = 'AL'
                   )
              AND  nl.home_runs = (
                       SELECT MAX(CAST(home_runs AS REAL)) FROM players
                       WHERE year = nl.year AND league = 'NL'
                   )
            ORDER  BY al.year DESC;
        """,
    },

    "top_hitters_per_team": {
        "desc": "Best batting average per team across all years",
        "sql": """
            SELECT p.team, p.league, p.player_name, p.year,
                   p.batting_avg, p.home_runs
            FROM   players p
            WHERE  p.batting_avg = (
                       SELECT MAX(CAST(batting_avg AS REAL))
                       FROM   players
                       WHERE  team = p.team
                   )
              AND  p.batting_avg IS NOT NULL
            ORDER  BY p.league, p.team;
        """,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def print_table(rows, headers, max_col=28):
    """Pretty-print query results as a fixed-width table."""
    if not rows:
        print("  (no results)")
        return

    widths = [min(max_col, max(len(str(h)), max(len(str(r[i] or "")) for r in rows)))
              for i, h in enumerate(headers)]

    sep  = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt  = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"

    print(sep)
    print(fmt.format(*[str(h)[:max_col] for h in headers]))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v or "")[:max_col] for v in row]))
    print(sep)
    print(f"  {len(rows)} row(s) returned.\n")


def run_query(conn: sqlite3.Connection, sql: str, params=()):
    """Execute SQL and return (headers, rows) or raise on error."""
    sql = textwrap.dedent(sql).strip()
    try:
        cursor = conn.execute(sql, params)
        rows    = cursor.fetchall()
        headers = [d[0] for d in cursor.description] if cursor.description else []
        return headers, rows
    except sqlite3.OperationalError as e:
        print(f"\n[SQL ERROR] {e}")
        print(f"  Query was:\n{sql}\n")
        return [], []


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC FILTER BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_year_query(year: int) -> tuple:
    sql = """
        SELECT p.year, p.player_name, p.team, p.league,
               p.home_runs, p.batting_avg,
               e.statistic, e.value
        FROM   players p
        LEFT JOIN events e
               ON e.year = p.year AND e.player = p.player_name AND e.league = p.league
        WHERE  p.year = ?
        ORDER  BY CAST(p.home_runs AS REAL) DESC;
    """
    return sql, (year,)


def build_player_query(name: str) -> tuple:
    sql = """
        SELECT p.year, p.player_name, p.team, p.league,
               p.home_runs, p.batting_avg,
               GROUP_CONCAT(DISTINCT e.statistic) AS categories_led
        FROM   players p
        LEFT JOIN events e
               ON e.player = p.player_name AND e.year = p.year
        WHERE  p.player_name LIKE ?
        GROUP  BY p.year, p.player_name
        ORDER  BY p.year;
    """
    return sql, (f"%{name}%",)


def build_statistic_query(statistic: str) -> tuple:
    """Search events table by statistic name (replaces award filter)."""
    sql = """
        SELECT e.year, e.league, e.statistic, e.player, e.team, e.value,
               p.home_runs, p.batting_avg
        FROM   events e
        LEFT JOIN players p
               ON e.player = p.player_name AND e.year = p.year
        WHERE  e.statistic LIKE ?
        ORDER  BY e.year DESC;
    """
    return sql, (f"%{statistic}%",)


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE MENU
# ─────────────────────────────────────────────────────────────────────────────

def interactive_menu(conn: sqlite3.Connection):
    """Run an interactive REPL for querying the database."""
    print("\n" + "="*60)
    print("   MLB Historical Database — Interactive Query Tool")
    print("="*60)
    print("  Type a number to run a preset query, or choose:")
    print("  [s] Custom SQL   [y] Filter by year   [p] Filter by player")
    print("  [a] Filter by statistic   [m] Reprint menu   [q] Quit")
    print("-"*60)

    menu_items = list(NAMED_QUERIES.items())
    for i, (key, meta) in enumerate(menu_items, 1):
        print(f"  {i:>2}. {key:<20}  {meta['desc']}")
    print("-"*60)

    while True:
        try:
            choice = input("\nEnter choice: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if choice == "q":
            print("Goodbye!")
            break

        elif choice == "m":
            interactive_menu(conn)
            break

        elif choice == "s":
            sql = input("SQL> ").strip()
            if sql:
                headers, rows = run_query(conn, sql)
                if headers:
                    print_table(rows, headers)

        elif choice == "y":
            year = input("Year: ").strip()
            try:
                sql, params = build_year_query(int(year))
                headers, rows = run_query(conn, sql, params)
                print_table(rows, headers)
            except ValueError:
                print("  Please enter a valid year number.")

        elif choice == "p":
            name = input("Player name (partial OK): ").strip()
            sql, params = build_player_query(name)
            headers, rows = run_query(conn, sql, params)
            print_table(rows, headers)

        elif choice == "a":
            stat = input("Statistic name (e.g. Home Runs, Batting Average, Strikeouts): ").strip()
            sql, params = build_statistic_query(stat)
            headers, rows = run_query(conn, sql, params)
            print_table(rows, headers)

        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(menu_items):
                key, meta = menu_items[idx]
                print(f"\n  Running: {meta['desc']}")
                headers, rows = run_query(conn, meta["sql"])
                print_table(rows, headers)
            else:
                print("  Invalid selection.")

        else:
            print("  Unrecognized input. Try a number, or s/y/p/a/q.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MLB Database Query CLI")
    parser.add_argument("--db",           default=DB_PATH, help="Path to mlb.db")
    parser.add_argument("--query",        help="Run a named preset query")
    parser.add_argument("--sql",          help="Run a raw SQL statement")
    parser.add_argument("--year",         type=int, help="Filter results by year")
    parser.add_argument("--player",       help="Filter results by player name")
    parser.add_argument("--statistic",    help="Filter results by statistic name (e.g. 'Home Runs')")
    parser.add_argument("--list-queries", action="store_true",
                        help="Print all available named queries and exit")
    args = parser.parse_args()

    # ── Ensure DB exists ──────────────────────────────────────────────────────
    if not os.path.exists(args.db):
        print(f"[ERROR] Database not found at {args.db}.")
        print(f"        Run: python 2_db_import.py --data-dir ./data --db {args.db}")
        raise SystemExit(1)

    if args.list_queries:
        print("\nAvailable named queries:")
        for key, meta in NAMED_QUERIES.items():
            print(f"  {key:<20}  {meta['desc']}")
        return

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        if args.query:
            q = NAMED_QUERIES.get(args.query)
            if not q:
                print(f"[ERROR] Unknown query '{args.query}'. Use --list-queries.")
            else:
                headers, rows = run_query(conn, q["sql"])
                print_table(rows, headers)

        elif args.sql:
            headers, rows = run_query(conn, args.sql)
            print_table(rows, headers)

        elif args.year:
            sql, params = build_year_query(args.year)
            headers, rows = run_query(conn, sql, params)
            print_table(rows, headers)

        elif args.player:
            sql, params = build_player_query(args.player)
            headers, rows = run_query(conn, sql, params)
            print_table(rows, headers)

        elif args.statistic:
            sql, params = build_statistic_query(args.statistic)
            headers, rows = run_query(conn, sql, params)
            print_table(rows, headers)

        else:
            interactive_menu(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()