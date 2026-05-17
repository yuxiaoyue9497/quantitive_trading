"""策略信号计算 — 支持多种均线类型、止损、仓位管理的策略引擎"""

from __future__ import annotations

import numpy as np
import pandas as pd


def dual_ma_strategy(
    df: pd.DataFrame,
    short: int = 5,
    medium: int = 20,
    ma_type: str = "sma",
    threshold: float = 0.0,
    stop_loss_pct: float = 0.0,
    trailing_stop_pct: float = 0.0,
    position_pct: float = 1.0,
    filter_volume: bool = False,
    volume_ratio: float = 1.0,
) -> pd.DataFrame:
    """计算策略信号并添加到 df 的 'signal' 列。

    参数：
        df:              行情 DataFrame，必须含 close、volume 列
        short:           短期均线窗口 (默认 5)
        medium:          长期均线窗口 (默认 20)
        ma_type:         均线类型，"sma" 移动平均或 "ema" 指数移动平均
        threshold:       交叉阈值，仅当 ma_short > ma_medium * (1 + threshold) 才买入
                        用于过滤假信号，默认 0.0（直接交叉即触发）
        stop_loss_pct:   固定止损比例 (如 0.05 表示 5%)
        trailing_stop_pct: 追踪止损比例 (如 0.03 表示从最高点回落 3% 触发)
        position_pct:    仓位比例 (0.0-1.0)，0.5 表示半仓
        filter_volume:   是否需要成交量过滤
        volume_ratio:    成交量倍数过滤，仅当日成交量 > volume_ratio * 近期均量时交易

    规则：
        基础：ma_short > ma_medium → 持仓 (signal=1)
        止损：触及止损 → 空仓 (signal=0)
        仓位：持仓时 signal 范围 [0, position_pct]

    返回：
        带有以下额外列的 DataFrame:
            MA_short, MA_medium, signal, ma_diff, is_stop_loss, cum_position
    """
    if ma_type == "ema":
        ma_short_ser = df["close"].ewm(span=short, adjust=False).mean()
        ma_medium_ser = df["close"].ewm(span=medium, adjust=False).mean()
    else:
        ma_short_ser = df["close"].rolling(window=short).mean()
        ma_medium_ser = df["close"].rolling(window=medium).mean()

    df["MA_short"] = ma_short_ser
    df["MA_medium"] = ma_medium_ser
    df["ma_diff"] = ma_short_ser - ma_medium_ser

    # ── 基础信号 ──
    if threshold > 0:
        df["signal"] = np.where(
            ma_short_ser > ma_medium_ser * (1 + threshold),
            1.0,
            0.0,
        )
    else:
        df["signal"] = np.where(ma_short_ser > ma_medium_ser, 1.0, 0.0)

    # ── 成交量过滤 ──
    if filter_volume:
        vol_ma = df["volume"].rolling(window=medium).mean()
        df["vol_filter"] = (df["volume"] > vol_ma * volume_ratio).astype(float)
        df["signal"] = df["signal"] * df["vol_filter"]

    # ── 追踪止损（优先于均线） ──
    if trailing_stop_pct > 0:
        # 从持仓最高点计算的回撤
        high_since_entry = df["high"].cummax()
        pull_back = (df["close"] / high_since_entry) - 1
        mask_trail = df["signal"] == 1
        df.loc[mask_trail, "signal"] = np.where(
            pull_back < -trailing_stop_pct,
            0.0,
            df.loc[mask_trail, "signal"],
        )
        df.loc[~mask_trail, "signal"] = 0.0  # 未持仓部分保持 0

    # ── 固定止损 ──
    if stop_loss_pct > 0:
        # 简化：从买入信号日起算，最大连续下跌超过 stop_loss_pct 则止损
        # 先找每个买入点
        is_buy = df["signal"].diff() == 1
        buy_dates_idx = is_buy[is_buy].index
        for idx in buy_dates_idx:
            entry_price = df.loc[idx, "close"]
            mask = (df.index >= idx) & (df["signal"] == 1)
            if mask.any():
                df.loc[mask, "signal"] = np.where(
                    df.loc[mask, "close"] < (entry_price * (1 - stop_loss_pct)),
                    0.0,
                    df.loc[mask, "signal"],
                )

    # ── 仓位管理 ──
    if position_pct < 1.0:
        mask = df["signal"] > 0
        df.loc[mask, "signal"] = position_pct

    # ── 标记止损触发点 ──
    df["is_stop_loss"] = False

    return df


def macd_strategy(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD 策略信号。

    规则：MACD 金叉（DIF 上穿 DEA）→ 买入，死叉 → 卖出。
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["dif"] = ema_fast - ema_slow
    df["dea"] = df["dif"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["dif"] - df["dea"]
    df["signal"] = 0.0
    # 金叉：DIF 从下方穿越 DEA
    df.loc[(df["dif"] > df["dea"]) & (df["dif"].shift(1) <= df["dea"].shift(1)), "signal"] = 1
    # 死叉：DIF 从上方穿越 DEA
    df.loc[(df["dif"] < df["dea"]) & (df["dif"].shift(1) >= df["dea"].shift(1)), "signal"] = 0
    df["signal"] = df["signal"].fillna(0)
    return df


def bollinger_strategy(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.DataFrame:
    """布林带策略信号。

    规则：价格下穿下轨 → 买入；价格上穿上轨 → 卖出。
    """
    df["MA"] = df["close"].rolling(window=window).mean()
    df["std"] = df["close"].rolling(window=window).std()
    df["upper"] = df["MA"] + num_std * df["std"]
    df["lower"] = df["MA"] - num_std * df["std"]
    df["signal"] = 0.0
    # 价格下穿下轨 → 买入
    df.loc[df["close"] < df["lower"], "signal"] = 1.0
    # 价格上穿上轨 → 卖出
    df.loc[df["close"] > df["upper"], "signal"] = 0.0
    return df
