import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 解决 matplotlib 中文显示问题
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # Mac环境，Windows可替换为 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# 1. 数据获取模块 (Data Feed)
# ==============================================================================
print("正在从 AKShare 获取宁德时代历史 K 线数据...")
# symbol: 股票代码, period: daily, adjust: qfq(前复权，保证价格连续性)
df = ak.stock_zh_a_hist(symbol="300750", period="daily", 
                        start_date="20230101", end_date="20251231", adjust="qfq")

# 重命名列名以符合通用量化习惯
df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']].rename(
    columns={'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'}
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

# 计算持仓状态：shift(1) 表示今天看昨天的信号决定今天的持仓（避免未来函数）
df['position'] = df['signal'].shift(1).fillna(0)

# ==============================================================================
# 3. 向量化回测引擎模块 (Backtest Engine)
# ==============================================================================
print("运行回测引擎...")
# 计算标的资产（股票）的每日涨跌幅
df['market_return'] = df['close'].pct_change()

# 计算策略的每日收益率：持仓(1)则享受涨跌，空仓(0)则收益为 0
# 暂不考虑交易手续费以简化流程
df['strategy_return'] = df['market_return'] * df['position']

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

print("\n" + "="*25 + " 回测绩效报告 " + "="*25)
print(f"策略总收益率 (Total Return):      {total_return * 100:.2f}%")
print(f"基准总收益率 (Benchmark Return):  {benchmark_return * 100:.2f}%")
print(f"年化收益率 (Annualized Return):   {annual_return * 100:.2f}%")
print(f"最大回撤 (Max Drawdown):          {max_drawdown * 100:.2f}%")
print(f"夏普比率 (Sharpe Ratio):          {sharpe_ratio:.2f}")
print("="*64)

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