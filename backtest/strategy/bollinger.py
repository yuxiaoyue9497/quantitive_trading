"""布林带策略。

布林带通过标准差构建价格通道，用于判断超买超卖。
当价格穿透通道边界时发出交易信号。

使用示例：
    >>> from backtest.strategy.bollinger import BollingerStrategy
    >>> strategy = BollingerStrategy(window=20, std_dev=2.0)
    >>> df = strategy.compute(df)
    >>> df['signal']  # 1=买入, 0=卖出
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseStrategy


@dataclass
class BollingerConfig:
    """布林带策略配置。

    Attributes:
        window: 均线计算窗口
        std_dev: 标准差倍数，决定通道宽度
    """

    window: int = 20
    std_dev: float = 2.0


class BollingerStrategy(BaseStrategy):
    """布林带策略。

    规则：
        - 价格下穿下轨 → 买入 (signal=1)
        - 价格上穿上轨 → 卖出 (signal=0)

    布林带计算：
        中轨 = 收盘价窗口均线
        上轨 = 中轨 + std_dev × 标准差
        下轨 = 中轨 - std_dev × 标准差
    """

    name = "bollinger"

    def __init__(self, window: int = 20, std_dev: float = 2.0) -> None:
        super().__init__()
        self.window = window
        self.std_dev = std_dev

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]

        # 计算布林带
        df["ma"] = close.rolling(window=self.window).mean()
        df["std"] = close.rolling(window=self.window).std()
        df["upper"] = df["ma"] + self.std_dev * df["std"]
        df["lower"] = df["ma"] - self.std_dev * df["std"]

        # 信号：穿越下轨买入，穿越上轨卖出
        df["signal"] = 0.0
        df.loc[close < df["lower"], "signal"] = 1.0
        df.loc[close > df["upper"], "signal"] = 0.0

        return df
