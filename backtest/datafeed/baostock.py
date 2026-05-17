"""Baostock 数据源适配器"""

from __future__ import annotations

from typing import Any

import baostock as bs
import pandas as pd

from .base import AbstractDataSource


class BaostockDataSource(AbstractDataSource):
    """Baostock 数据源适配器"""

    FIELDS = "date,code,open,high,low,close,preclose,volume,turn,amount,adjustflag,pctChg"
    FREQ = "d"

    def __init__(self, **kwargs: Any) -> None:
        """Baostock 不需要额外参数，忽略 kwargs。"""

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str | None = "2",
    ) -> pd.DataFrame:
        lg = bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                code=code,
                fields=self.FIELDS,
                start_date=start,
                end_date=end,
                frequency=self.FREQ,
                adjustflag=adjust or "2",
            )
            df_raw = rs.get_data()
        finally:
            bs.logout()

        df = df_raw[["date", "open", "high", "low", "close", "volume"]].copy()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        return df
