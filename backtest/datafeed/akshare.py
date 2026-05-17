"""AkShare 数据源适配器"""

from __future__ import annotations

import pandas as pd

from .base import AbstractDataSource


class AkShareDataSource(AbstractDataSource):
    """AkShare 数据源适配器"""

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str | None = "2",
    ) -> pd.DataFrame:
        try:
            import akshare as ak
        except ImportError:
            raise ImportError(
                "AkShare 数据源需要安装 akshare: uv add akshare"
            )

        symbol = code.split(".")[-1]

        # ak.stock_zh_a_hist 的 adjust 参数: "" 不复权, "qfq" 前复权, "hfq" 后复权
        adjust_map = {None: "", "1": "", "2": "qfq", "3": "hfq"}
        ak_adjust = adjust_map.get(adjust, "qfq")

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
            adjust=ak_adjust,
        )

        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        })
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
        return df
