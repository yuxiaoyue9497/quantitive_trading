"""SuperTrend 策略。

基于 ATR 构建价格通道，趋势方向随价格穿越通道而变化。
适用于趋势跟踪场景。

使用示例：
    >>> from backtest.strategy.supertrend import SuperTrendStrategy
    >>> strategy = SuperTrendStrategy(atr_period=10, atr_mult=3.0)
    >>> df = strategy.compute(df)
    >>> df['signal']  # 1=看多, 0=看空
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseStrategy


@dataclass
class SuperTrendConfig:
    """SuperTrend 策略配置。

    Attributes:
        atr_period: ATR 计算周期
        atr_mult:   ATR 乘数，决定通道宽度
    """

    atr_period: int = 10
    atr_mult: float = 3.0


class SuperTrendStrategy(BaseStrategy):
    """SuperTrend 策略。

    规则：
        - 价格 > SuperTrend 下轨 → 看多 (signal=1)
        - 价格 < SuperTrend 上轨 → 看空 (signal=0)

    核心逻辑：
        1. 计算 ATR (Average True Range)
        2. 基于 ATR 构建上下通道
        3. 价格穿越通道时趋势翻转
    """

    name = "supertrend"

    def __init__(self, atr_period: int = 10, atr_mult: float = 3.0) -> None:
        super().__init__()
        self.atr_period = atr_period
        self.atr_mult = atr_mult

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # 经典价格 (HL2)
        hl2 = (high + low) / 2

        # ATR 计算
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=self.atr_period).mean()

        # 上下通道
        upper = hl2 + self.atr_mult * atr
        lower = hl2 - self.atr_mult * atr

        # SuperTrend 方向（动态调整）
        # 初始：假设价格在通道中间
        prev_trend = np.zeros(len(df))
        current_trend = np.zeros(len(df))

        # 第一个点
        prev_trend[0] = 1 if close.iloc[0] > lower.iloc[0] else -1

        for i in range(1, len(df)):
            if close.iloc[i] > close.iloc[i - 1]:
                prev_trend[i] = max(prev_trend[i], 1)
            else:
                prev_trend[i] = max(prev_trend[i], -1)

            # 价格穿越上轨
            if prev_trend[i] < 0 and close.iloc[i] > upper.iloc[i]:
                prev_trend[i] = 1

            # 价格穿越下轨
            if prev_trend[i] > 0 and close.iloc[i] < lower.iloc[i]:
                prev_trend[i] = -1

        df["super_trend"] = np.where(current_trend == 1, lower, upper)
        df["signal"] = np.where(close > df["super_trend"], 1.0, 0.0)
        df["atr"] = atr
        df["upper_band"] = upper
        df["lower_band"] = lower

        return df
