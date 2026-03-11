# Program 3 - Database Query CLI
# Interactive command-line tool for exploring the mlb.db database.
# Includes preset queries with JOINs and free-form SQL input.
#
# Usage:
#   python 3_query.py                         # interactive menu
#   python 3_query.py --query top_hr          # run a preset
#   python 3_query.py --year 2001             # filter by year
#   python 3_query.py --player "Bonds"        # search by player
#   python 3_query.py --statistic "Home Runs" # search events by stat
#   python 3_query.py --sql "SELECT ..."      # raw SQL
#   python 3_query.py --list-queries          # show all presets

import argparse
import os
import sqlite3
import textwrap

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "mlb.db")

QUERIES = {

    "top_hr": {
        "desc": "Top 20 single-season home run totals",
        "sql": """
            SELECT year, player_name, team, league, home_runs, batting_avg
            FROM players
            WHERE home_runs IS NOT NULL
            ORDER BY CAST(home_runs AS REAL) DESC
            LIMIT 20;
        """,
    },

    "top_avg": {
        "desc": "Top 20 single-season batting averages",
        "sql": """
            SELECT year, player_name, team, league, batting_avg, home_runs
            FROM players
            WHERE batting_avg IS NOT NULL
            ORDER BY CAST(batting_avg AS REAL) DESC
            LIMIT 20;
        """,
    },

    "hr_by_league": {
        "desc": "Average home runs per season by league (JOIN: players x events)",
        "sql": """
            SELECT p.league,
                   p.year,
                   ROUND(AVG(CAST(p.home_runs AS REAL)), 2) AS avg_hr,
                   COUNT(DISTINCT p.player_name) AS players,
                   COUNT(DISTINCT e.statistic)   AS event_types
            FROM players p
            JOIN events e ON p.year = e.year AND p.league = e.league
            WHERE p.home_runs IS NOT NULL
            GROUP BY p.league, p.year
            ORDER BY p.year, p.league;
        """,
    },

    "stat_leaders_by_year": {
        "desc": "All stat leaders for a given year with player stats (JOIN: events x players)",
        "sql": """
            SELECT e.year, e.league, e.statistic, e.player, e.team, e.value,
                   p.home_runs, p.batting_avg
            FROM events e
            LEFT JOIN players p ON e.player = p.player_name AND e.year = p.year
            ORDER BY e.year DESC, e.league, e.statistic
            LIMIT 50;
        """,
    },

    "team_stat_leaders": {
        "desc": "Teams with the most stat leader appearances (JOIN: events x players)",
        "sql": """
            SELECT e.team,
                   e.league,
                   COUNT(*) AS leader_appearances,
                   COUNT(DISTINCT e.statistic) AS unique_stats,
                   COUNT(DISTINCT e.player) AS unique_players,
                   ROUND(AVG(CAST(p.home_runs AS REAL)), 1) AS avg_hr
            FROM events e
            LEFT JOIN players p ON e.player = p.player_name AND e.year = p.year
            GROUP BY e.team
            ORDER BY leader_appearances DESC
            LIMIT 20;
        """,
    },

    "player_dominance": {
        "desc": "Players who led the most stat categories (JOIN: events x players)",
        "sql": """
            SELECT e.player,
                   e.team,
                   e.league,
                   COUNT(*) AS times_led,
                   COUNT(DISTINCT e.statistic) AS categories,
                   MIN(e.year) AS first_year,
                   MAX(e.year) AS last_year,
                   p.home_runs,
                   p.batting_avg
            FROM events e
            LEFT JOIN players p ON e.player = p.player_name AND e.year = p.year
            GROUP BY e.player
            HAVING COUNT(*) >= 2
            ORDER BY times_led DESC
            LIMIT 20;
        """,
    },

    "decade_summary": {
        "desc": "Average offensive stats grouped by decade",
        "sql": """
            SELECT (CAST(year AS INTEGER) / 10) * 10 AS decade,
                   COUNT(*) AS player_seasons,
                   ROUND(AVG(CAST(home_runs AS REAL)), 1) AS avg_hr,
                   ROUND(AVG(CAST(batting_avg AS REAL)), 3) AS avg_ba
            FROM players
            WHERE year IS NOT NULL
            GROUP BY decade
            ORDER BY decade;
        """,
    },

    "events_by_year": {
        "desc": "All stat leaders from the events table, most recent first",
        "sql": """
            SELECT year, league, statistic, player, team, value
            FROM events
            ORDER BY year DESC, league, statistic
            LIMIT 50;
        """,
    },

    "al_vs_nl_hr": {
        "desc": "AL vs NL home run leader comparison per year (self-JOIN on players)",
        "sql": """
            SELECT al.year,
                   al.player_name AS al_leader, al.team AS al_team, al.home_runs AS al_hr,
                   nl.player_name AS nl_leader, nl.team AS nl_team, nl.home_runs AS nl_hr
            FROM players al
            JOIN players nl ON al.year = nl.year AND al.league = 'AL' AND nl.league = 'NL'
            WHERE al.home_runs = (
                SELECT MAX(CAST(home_runs AS REAL)) FROM players
                WHERE year = al.year AND league = 'AL'
            )
            AND nl.home_runs = (
                SELECT MAX(CAST(home_runs AS REAL)) FROM players
                WHERE year = nl.year AND league = 'NL'
            )
            ORDER BY al.year DESC;
        """,
    },

    "top_hitters_per_team": {
        "desc": "Best batting average ever recorded per team",
        "sql": """
            SELECT p.team, p.league, p.player_name, p.year,
                   p.batting_avg, p.home_runs
            FROM players p
            WHERE p.batting_avg = (
                SELECT MAX(CAST(batting_avg AS REAL))
                FROM players
                WHERE team = p.team
            )
            AND p.batting_avg IS NOT NULL
            ORDER BY p.league, p.team;
        """,
    },
}


