"""MACD 策略。

MACD（Moving Average Convergence Divergence）通过两条 EMA 的交叉产生交易信号。
适用于趋势行情，在震荡市中可能产生较多假信号。

使用示例：
    >>> from backtest.strategy.macd import MacdStrategy
    >>> strategy = MacdStrategy(fast_period=12, slow_period=26, signal_period=9)
    >>> df = strategy.compute(df)
    >>> df['signal']  # 1=买入, 0=卖出
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .base import BaseStrategy


@dataclass
class MacdConfig:
    """MACD 策略配置。

    Attributes:
        fast_period:   快速 EMA 周期
        slow_period:   慢速 EMA 周期
        signal_period: 信号线 EMA 周期
    """

    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9


class MacdStrategy(BaseStrategy):
    """MACD 金叉/死叉策略。

    规则：
        - DIF 金叉 DEA → 买入 (signal=1)
        - DIF 死叉 DEA → 卖出 (signal=0)

    MACD 计算：
        DIF = FastEMA - SlowEMA
        DEA = DIF 的 Signal 线
        MACD 柱 = DIF - DEA

    金叉：DIF 从下方向上穿越 DEA
    死叉：DIF 从上方向下穿越 DEA
    """

    name = "macd"

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> None:
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]

        # 计算 EMA
        ema_fast = close.ewm(span=self.fast_period).mean()
        ema_slow = close.ewm(span=self.slow_period).mean()

        # DIF = FastEMA - SlowEMA
        df["dif"] = ema_fast - ema_slow

        # DEA = DIF 的信号线
        df["dea"] = df["dif"].ewm(span=self.signal_period).mean()

        # MACD 柱状图
        df["macd_hist"] = df["dif"] - df["dea"]

        # 金叉/死叉信号
        df["signal"] = 0.0
        # 金叉：DIF 从下方向上穿越 DEA
        mask_gold = (df["dif"] > df["dea"]) & (df["dif"].shift(1) <= df["dea"].shift(1))
        df.loc[mask_gold, "signal"] = 1.0

        # 死叉：DIF 从上方向下穿越 DEA
        mask_death = (df["dif"] < df["dea"]) & (df["dif"].shift(1) >= df["dea"].shift(1))
        df.loc[mask_death, "signal"] = 0.0

        return df
