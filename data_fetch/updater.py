"""Data update scheduler: full + incremental update."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Literal

import baostock as bs
import pandas as pd

from .db_schema import SCHEMA_STOCK_TABLES, create_all_stock_tables
from .sqlite_store import SQLiteStore
from .daily_kline import fetch_daily_kline_baostock, KLINE_FIELDS
from .financial_data import fetch_financial_qtr
from .index_constituents import INDEX_MAP, fetch_historical_constituents

logger = logging.getLogger(__name__)


@dataclass
class UpdateConfig:
    """Update configuration."""
    source: str = "baostock"  # 'baostock' | 'akshare'
    pool: Literal["all_a", "hs300", "zz500"] = "all_a"
    start_date: str = "2026-05-01"  # First A-share listing date
    end_date: str | None = None
    update_constituents: bool = True
    index_keys: list[str] = field(default_factory=lambda: list(INDEX_MAP.keys()))
    update_financial: bool = True
    progress_interval: int = 100  # Log every N stocks


class DataUpdater:
    """Unified data update scheduler: full + incremental + health check."""

    def __init__(self, db_store: SQLiteStore, config: UpdateConfig | None = None):
        self.store = db_store
        self.config = config or UpdateConfig()

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    def _get_stock_list(self) -> pd.DataFrame:
        """Get all A-share stock list from baostock."""
        lg = bs.login()
        try:
            rs = bs.query_stock_basic()
            df_list = []
            while (rs.error_code == "0") and rs.next():
                df_list.append(rs.get_row_data())
            df = pd.DataFrame(df_list, columns=rs.fields)
        finally:
            bs.logout()
        return df

    def update_stock_info(self, force_full: bool = False) -> int:
        """Update stock_info table. Returns number of records inserted/updated."""
        df = self._get_stock_list()
        if df.empty:
            logger.warning("Stock list is empty.")
            return 0

        required_cols = [
            "code", "code_name", "ipoDate", "outDate", "exchange",
        ]
        available = [c for c in required_cols if c in df.columns]
        for c in required_cols:
            if c not in df.columns:
                df[c] = None

        df_out = df[available].rename(columns={
            "code": "code",
            "code_name": "name",
            "ipoDate": "listed_date",
            "outDate": "delisted_date",
            "exchange": "exchange",
        })

        # Ensure all expected columns exist even if source fields are missing
        for col in ["code", "name", "industry", "listed_date", "delisted_date", "exchange", "board", "updated_at"]:
            if col not in df_out.columns:
                df_out[col] = None

        # Clean exchange: add board info
        df_out["exchange"] = df_out["exchange"].replace({
            "SH": "SSE", "SZ": "SZSE",
        })
        # Infer board from exchange
        df_out["board"] = None
        # SSE: Main; SZSE: Main for codes < 300, ChiNext for >= 300
        def _infer_board(row):
            if row.get("exchange") == "SZSE":
                code_num = int(str(row.get("code", "0"))[:2]) if row.get("code") and str(row.get("code", "0"))[:2].isdigit() else 0
                return "ChiNext" if code_num >= 30 else "Main"
            return "Main"
        df_out["board"] = df_out.apply(_infer_board, axis=1)

        mask = (~df_out["delisted_date"].isin(["--", ""])) | df_out["delisted_date"].isna()
        df_out.loc[~mask, "delisted_date"] = None

        df_out["updated_at"] = datetime.datetime.now().isoformat()

        # Only write columns that exist in stock_info schema
        target_cols = [c for c in [
            "code", "name", "industry", "listed_date",
            "delisted_date", "exchange", "board", "updated_at",
        ] if c in df_out.columns]

        records = df_out[target_cols].to_dict("records")
        n = self.store.upsert("stock_info", records)
        logger.info("stock_info updated: %d records", n)
        return n

    def update_daily_kline(
        self,
        codes: list[str] | None = None,
        partial: bool = True,
    ) -> int:
        """Update daily kline data.

        Args:
            codes: Stock codes to update. None = all active stocks.
            partial: True = incremental (only new dates), False = full re-fetch.
        """
        if codes is None:
            df_info = self.store.query_df(
                "SELECT code FROM stock_info WHERE delisted_date IS NULL"
            )
            codes = df_info["code"].tolist() if not df_info.empty else []

        if not codes:
            logger.warning("No stocks to update.")
            return 0

        end_date = self.config.end_date or self._today()
        n_updated = 0
        fail_count = 0

        for i, code in enumerate(codes):
            if i % self.config.progress_interval == 0:
                pct = (i + 1) / len(codes) * 100
                logger.info(
                    "Kline progress: %.1f%% (%d/%d) updated=%d failed=%d",
                    pct, i + 1, len(codes), n_updated, fail_count,
                )

            try:
                start_date = self.config.start_date
                if partial:
                    latest = self.store.get_latest_date("daily_kline", code)
                    if latest:
                        latest_dt = datetime.datetime.strptime(latest, "%Y-%m-%d")
                        start_date = (
                            latest_dt + datetime.timedelta(days=1)
                        ).strftime("%Y-%m-%d")

                if start_date >= end_date:
                    continue

                df = fetch_daily_kline_baostock(code, start_date, end_date)
                if df.empty:
                    continue

                required_cols = [c for c in KLINE_FIELDS if c in df.columns]
                records = df[required_cols].to_dict("records")
                n_updated += len(records)
                self.store.upsert("daily_kline", records)
            except Exception as e:
                fail_count += 1
                if fail_count <= 10:
                    logger.warning("Failed to fetch kline for %s: %s", code, e)

        logger.info(
            "Kline update done: updated=%d failed=%d", n_updated, fail_count
        )
        return n_updated

    def update_financial_data(self) -> int:
        """Update quarterly financial data."""
        df_info = self.store.query_df(
            "SELECT code FROM stock_info WHERE delisted_date IS NULL"
        )
        codes = df_info["code"].tolist() if not df_info.empty else []

        end_date = self.config.end_date or self._today()
        start_year = "2005"

        n_updated = 0
        fail_count = 0

        for i, code in enumerate(codes):
            if i % self.config.progress_interval == 0:
                logger.info(
                    "Financial progress: %d/%d updated=%d failed=%d",
                    i + 1, len(codes), n_updated, fail_count,
                )

            try:
                # Filter codes that don't have a valid start for profit_data
                # baostock's query_profit_data needs a valid code format
                df = fetch_financial_qtr(code, start_year, end_date)
                if df.empty:
                    continue

                records = df.to_dict("records")
                # Filter out records where all financial fields are None
                clean_records = []
                for rec in records:
                    if any(v is not None for v in rec.values()):
                        clean_records.append(rec)
                if clean_records:
                    n_updated += len(clean_records)
                    self.store.upsert("financial_qtr", clean_records)
            except Exception as e:
                fail_count += 1
                if fail_count <= 5:
                    logger.warning("Failed to fetch financial for %s: %s", code, e)

        logger.info(
            "Financial update done: updated=%d failed=%d", n_updated, fail_count
        )
        return n_updated

    def update_constituents(self) -> int:
        """Update index constituents history."""
        if not self.config.update_constituents:
            return 0

        n_total = 0
        for index_key in self.config.index_keys:
            logger.info("Updating constituents for index: %s", index_key)
            df = fetch_historical_constituents(
                index_key,
                "2005-01-01",
                self._today(),
            )
            if not df.empty:
                n_total += len(df)
                self.store.upsert("index_constituents", df.to_dict("records"))

        logger.info("Constituents update done: %d records", n_total)
        return n_total

    def update_full(self) -> dict:
        """Execute full data update."""
        logger.info("=" * 50)
        logger.info("Starting full data update")
        logger.info("=" * 50)

        stats = {}

        logger.info("[1/4] Stock list...")
        stats["stock_info"] = self.update_stock_info()

        logger.info("[2/4] Daily kline...")
        stats["daily_kline"] = self.update_daily_kline(partial=False)

        logger.info("[3/4] Financial data...")
        stats["financial"] = (
            self.update_financial_data() if self.config.update_financial else 0
        )

        logger.info("[4/4] Index constituents...")
        stats["constituents"] = self.update_constituents()

        logger.info("Full update complete.")
        return stats

    def update_incremental(self) -> dict:
        """Execute incremental update."""
        logger.info("=" * 50)
        logger.info("Starting incremental data update")
        logger.info("=" * 50)

        stats = {}

        logger.info("[1/2] Daily kline (incremental)...")
        stats["daily_kline"] = self.update_daily_kline(partial=True)

        logger.info("[2/2] Financial data (not daily)")
        stats["financial"] = 0

        logger.info("Incremental update done.")
        return stats


def run_full_update(db_path: str) -> dict:
    """Convenience function: run full data update."""
    store = SQLiteStore(db_path)
    store.init_schema()
    updater = DataUpdater(store)
    return updater.update_full()


def run_incremental_update(db_path: str) -> dict:
    """Convenience function: run incremental data update."""
    store = SQLiteStore(db_path)
    store.init_schema()
    updater = DataUpdater(store)
    return updater.update_incremental()
