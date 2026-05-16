"""回测引擎 — 持仓管理、收益与交易成本"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import TradingConsts


def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    """向量化回测，输入含 signal 列的 DataFrame，补充收益相关列。

    补充列：
        market_return, position, signal_change,
        is_buy, is_sell, trading_cost,
        strategy_return, cum_market, cum_strategy
    """
    df["market_return"] = df["close"].pct_change()

    # shift(1) 用昨天的信号决定今天持仓，避免未来函数
    df["position"] = df["signal"].shift(1).fillna(0)

    # 交易方向
    df["signal_change"] = df["signal"].diff()
    df["is_buy"] = (df["signal_change"] == 1).astype(float)
    df["is_sell"] = (df["signal_change"] == -1).astype(float)

    # 手续费
    df["trading_cost"] = (
        df["is_buy"] * TradingConsts.RATE_BUY
        + df["is_sell"] * TradingConsts.RATE_SELL
    ) * df["position"]

    # 收益（起始资金=1）
    df["strategy_return"] = (
        df["market_return"] * df["position"] - df["trading_cost"]
    )
    df["cum_market"] = (1 + df["market_return"].fillna(0)).cumprod()
    df["cum_strategy"] = (1 + df["strategy_return"].fillna(0)).cumprod()
    return df


def calc_performance(df: pd.DataFrame) -> dict:
    """从回测 DataFrame 中计算绩效指标。

    返回字典：
        total_return, benchmark_return, alpha,
        annual_return, annual_vol, sharpe_ratio,
        max_drawdown, buy_count, sell_count, total_cost,
        total_buy_cost, total_sell_cost
    """
    total_return = df["cum_strategy"].iloc[-1] - 1
    benchmark_return = df["cum_market"].iloc[-1] - 1
    alpha = total_return - benchmark_return

    # 最大回撤
    cum_peaks = df["cum_strategy"].cummax()
    drawdown = (df["cum_strategy"] - cum_peaks) / cum_peaks
    max_drawdown = drawdown.min()

    # 夏普比率
    ann_ret = df["strategy_return"].mean() * 242
    ann_vol = df["strategy_return"].std() * (242 ** 0.5)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol != 0 else 0

    cost_mask = df["trading_cost"] > 0
    total_buy_cost = (df["trading_cost"] * cost_mask * (df["is_buy"] > 0)).sum()
    total_sell_cost = (df["trading_cost"] * cost_mask * (df["is_sell"] > 0)).sum()

    return {
        "total_return": total_return,
        "benchmark_return": benchmark_return,
        "alpha": alpha,
        "annual_return": ann_ret,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "buy_count": int(df["is_buy"].sum()),
        "sell_count": int(df["is_sell"].sum()),
        "total_cost": df["trading_cost"].sum(),
        "total_buy_cost": total_buy_cost,
        "total_sell_cost": total_sell_cost,
    }
