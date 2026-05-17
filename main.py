"""量化回测框架入口 — 双均线策略"""

from __future__ import annotations

import sys

from backtest.constants import BacktestConsts
from backtest.data_feed import fetch_stock_data
from backtest.datafeed.resolver import resolve_data_source
from backtest.engine import calc_performance, run_backtest
from backtest.plotter import plot_backtest
from backtest.strategy import dual_ma_strategy


def print_report(metrics: dict) -> None:
    """终端打印绩效报告。"""
    sep = "=" * 55
    thin = "-" * 55
    print(f"\n{sep}")
    print("               回测绩效报告")
    print(sep)
    print(f"策略总收益率 (Total Return):        {metrics['total_return'] * 100:.2f}%")
    print(f"基准总收益率 (Benchmark Return):    {metrics['benchmark_return'] * 100:.2f}%")
    print(f"超额收益 (Alpha):                   {metrics['alpha'] * 100:.2f}%")
    print(thin)
    print(f"年化收益率 (Annualized Return):     {metrics['annual_return'] * 100:.2f}%")
    print(f"年化波动率 (Annualized Volatility): {metrics['annual_volatility'] * 100:.2f}%")
    print(f"最大回撤 (Max Drawdown):            {metrics['max_drawdown'] * 100:.2f}%")
    print(f"夏普比率 (Sharpe Ratio):            {metrics['sharpe_ratio']:.2f}")
    print(thin)
    print(f"交易次数 (买入/卖出):               {metrics['buy_count']} / {metrics['sell_count']}")
    print(f"总手续费成本 (Trading Cost):          {metrics['total_cost']:.6f} ({metrics['total_cost'] * 100:.2f}%)")
    print(f"  ├─ 买入手续费:                     {metrics['total_buy_cost']:.6f}")
    print(f"  └─ 卖出手续费:                     {metrics['total_sell_cost']:.6f}")
    print(sep)


def main() -> None:
    # ── 配置 ──
    SYMBOL = "sz.300750"       # 宁德时代（深市）
    START_DATE = "2023-01-01"
    END_DATE = "2025-12-31"
    DATA_SOURCE = "baostock"   # ─ 数据源配置 ─ 可选: baostock / akshare / tushare
    TUSHARE_TOKEN = ""         # 仅当 DATA_SOURCE="tushare" 时需要
    ADJUST = "2"               # 复权: 1=不复权 / 2=前复权 / 3=后复权

    # ── 1. 获取数据 ──
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

    # ── 2. 策略信号 ──
    print("计算双均线策略信号...")
    df = dual_ma_strategy(df, short=5, medium=20)

    # ── 3. 回测 ──
    print("运行回测引擎...")
    df = run_backtest(df)

    # ── 4. 绩效 ──
    print("计算量化绩效指标...")
    metrics = calc_performance(df)
    print_report(metrics)

    # ── 5. 绘图 ──
    report_title = f"{SYMBOL} {DATA_SOURCE} | 双均线策略 ({START_DATE[:4]}-{END_DATE[:4]})"
    plot_backtest(df, report_title)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。")
        sys.exit(1)
    except ImportError as e:
        # 优雅处理未安装的数据源依赖
        print(f"\n导入错误: {e}")
        print("请安装对应数据源: uv add akshare 或 uv add tushare")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
