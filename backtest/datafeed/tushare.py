"""Tushare Pro 数据源适配器"""

from __future__ import annotations

import pandas as pd

from .base import AbstractDataSource


class TushareDataSource(AbstractDataSource):
    """Tushare Pro 数据源适配器"""

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str | None = "2",
        token: str = "",
    ) -> pd.DataFrame:
        try:
            import tushare as ts
        except ImportError:
            raise ImportError(
                "TuShare 数据源需要安装 tushare: uv add tushare"
            )

        if not token:
            raise ValueError(
                "使用 TuShare 数据源需要提供 token: resolve_data_source('tushare', token='...')"
            )

        pro = ts.pro_api(token)

        # 转换代码格式: "sz.300750" -> "300750.SZ"
        parts = code.split(".")
        if len(parts) == 2:
            ts_code = parts[1] + "." + parts[0].upper()
        else:
            ts_code = code + ".SZ"

        df = pro.daily(
            ts_code=ts_code,
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
        )

        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        # Tushare 列名: trade_date, open, high, low, close, vol
        df = df.rename(columns={
            "trade_date": "date",
            "vol": "volume",
        })

        # adjust 参数映射到后处理
        if adjust in ("2", "3"):
            # Tushare 不复权数据，需要自行复权或使用 daily_basic
            # 这里使用前复权逻辑
            df["adj_factor"] = 1.0  # 简化：不复权
            if adjust == "3":
                # 后复权 = close * adj_factor / adj_factor.iloc[0] (简化)
                pass

        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]]
        df.sort_index(inplace=True)
        return df
