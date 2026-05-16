"""策略信号计算 — 双均线策略"""

from __future__ import annotations

import numpy as np
import pandas as pd


def dual_ma_strategy(df: pd.DataFrame, short: int = 5, medium: int = 20) -> pd.DataFrame:
    """计算双均线交叉信号并添加到 df 的 'signal' 列。

    规则：MA_short > MA_medium → signal=1（持仓），否则 signal=0（空仓）。
    """
    ma_short = df["close"].rolling(window=short).mean()
    ma_medium = df["close"].rolling(window=medium).mean()

    df["MA5"] = ma_short
    df["MA20"] = ma_medium
    df["signal"] = np.where(ma_short > ma_medium, 1, 0)
    return df
