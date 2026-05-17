"""终端 UI 输出 — 报告打印、状态提示等。"""

from __future__ import annotations


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
