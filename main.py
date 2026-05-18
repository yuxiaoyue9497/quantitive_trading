"""回测框架入口 — 策略驱动的回测引擎。

通过配置切换不同策略：
    STRATEGY = "dual_ma"      # 双均线策略
    STRATEGY = "bollinger"    # 布林带策略
    STRATEGY = "supertrend"   # SuperTrend 策略
    STRATEGY = "macd"         # MACD 策略
"""

from __future__ import annotations

import sys

from backtest.constants import BacktestConsts
from backtest.data_feed import fetch_stock_data
from backtest.datafeed.resolver import resolve_data_source
from backtest.engine import calc_performance, run_backtest
from backtest.plotter import plot_backtest
from backtest.strategy import (
    BaseStrategy,
    DualMaStrategy,
    BollingerStrategy,
    MacdStrategy,
    SuperTrendStrategy,
)

STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "dual_ma": DualMaStrategy,
    "bollinger": BollingerStrategy,
    "macd": MacdStrategy,
    "supertrend": SuperTrendStrategy,
}


def main() -> None:
    # ── 1. 配置 ──
    SYMBOL = "sz.300750"           # 宁德时代（深市）
    START_DATE = "2023-01-01"
    END_DATE = "2025-12-31"
    DATA_SOURCE = "baostock"       # 可选: baostock / akshare / tushare
    TUSHARE_TOKEN = ""             # 仅当 DATA_SOURCE="tushare" 时需要
    ADJUST = "2"                   # 复权: 1=不复权 / 2=前复权 / 3=后复权
    STRATEGY_NAME = "dual_ma"      # 可选: dual_ma / bollinger / macd / supertrend

    # ── 2. 获取数据 ──
    print(f"正在从 {DATA_SOURCE} 获取历史 K 线数据...")
    df = fetch_stock_data(
        code=SYMBOL,
        start=START_DATE,
        end=END_DATE,
        source=DATA_SOURCE,
        adjust=ADJUST,
        token=TUSHARE_TOKEN if DATA_SOURCE == "tushare" else None,
    )
    print(f"  获取到 {len(df)} 条日 K 数据")

    # ── 3. 策略信号 ──
    strategy_cls = STRATEGY_MAP.get(STRATEGY_NAME)
    if strategy_cls is None:
        names = ", ".join(STRATEGY_MAP.keys())
        raise ValueError(f"不支持的策略: '{STRATEGY_NAME}'。可选: [{names}]")

    # 根据策略名创建实例
    if STRATEGY_NAME == "dual_ma":
        strategy = DualMaStrategy(short=5, medium=20)
    elif STRATEGY_NAME == "bollinger":
        strategy = BollingerStrategy(window=20, std_dev=2.0)
    elif STRATEGY_NAME == "macd":
        strategy = MacdStrategy(fast_period=12, slow_period=26, signal_period=9)
    elif STRATEGY_NAME == "supertrend":
        strategy = SuperTrendStrategy(atr_period=10, atr_mult=3.0)

    print(f"使用策略: {strategy.name}")
    df = strategy.compute(df)

    # ── 4. 回测 ──
    print("运行回测引擎...")
    df = run_backtest(df)

    # ── 5. 绩效 ──
    print("计算量化绩效指标...")
    metrics = calc_performance(df)
    print_report(metrics)

    # ── 6. 绘图 ──
    report_title = f"{SYMBOL} {DATA_SOURCE} | {strategy.name} ({START_DATE[:4]}-{END_DATE[:4]})"
    plot_backtest(df, report_title)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。")
        sys.exit(1)
    except ImportError as e:
        print(f"\n导入错误: {e}")
        print("请安装对应数据源: uv add akshare 或 uv add tushare")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
