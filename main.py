import tushare as ts
from tushare import pro_bar
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import os

# Tushare API Token（建议通过环境变量 TUSHARE_TOKEN 设置）
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '')

# 解决 matplotlib 中文显示问题
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # Mac环境，Windows可替换为 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
else:
    print("警告: 未设置 TUSHARE_TOKEN，请将 token 放入环境变量 TUSHARE_TOKEN")
    print("请前往 https://tushare.pro/register 注册并获取 token")
    import sys; sys.exit(1)

# ==============================================================================
# 1. 数据获取模块 (Data Feed)
# ==============================================================================
print("正在从 Tushare 获取宁德时代历史 K 线数据...")
# pro_bar 获取前复权日K数据
# 积分200分以上才有复权类型
df_raw = pro_bar(ts_code='300750.SZ', start_date='20230101', end_date='20251231')
# df_raw = pro_bar(ts_code='300750.SZ', adj='qfq', start_date='20230101', end_date='20251231')

# 重命名列名以符合通用量化习惯
df = df_raw[['trade_date', 'open', 'high', 'low', 'close', 'vol']].rename(
    columns={'trade_date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'vol': 'volume'}
)

df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)
df.sort_index(inplace=True)

# ==============================================================================
# 2. 策略信号计算模块 (Strategy & Signals)
# ==============================================================================
print("计算双均线策略信号...")
df['MA5'] = df['close'].rolling(window=5).mean()
df['MA20'] = df['close'].rolling(window=20).mean()

# 生成交易信号：MA5 > MA20 时为 1（持仓），否则为 0（空仓）
df['signal'] = np.where(df['MA5'] > df['MA20'], 1, 0)

# 向量化回测引擎模块 (Backtest Engine)
print("运行回测引擎...")
df['market_return'] = df['close'].pct_change()

# 持仓状态：1(满仓), 0(空仓) — shift(1) 用昨天的信号决定今天持仓，避免未来函数
df['position'] = df['signal'].shift(1).fillna(0)

# 交易信号：买入(1), 卖出(-1), 无交易(0)
df['signal_change'] = df['signal'].diff()
df['is_buy'] = (df['signal_change'] == 1).astype(float)
df['is_sell'] = (df['signal_change'] == -1).astype(float)

# 手续费模型
# A股通用费率：买入万三佣金+万零六过户费 = 3.6 BPS
#         卖出万三佣金+万零六过户费+千一印花税 = 13.6 BPS
RATE_BUY = 0.0003 + 0.00006  # 0.036%
RATE_SELL = 0.0003 + 0.00006 + 0.001  # 0.136%

# 交易成本（按持仓价值估算）
df['trading_cost'] = (df['is_buy'] * RATE_BUY + df['is_sell'] * RATE_SELL) * df['position']

# 策略每日总收益 = 持仓收益 - 交易成本
df['strategy_return'] = df['market_return'] * df['position'] - df['trading_cost']

# 计算累计收益（净值曲线，起始资金为 1）
df['cum_market'] = (1 + df['market_return'].fillna(0)).cumprod()
df['cum_strategy'] = (1 + df['strategy_return'].fillna(0)).cumprod()

# ==============================================================================
# 4. 绩效指标统计模块 (Performance Metrics)
# ==============================================================================
print("计算量化绩效指标...")
# 总收益率
total_return = df['cum_strategy'].iloc[-1] - 1
# 基准收益率
benchmark_return = df['cum_market'].iloc[-1] - 1

# 计算最大回撤 (Max Drawdown)
# 寻找策略净值曲线的历史滚动最高点
df['cum_peaks'] = df['cum_strategy'].cummax()
df['drawdown'] = (df['cum_strategy'] - df['cum_peaks']) / df['cum_peaks']
max_drawdown = df['drawdown'].min()

# 计算夏普比率 (Sharpe Ratio) - 假设无风险利率为 2%
annual_return = (df['strategy_return'].mean() * 242) # A股一年大约242个交易日
annual_vol = df['strategy_return'].std() * np.sqrt(242)
sharpe_ratio = (annual_return - 0.02) / annual_vol if annual_vol != 0 else 0

# === 手续费统计 ===
total_buy_cost = (df['trading_cost'] * (df['trading_cost'] > 0) * (df['is_buy'] > 0)).sum()
total_sell_cost = (df['trading_cost'] * (df['trading_cost'] > 0) * (df['is_sell'] > 0)).sum()
total_cost = df['trading_cost'].sum()
n_buys = df['is_buy'].sum()
n_sells = df['is_sell'].sum()

print("\n" + "="*55)
print("               回测绩效报告")
print("="*55)
print(f"策略总收益率 (Total Return):      {total_return * 100:.2f}%")
print(f"基准总收益率 (Benchmark Return):  {benchmark_return * 100:.2f}%")
print(f"超额收益 (Alpha):                 {(total_return - benchmark_return) * 100:.2f}%")
print("-" * 55)
print(f"年化收益率 (Annualized Return):   {annual_return * 100:.2f}%")
print(f"年化波动率 (Annualized Volatility): {annual_vol * 100:.2f}%")
print(f"最大回撤 (Max Drawdown):          {max_drawdown * 100:.2f}%")
print(f"夏普比率 (Sharpe Ratio):          {sharpe_ratio:.2f}")
print("-" * 55)
print(f"交易次数 (买入/卖出):             {int(n_buys)} / {int(n_sells)}")
print(f"总手续费成本 (Trading Cost):       {total_cost:.6f} ({total_cost * 100:.2f}%)")
print(f"  ├─ 买入手续费:                   {total_buy_cost:.6f}")
print(f"  └─ 卖出手续费:                   {total_sell_cost:.6f}")
print("="*55)

# ==============================================================================
# 5. 可视化输出模块 (Visualization)
# ==============================================================================
plt.figure(figsize=(14, 7))
plt.plot(df['cum_strategy'], label='双均线策略净值', color='red', linewidth=2)
plt.plot(df['cum_market'], label='宁德时代基准净值', color='blue', alpha=0.6, linestyle='--')
plt.title('宁德时代 (300750) 双均线策略回测净值曲线 (2023-2025)', fontsize=14)
plt.xlabel('日期', fontsize=12)
plt.ylabel('资产净值 (起始为1)', fontsize=12)
plt.legend(fontsize=12)
plt.grid(True, alpha=0.3)
plt.show()