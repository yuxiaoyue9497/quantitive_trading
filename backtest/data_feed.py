"""数据获取模块 — Baostock 行情源"""

from __future__ import annotations

from typing import Optional

import baostock as bs
import pandas as pd

from .constants import DataConsts


def fetch_stock_data(
    code: str,
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    *,
    adjust: Optional[str] = "2",
) -> pd.DataFrame:
    """拉取日 K 数据并清理为标准格式。

    参数：
        code: 股票代码，如 "sz.300750"
        start: 开始日期 YYYY-MM-DD
        end:   结束日期 YYYY-MM-DD
        adjust: 复权方式 (None/1=不复权/2=前复权/3=后复权)

    返回：
        列名 [date, open, high, low, close, volume] 的 DataFrame，
        date 为 datetime 索引，已按时间排序。
    """
    lg = bs.login()
    try:
        fields = DataConsts.BAOSTOCK_FIELDS
        freq = DataConsts.BAOSTOCK_FREQ or "d"
        adj = adjust or DataConsts.BAOSTOCK_ADJUST

        rs = bs.query_history_k_data_plus(
            code=code,
            fields=fields,
            start_date=start,
            end_date=end,
            frequency=freq,
            adjustflag=adj,
        )
        df_raw = rs.get_data()
    finally:
        bs.logout()

    numeric_cols = ["open", "high", "low", "close", "volume"]
    df = df_raw[["date", "open", "high", "low", "close", "volume"]].copy()
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    return df
