# A股量化策略回测框架

A 股量化策略回测框架，支持多数据源接入、多策略切换、手续费建模、绩效分析和净值可视化。

## 功能特性

- **多数据源**：支持 Baostock（默认）、AkShare、Tushare 三种数据源，通过配置项 `DATA_SOURCE` 一键切换
- **数据缓存**：`data_fetch` 模块提供 SQLite 本地缓存，支持全市场批量拉取 + 每日增量更新，回测无需反复调 API
- **多策略框架**：类式策略设计，继承 `BaseStrategy` 即可扩展新策略。内置双均线、布林带、MACD、SuperTrend 四种策略
- **手续费建模**：买入万三佣金 + 万零六过户费（3.6 BPS），卖出万三佣金 + 万零六过户费 + 千一印花税（13.6 BPS）
- **向量化回测**：高性能 pandas/numpy 向量化计算，避免未来函数
- **绩效指标**：总收益率、超额收益（Alpha）、年化收益率、年化波动率、最大回撤、夏普比率
- **手续费统计**：买入 / 卖出手续费明细、交易次数统计
- **净值曲线对比**：策略净值 vs 基准净值可视化

## 安装依赖

本项目使用 [uv](https://github.com/astral-sh/uv) 管理 Python 环境。

```bash
uv sync
```

按需启用额外数据源：

```bash
uv sync --extra akshare    # AkShare
uv sync --extra tushare    # Tushare
```

## 数据同步

`data_fetch` 包提供全市场数据缓存工具：

```bash
# 1. 初始化数据库 + 拉取全市场股票基础信息
uv run python -m data_fetch.cli init

# 2. 全量拉取所有股票的日线和财务数据（首次同步，预计较久）
uv run python -m data_fetch.cli update --full

# 3. 日常增量更新（仅拉取当日数据）
uv run python -m data_fetch.cli update --incremental

# 查看数据库统计
uv run python -m data_fetch.cli info
```

SQLite 数据库位于 `data/sqlite/stock_data.db`，包含以下表：

| 表名 | 说明 | 行数 |
|------|------|------|
| `stock_info` | 沪深 A 股基本资料（代码、名称、行业、上市日期等） | ~9,000 |
| `stock_industry` | 申万三级行业分类 | ~5,000 |
| `daily_kline` | 日 K 线（不复权） | 按需填充 |
| `financial_qtr` | 季报财务数据 | 按需填充 |

回测框架可配置使用 SQLite 缓存数据源（减少 API 调用）：

```python
from backtest.datafeed import SQLiteCacheFeed

data = SQLiteCacheFeed.fetch_stock_data(stock_code, start_date, end_date)
```

## 运行回测

### 默认运行

```bash
uv run main.py
```

默认使用 **Baostock** 数据源 + **双均线策略**。

### 切换策略与数据源

修改 `main.py` 中的配置：

```python
# main.py
DATA_SOURCE = "akshare"       # baostock | akshare | tushare
STRATEGY_NAME = "macd"        # dual_ma | bollinger | macd | supertrend
TUSHARE_TOKEN = "your-token"  # 使用 tushare 时需要
```

### 自定义策略

```python
from backtest.strategy import DualMaStrategy, BollingerStrategy, MacdStrategy, SuperTrendStrategy

strategy = DualMaStrategy(short=5, medium=20)
# strategy = BollingerStrategy(window=20, std_dev=2.0)
# strategy = MacdStrategy(fast_period=12, slow_period=26, signal_period=9)
# strategy = SuperTrendStrategy(atr_period=10, atr_mult=3.0)

df = strategy.compute(df)  # df 必须包含 close 列，返回中添加 signal 列
```

### 新建策略

```python
from backtest.strategy import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    name = "my_strategy"

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df["signal"] = ...  # 取值 [0, 1]
        return df
```

### 新建数据源

```python
from backtest.datafeed import AbstractDataSource, register_data_source

class MyDataSource(AbstractDataSource):
    def fetch(self, code: str, start: str, end: str, adjust: str | None) -> pd.DataFrame:
        ...  # 返回 [open, high, low, close, volume]

register_data_source("my", MyDataSource)
```

## 架构设计

```
quantitive-trading/
├── backtest/              # 核心回测模块
│   ├── engine.py          # 回测引擎
│   ├── plotter.py         # 净值曲线可视化
│   ├── data_feed.py       # 统一数据获取入口
│   ├── constants.py       # 费率、交易日等常量
│   ├── strategy/          # 策略模块
│   │   ├── base.py        # BaseStrategy 基类
│   │   ├── dual_ma.py     # 双均线
│   │   ├── bollinger.py   # 布林带
│   │   ├── macd.py        # MACD
│   │   └── supertrend.py  # SuperTrend
│   └── datafeed/          # 数据源适配器
│       ├── baostock.py    # Baostock
│       ├── akshare.py     # AkShare
│       ├── tushare.py     # Tushare
│       └── resolver.py    # 数据源解析器
├── data_fetch/            # 数据获取与缓存模块
│   ├── cli.py             # CLI 入口
│   ├── db.py              # SQLite 数据库操作
│   ├── fetch_stock_info.py
│   ├── fetch_industry.py
│   ├── fetch_daily_kline.py
│   ├── fetch_financial_qtr.py
│   └── fetch_utils.py
├── docs/
├── main.py                # 入口
├── pyproject.toml
└── uv.lock
```

## 内置策略说明

### 双均线 (dual_ma)
- 买入：短期均线上穿长期均线
- 卖出：短期均线下穿长期均线
- 参数：short, medium, ma_type(sma/ema)

### 布林带 (bollinger)
- 买入：价格下穿下轨
- 卖出：价格上穿上轨
- 参数：window, std_dev

### MACD (macd)
- 买入：DIF 金叉 DEA
- 卖出：DIF 死叉 DEA
- 参数：fast_period(12), slow_period(26), signal_period(9)

### SuperTrend (supertrend)
- 买入：价格上穿 SuperTrend 通道
- 卖出：价格下穿 SuperTrend 通道
- 参数：atr_period, atr_mult

## 手续费模型

| 费用类型 | 买入 | 卖出 |
|------|------|------|
| 佣金 | 万三 | 万三 |
| 印花税 | -- | 千一 |
| 过户费 | 万零六 | 万零六 |
| **合计** | **3.6 BPS** | **13.6 BPS** |

## 绩效指标

| 指标 | 公式 |
|------|------|
| 总收益率 | $(W_e - W_0) / W_0$ |
| 超额收益 (Alpha) | 总收益率 $-$ 基准收益率 |
| 年化收益率 | $(W_e / W_0)^{252/T} - 1$ |
| 年化波动率 | $\sigma_{daily} \times \sqrt{252}$ |
| 最大回撤 | $\min \frac{P_t - \max P_s}{\max P_s}$ |
| 夏普比率 | $(R_{ann} - 0.03) / \sigma_{ann}$ |

## 回测输出

### 绩效报告

```
=======================================================
                   回测绩效报告
=======================================================
策略总收益率 (Total Return):        XX.XX%
基准总收益率 (Benchmark Return):    XX.XX%
超额收益 (Alpha):                   XX.XX%
------
年化收益率 (Annualized Return):     XX.XX%
年化波动率 (Annualized Volatility): XX.XX%
最大回撤 (Max Drawdown):            XX.XX%
夏普比率 (Sharpe Ratio):            X.XX
------
交易次数 (买入/卖出):               N / N
总手续费成本 (Trading Cost):          X.XXXXXX (XX.XX%)
  +-- 买入手续费:                     X.XXXXXX
  +-- 卖出手续费:                     X.XXXXXX
=======================================================
```

### 可视化

程序输出策略净值 vs 基准净值对比图：
- **红实线**：策略净值（扣手续费后）
- **蓝虚线**：标的基准净值

## 数据源对比

| 数据源 | 费用 | Token | 数据质量 | 场景 |
|------|------|------|------|-- ----|
| Baostock | 免费 | 不需要 | 良好 | 个人回测 / 教学 |
| Tushare Pro | 免费+付费 | 需要 | 极好 | 机构级研究 |
| AkShare | 免费 | 不需要 | 一般 | 快速探索 |

## 注意事项

- 未考虑**滑点**、**涨跌停**、**停牌**、**最低佣金 5 元**
- 手续费按固定费率计算，未随券商差异化
- 实际使用需要**参数扫描**和**样本外验证**
- 回测结果仅供参考，不构成投资建议
