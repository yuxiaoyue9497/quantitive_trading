"""策略模块入口 — 统一导出所有策略和配置类。

使用示例：
    >>> from backtest.strategy import DualMaStrategy, BollingerStrategy
    >>> strategy = DualMaStrategy(short=5, medium=20)
    >>> df = strategy.compute(df)
"""

from __future__ import annotations

from .base import BaseStrategy, StrategyConfig
from .dual_ma import DualMaStrategy, DualMaConfig
from .bollinger import BollingerStrategy
from .macd import MacdStrategy
from .supertrend import SuperTrendStrategy

__all__ = [
    "BaseStrategy",
    "StrategyConfig",
    "DualMaStrategy",
    "DualMaConfig",
    "BollingerStrategy",
    "MacdStrategy",
    "SuperTrendStrategy",
]
