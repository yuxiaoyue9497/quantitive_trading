"""可视化模块 — 净值曲线绘制"""

from __future__ import annotations

import pandas as pd

# 中文显示配置
import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams["font.sans-serif"] = ["Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False


def plot_backtest(df: pd.DataFrame, title: str = "策略回测净值曲线") -> None:
    """绘制策略净值 vs 基准净值对比图。

    参数：
        df: 回测结果 DataFrame（必须包含 cum_strategy 和 cum_market 列）
        title: 图表标题
    """
    plt.figure(figsize=(14, 7))
    plt.plot(df["cum_strategy"], label="双均线策略净值", color="red", linewidth=2)
    plt.plot(df["cum_market"], label="基准净值", color="blue", alpha=0.6, linestyle="--")
    plt.title(title, fontsize=14)
    plt.xlabel("日期", fontsize=12)
    plt.ylabel("资产净值 (起始为1)", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.show()
