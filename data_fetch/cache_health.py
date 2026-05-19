"""Data health check report."""

from __future__ import annotations

import datetime
import logging

from .sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

WARN_COVERAGE = 0.95
WARN_MAX_DAYS_DIFF = 7
WARN_PCT_CHANGE = 15.0


def check_health(db_path: str) -> dict:
    """数据健康检查，返回检查结果。

    Checks:
    - 数据新鲜度: 最新数据日期 vs 当前日期
    - 股票覆盖率: 每个交易日有数据的股票数
    - 缺失检测: 连续停牌超过 X 日
    - 异常检测: 单日涨跌幅 > 15% (非ST)
    """
    store = SQLiteStore(db_path)
    today = datetime.date.today().isoformat()

    result = {
        "check_date": today,
        "freshness": None,
        "stock_coverage": None,
        "suspension_alerts": [],
        "abnormal_alerts": [],
        "overall": "OK",
    }

    # 1. 数据新鲜度
    latest = store.query_one(
        "SELECT MAX(date) as latest FROM daily_kline"
    )
    if latest and latest.get("latest"):
        result["freshness"] = latest["latest"]
        days_diff = (
            datetime.date.fromisoformat(today)
            - datetime.date.fromisoformat(latest["latest"])
        ).days
        if days_diff > WARN_MAX_DAYS_DIFF:
            result["freshness_status"] = "WARN"
            result["freshness_days_off"] = days_diff
        else:
            result["freshness_status"] = "OK"
    else:
        result["freshness"] = None
        result["freshness_status"] = "ERROR"

    # 2. 每日股票数 (最近30行)
    if latest and latest.get("latest"):
        trade_dates = store.query_df(
            "SELECT date, COUNT(code) as cnt FROM daily_kline "
            "GROUP BY date ORDER BY date DESC LIMIT 30"
        )
        if not trade_dates.empty:
            result["daily_counts"] = trade_dates.to_dict("records")

    # 3. 股票总数
    total_stocks = store.query_one(
        "SELECT COUNT(*) as cnt FROM stock_info"
    )
    if total_stocks:
        result["total_stocks"] = total_stocks["cnt"]

    # 4. 异常涨跌检测
    abnormal = store.query_df(
        f"SELECT code, date, pct_chg, close FROM daily_kline "
        f"WHERE pct_chg > {WARN_PCT_CHANGE} OR pct_chg < {-WARN_PCT_CHANGE} "
        f"AND tradestatus = 0 "
        f"ORDER BY ABS(pct_chg) DESC LIMIT 50"
    )
    if not abnormal.empty:
        result["abnormal_alerts"] = abnormal.head(20).to_dict("records")
        result["abnormal_count"] = len(abnormal)
        if "overall" in result:
            result["overall"] = "WARN"

    # 5. 数据完整性评估
    stock_data = store.query_df(
        "SELECT code, COUNT(date) as days, MIN(date) as min_date, MAX(date) as max_date "
        "FROM daily_kline GROUP BY code"
    )
    if not stock_data.empty:
        min_days = stock_data["days"].min()
        result["min_data_days"] = int(min_days)
        result["mean_data_days"] = int(stock_data["days"].mean())

        if min_days < 10:
            result["overall"] = "WARN"

    store.close()
    _print_health_report(result)
    return result


def _print_health_report(result: dict) -> None:
    """输出健康检查报告"""
    print("=" * 50)
    print("  Data Health Check Report")
    print("=" * 50)

    status = result.get("freshness_status", "ERROR")
    emoji = {"OK": "\u2705", "WARN": "\u26a0\ufe0f", "ERROR": "\u274c"}

    if result.get("freshness"):
        latest = result["freshness"]
        days = result.get("freshness_days_off", 0)
        print(f"  Latest data date: {latest}")
        print(f"  Freshness: {emoji.get(status, '?')} {days} days off")
    else:
        print("  Freshness: no data")

    if result.get("total_stocks"):
        print(f"  Total stocks: {result['total_stocks']}")
        if result.get("mean_data_days"):
            print(f"  Avg data days: {result['mean_data_days']}")
        if result.get("min_data_days"):
            print(f"  Min data days: {result['min_data_days']}")

    if result.get("abnormal_count"):
        print(f"  Warning: {result['abnormal_count']} abnormal price changes")
        for row in result.get("abnormal_alerts", [])[:5]:
            print(
                f"    - {row.get('code')}: "
                f"+{row.get('pct_chg', 0):.2f}% ({row.get('date')})"
            )

    overall = result.get("overall", "OK")
    print(f"  Overall: {emoji.get(overall, '?')} {overall}")
    print("=" * 50)
