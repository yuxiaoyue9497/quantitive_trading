"""双均线交叉策略。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import BaseStrategy, StrategyConfig


@dataclass
class DualMaConfig(StrategyConfig):
    """双均线策略配置。"""

    short: int = 5
    medium: int = 20
    ma_type: str = "sma"            # "sma" or "ema"
    threshold: float = 0.0           # 交叉阈值(过滤假信号)
    stop_loss_pct: float = 0.0       # 固定止损
    trailing_stop_pct: float = 0.0   # 追踪止损
    position_pct: float = 1.0        # 仓位比例
    filter_volume: bool = False      # 成交量过滤
    volume_ratio: float = 1.0        # 成交量倍数


class DualMaStrategy(BaseStrategy):
    """双均线交叉策略。

    规则：short MA > medium MA → 持仓，否则空仓。
    可选：止损、追踪止损、仓位管理、成交量过滤。
    """

    name = "dual_ma"

    def __init__(self, **kwargs: object) -> None:
        self.config = DualMaConfig(**kwargs)
        super().__init__(**kwargs)

    def _compute_ma(self, close: pd.Series, window: int, ma_type: str) -> pd.Series:
        if ma_type == "ema":
            return close.ewm(span=window, adjust=False).mean()
        return close.rolling(window=window).mean()

    def _apply_trailing_stop(
        self,
        df: pd.DataFrame,
        high: pd.Series,
        signal: pd.Series,
        pct: float,
    ) -> pd.Series:
        high_since_entry = high.cummax()
        pull_back = (df["close"] / high_since_entry) - 1
        mask_holding = signal == 1
        result = signal.copy()
        result.loc[mask_holding & (pull_back < -pct)] = 0
        result.loc[~mask_holding] = 0
        return result

    def _apply_fixed_stop(self, df: pd.DataFrame, signal: pd.Series, pct: float) -> pd.Series:
        is_buy = signal.diff() == 1
        for idx in is_buy[is_buy].index:
            entry_price = df.loc[idx, "close"]
            mask = df.index >= idx
            holding = df.loc[mask]
            already_zero = holding["signal"] == 0
            trigger = (holding["close"] < entry_price * (1 - pct)) & (~already_zero)
            df.loc[trigger, "signal"] = 0
        return signal

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        c = self.config
        close = df["close"]

        # ── 均线 ──
        ma_short = self._compute_ma(close, c.short, c.ma_type)
        ma_medium = self._compute_ma(close, c.medium, c.ma_type)

        df["MA_short"] = ma_short
        df["MA_medium"] = ma_medium
        df["ma_diff"] = ma_short - ma_medium

        # ── 基础信号 ──
        if c.threshold > 0:
            df["signal"] = np.where(
                ma_short > ma_medium * (1 + c.threshold),
                1.0,
                0.0,
            )
        else:
            df["signal"] = np.where(ma_short > ma_medium, 1.0, 0.0)

        # ── 成交量过滤 ──
        if c.filter_volume and "volume" in df.columns:
            vol_ma = df["volume"].rolling(window=c.medium).mean()
            df["vol_filter"] = (df["volume"] > vol_ma * c.volume_ratio).astype(float)
            df["signal"] = df["signal"] * df["vol_filter"]

        # ── 追踪止损 ──
        if c.trailing_stop_pct > 0:
            df["signal"] = self._apply_trailing_stop(df, df["high"], df["signal"], c.trailing_stop_pct)
            df["is_trailing_stop"] = True

        # ── 固定止损 ──
        if c.stop_loss_pct > 0:
            df["signal"] = self._apply_fixed_stop(df, df["signal"], c.stop_loss_pct)
            df["is_stop_loss"] = True

        # ── 仓位管理 ──
        if c.position_pct < 1.0:
            mask = df["signal"] > 0
            df.loc[mask, "signal"] = c.position_pct

        return df
