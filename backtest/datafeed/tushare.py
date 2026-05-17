"""Tushare Pro 数据源适配器（完整版）"""

from __future__ import annotations

import pandas as pd


class TushareDataSource:
    """Tushare Pro 完整版数据源适配器。

    使用 pro_api 直接调用，支持手动前/后复权。
    """

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
            raise ImportError("Tushare 数据源需要安装 tushare: uv add tushare")

        if not token:
            raise ValueError("使用 Tushare 数据源需要提供 token: resolve_data_source('tushare', token='...')")

        pro = ts.pro_api(token)

        # 转换代码格式: "sz.300750" -> "300750.SZ"
        parts = code.split(".")
        if len(parts) == 2:
            ts_code = parts[1] + "." + parts[0].upper()
        else:
            ts_code = code + ".SZ"

        # 获取不复权原始数据
        df = pro.daily(ts_code=ts_code, start_date=start.replace("-", ""), end_date=end.replace("-", ""))

        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        # 同时拉取复权因子
        df_adj = pro.adj_factor(ts_code=ts_code, start_date=start.replace("-", ""), end_date=end.replace("-", ""))
        if df_adj is not None and not df_adj.empty:
            df = df.merge(df_adj[["trade_date", "adj_factor"]], on="trade_date", how="left")
            df["adj_factor"] = df["adj_factor"].fillna(method="ffill")

        df = df.rename(columns={
            "trade_date": "date",
            "vol": "volume",
        })

        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        # 手动复权
        if adjust in ("1", None):
            # 不复权
            pass
        elif adjust == "2":
            # 前复权: close' = close * adj_factor[0] / adj_factor
            adj = df["adj_factor"]
            base = adj.iloc[0]
            df["open"] = df["open"] * base / adj
            df["high"] = df["high"] * base / adj
            df["low"] = df["low"] * base / adj
            df["close"] = df["close"] * base / adj
        elif adjust == "3":
            # 后复权: close' = close * adj_factor / adj_factor.iloc[0]
            adj = df["adj_factor"]
            base = adj.iloc[0]
            df["open"] = df["open"] * adj / base
            df["high"] = df["high"] * adj / base
            df["low"] = df["low"] * adj / base
            df["close"] = df["close"] * adj / base

        df.drop(columns=["adj_factor"], inplace=True)
        df = df[["open", "high", "low", "close", "volume"]]
        df.sort_index(inplace=True)
        return df