def print_table(rows, headers, max_col=28):
    if not rows:
        print("  (no results)")
        return
    widths = [
        min(max_col, max(len(str(h)), max(len(str(r[i] or "")) for r in rows)))
        for i, h in enumerate(headers)
    ]
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"
    print(sep)
    print(fmt.format(*[str(h)[:max_col] for h in headers]))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v or "")[:max_col] for v in row]))
    print(sep)
    print(f"  {len(rows)} row(s)\n")


def run_query(conn, sql, params=()):
    sql = textwrap.dedent(sql).strip()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description] if cur.description else []
        return headers, rows
    except sqlite3.OperationalError as e:
        print(f"\nSQL error: {e}")
        print(f"Query was:\n{sql}\n")
        return [], []


def build_year_query(year):
    sql = """
        SELECT p.year, p.player_name, p.team, p.league,
               p.home_runs, p.batting_avg,
               e.statistic, e.value
        FROM players p
        LEFT JOIN events e ON e.year = p.year
            AND e.player = p.player_name
            AND e.league = p.league
        WHERE p.year = ?
        ORDER BY CAST(p.home_runs AS REAL) DESC;
    """
    return sql, (year,)


def build_player_query(name):
    sql = """
        SELECT p.year, p.player_name, p.team, p.league,
               p.home_runs, p.batting_avg,
               GROUP_CONCAT(DISTINCT e.statistic) AS categories_led
        FROM players p
        LEFT JOIN events e ON e.player = p.player_name AND e.year = p.year
        WHERE p.player_name LIKE ?
        GROUP BY p.year, p.player_name
        ORDER BY p.year;
    """
    return sql, (f"%{name}%",)


def build_statistic_query(statistic):
    sql = """
        SELECT e.year, e.league, e.statistic, e.player, e.team, e.value,
               p.home_runs, p.batting_avg
        FROM events e
        LEFT JOIN players p ON e.player = p.player_name AND e.year = p.year
        WHERE e.statistic LIKE ?
        ORDER BY e.year DESC;
    """
    return sql, (f"%{statistic}%",)


def show_menu():
    print("\n" + "=" * 58)
    print("   MLB Historical Database - Query Tool")
    print("=" * 58)
    print("  Pick a number to run a preset, or:")
    print("  [s] custom SQL   [y] by year   [p] by player")
    print("  [a] by statistic   [m] menu   [q] quit")
    print("-" * 58)
    items = list(QUERIES.items())
    for i, (key, meta) in enumerate(items, 1):
        print(f"  {i:>2}. {key:<22} {meta['desc']}")
    print("-" * 58)
    return items


def interactive(conn):
    items = show_menu()

    while True:
        try:
            choice = input("\n> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if choice == "q":
            print("Bye!")
            break
        elif choice == "m":
            items = show_menu()
        elif choice == "s":
            sql = input("SQL> ").strip()
            if sql:
                h, r = run_query(conn, sql)
                if h:
                    print_table(r, h)
        elif choice == "y":
            try:
                year = int(input("Year: ").strip())
                h, r = run_query(conn, *build_year_query(year))
                print_table(r, h)
            except ValueError:
                print("  Enter a valid year.")
        elif choice == "p":
            name = input("Player name (partial ok): ").strip()
            h, r = run_query(conn, *build_player_query(name))
            print_table(r, h)
        elif choice == "a":
            stat = input("Statistic (e.g. Home Runs, ERA): ").strip()
            h, r = run_query(conn, *build_statistic_query(stat))
            print_table(r, h)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                key, meta = items[idx]
                print(f"\n  {meta['desc']}")
                h, r = run_query(conn, meta["sql"])
                print_table(r, h)
            else:
                print("  Invalid number.")
        else:
            print("  Type a number, or s / y / p / a / q.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",           default=DB_PATH)
    parser.add_argument("--query",        help="run a named preset query")
    parser.add_argument("--sql",          help="run raw SQL")
    parser.add_argument("--year",         type=int)
    parser.add_argument("--player",       help="filter by player name")
    parser.add_argument("--statistic",    help="filter by statistic name")
    parser.add_argument("--list-queries", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        print(f"Run: python 2_db_import.py --data-dir ./data --db {args.db}")
        raise SystemExit(1)

    if args.list_queries:
        for key, meta in QUERIES.items():
            print(f"  {key:<22} {meta['desc']}")
        return

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        if args.query:
            q = QUERIES.get(args.query)
            if not q:
                print(f"Unknown query '{args.query}'. Use --list-queries to see options.")
            else:
                h, r = run_query(conn, q["sql"])
                print_table(r, h)
        elif args.sql:
            h, r = run_query(conn, args.sql)
            print_table(r, h)
        elif args.year:
            h, r = run_query(conn, *build_year_query(args.year))
            print_table(r, h)
        elif args.player:
            h, r = run_query(conn, *build_player_query(args.player))
            print_table(r, h)
        elif args.statistic:
            h, r = run_query(conn, *build_statistic_query(args.statistic))
            print_table(r, h)
        else:
            interactive(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()