"""CLI entry point for data_fetch package."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .sqlite_store import SQLiteStore

from .updater import DataUpdater, UpdateConfig, run_full_update, run_incremental_update
from .cache_health import check_health

DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "sqlite", "stock_data.db"
)


def main():
    parser = argparse.ArgumentParser(
        description="A-share quantitative data update tool"
    )
    subparsers = parser.add_subparsers(dest="command")

    # update subcommand
    update_parser = subparsers.add_parser("update", help="Data update")
    update_parser.add_argument(
        "--full", action="store_true", help="Full update"
    )
    update_parser.add_argument(
        "--incremental", action="store_true", help="Incremental update"
    )
    update_parser.add_argument(
        "--financial", action="store_true", help="Financial data only"
    )
    update_parser.add_argument(
        "--constituents", action="store_true", help="Index constituents only"
    )
    update_parser.add_argument(
        "--pool",
        choices=["all_a", "hs300", "zz500"],
        default="all_a",
        help="Stock pool",
    )
    update_parser.add_argument(
        "--source",
        choices=["baostock", "akshare"],
        default="baostock",
        help="Data source",
    )
    update_parser.add_argument("--db", default=DB_PATH, help="DB path")

    # health subcommand
    health_parser = subparsers.add_parser("health", help="Health check")
    health_parser.add_argument("--db", default=DB_PATH, help="DB path")

    # init subcommand
    subparsers.add_parser("init", help="Initialize database")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s: %(message)s"
    )

    if args.command == "init":
        store = SQLiteStore(args.db)
        store.init_schema()
        print(f"Database initialized: {args.db}")

    elif args.command == "update":
        if args.incremental:
            run_incremental_update(args.db)
        elif args.full:
            run_full_update(args.db)
        elif args.financial:
            store = SQLiteStore(args.db)
            store.init_schema()
            updater = DataUpdater(
                store, UpdateConfig(source=args.source, pool=args.pool)
            )
            updater.update_financial_data()
        elif args.constituents:
            store = SQLiteStore(args.db)
            store.init_schema()
            updater = DataUpdater(
                store, UpdateConfig(source=args.source, pool=args.pool)
            )
            updater.update_constituents()
        else:
            # Default: incremental
            run_incremental_update(args.db)

    elif args.command == "health":
        check_health(args.db)


if __name__ == "__main__":
    main()
