"""量价指标模块。

提供常用的成交量相关指标计算。
"""

from __future__ import annotations

import pandas as pd


def vol_ma(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """计算成交量均线。

    参数：
        df: 必须包含 volume 列
        window: 均线周期

    返回：
        带有 vol_ma 列的 DataFrame
    """
    df["vol_ma"] = df["volume"].rolling(window=window).mean()
    return df


def vol_rate(df: pd.DataFrame) -> pd.DataFrame:
    """计算量比（当日成交量 / 5日均量）。

    参数：
        df: 必须包含 volume 列

    返回：
        带有 vol_rate 列的 DataFrame
    """
    df["vol_ma"] = df["volume"].rolling(window=5).mean()
    df["vol_rate"] = df["volume"] / df["vol_ma"]
    return df


def vol_weighted_price(df: pd.DataFrame) -> pd.DataFrame:
    """计算成交量加权价格 VWAP。

    使用典型价格 (high + low + close) / 3 × volume 计算累积 VWAP。

    参数：
        df: 必须包含 high, low, close, volume 列

    返回：
        带有 vwap 列的 DataFrame
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
    return df
