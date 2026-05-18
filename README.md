# A股量化策略回测框架

A 股量化策略回测框架，支持多数据源接入、多策略切换、手续费建模、绩效分析和净值可视化。

## 功能特性

- **多数据源**：支持 Baostock（默认）、AkShare、Tushare 三种数据源，通过配置项 `DATA_SOURCE` 一键切换
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
uv sync --extra akshare    # AkShare 数据源
uv sync --extra tushare    # Tushare 数据源
```

## 运行回测

### 默认运行

```bash
uv run main.py
```

默认使用 **Baostock** 数据源 + **双均线策略**。

### 切换策略与数据源

在 `main.py` 中修改配置项：

```python
# main.py
DATA_SOURCE = "akshare"    # 可选: baostock | akshare | tushare
STRATEGY_NAME = "macd"     # 可选: dual_ma | bollinger | macd | supertrend
TUSHARE_TOKEN = "your-token"  # 使用 tushare 时需要
```

- **Baostock**（默认）：无需 Token，开箱即用
- **AkShare**：`uv sync --extra akshare` 安装
- **Tushare**：需注册获取 Token，`uv sync --extra tushare` 安装

### 自定义策略

```python
from backtest.strategy import DualMaStrategy, BollingerStrategy, MacdStrategy, SuperTrendStrategy

# 双均线
strategy = DualMaStrategy(short=5, medium=20)

# 布林带
strategy = BollingerStrategy(window=20, std_dev=2.0)

# MACD
strategy = MacdStrategy(fast_period=12, slow_period=26, signal_period=9)

# SuperTrend
strategy = SuperTrendStrategy(atr_period=10, atr_mult=3.0)

# 执行
df = strategy.compute(df)  # df 必须包含 close 列，返回中添加 signal 列
```

## 架构设计

```
quantitive-trading/
├── backtest/                    # 核心回测模块
│   ├── __init__.py
│   ├── constants.py             # 费率、交易日、数据源配置等常量
│   ├── engine.py                # 回测引擎：持仓/收益/成本/绩效指标
│   ├── plotter.py               # 净值曲线可视化
│   ├── data_feed.py             # 统一数据获取入口
│   ├── strategy/                # 策略模块（每个策略独立文件）
│   │   ├── __init__.py          # 统一导出所有策略
│   │   ├── base.py              # BaseStrategy 抽象基类 + StrategyConfig
│   │   ├── dual_ma.py           # 双均线策略
│   │   ├── bollinger.py         # 布林带策略
│   │   ├── macd.py              # MACD 策略
│   │   └── supertrend.py        # SuperTrend 策略
│   ├── datafeed/                # 多数据源适配器
│   │   ├── __init__.py
│   │   ├── base.py              # AbstractDataSource 抽象基类
│   │   ├── baostock.py          # Baostock 适配器（默认）
│   │   ├── akshare.py           # AkShare 适配器
│   │   ├── tushare.py           # Tushare Pro 适配器
│   │   └── resolver.py          # 数据源解析器（factory + registry）
│   └── indicator/               # 技术指标（扩展）
│       └── __init__.py
├── docs/
│   └── data_source_selection.md  # 数据源选型记录
├── main.py                      # 入口：编排数据 → 策略 → 回测 → 报告 → 绘图
├── pyproject.toml               # 项目配置与依赖
└── uv.lock                      # uv 依赖锁文件
```

### 新建策略

继承 `BaseStrategy` 实现 `compute()` 方法：

```python
from backtest.strategy import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    name = "my_strategy"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        # 在 df 中添加 signal 列，取值 [0, 1]
        df["signal"] = ...
        return df
```

### 新建数据源

继承 `AbstractDataSource` 实现 `fetch()` 方法：

```python
from backtest.datafeed import AbstractDataSource, register_data_source
import pandas as pd

class MyDataSource(AbstractDataSource):
    def fetch(self, code: str, start: str, end: str, adjust: str | None) -> pd.DataFrame:
        # 返回列名 [open, high, low, close, volume] 的 DataFrame
        ...

register_data_source("my", MyDataSource)
```

各模块职责：

| 模块 | 职责 |
|------|------|
| `datafeed/base.py` | `AbstractDataSource` 抽象基类，定义 fetch() 接口 |
| `datafeed/baostock.py` | Baostock 数据源适配器（默认） |
| `datafeed/akshare.py` | AkShare 数据源适配器 |
| `datafeed/tushare.py` | Tushare Pro 数据源适配器 |
| `datafeed/resolver.py` | 数据源解析器（工厂模式 + 注册表），支持通过配置切换 |
| `data_feed.py` | `fetch_stock_data(source=...)` — 统一数据获取入口 |
| `strategy/base.py` | `BaseStrategy` 策略基类，子类实现 compute() |
| `strategy/*.py` | 独立策略实现文件 |
| `engine.py` | `run_backtest()` 建持仓/收益，`calc_performance()` 计算夏普/回撤等 |
| `plotter.py` | `plot_backtest()` 净值图 |
| `constants.py` | 费率、交易日等常量统一收敛 |

设计原则：各模块通过 DataFrame 接口解耦，策略和回测引擎完全独立于数据源，可插拔替换。

## 内置策略说明

### 双均线策略 (dual_ma)

- **买入信号**：短期均线穿越长期均线上方
- **卖出信号**：短期均线穿越长期均线下方
- **参数**：`short`（短周期）、`medium`（长周期）、`ma_type`（sma/ema）
- **可选**：固定止损、追踪止损、仓位管理、成交量过滤

### 布林带策略 (bollinger)

- **买入信号**：价格下穿下轨
- **卖出信号**：价格上穿上轨
- **参数**：`window`（均线周期）、`std_dev`（标准差倍数）

### MACD 策略 (macd)

- **买入信号**：DIF 金叉 DEA
- **卖出信号**：DIF 死叉 DEA
- **参数**：`fast_period`（12）、`slow_period`（26）、`signal_period`（9）

### SuperTrend 策略 (supertrend)

- **买入信号**：价格上穿 SuperTrend 通道
- **卖出信号**：价格下穿 SuperTrend 通道
- **参数**：`atr_period`（ATR 周期）、`atr_mult`（ATR 乘数）

## 手续费模型

| 费用类型 | 买入 | 卖出 | 说明 |
|------|------|------|------|
| 佣金 | 万三 | 万三 | A 股双向收取 |
| 印花税 | — | 千一 | 仅卖出收取 |
| 过户费 | 万零六 | 万零六 | A 股双向收取 |
| **合计** | **3.6 BPS** | **13.6 BPS** | 基于仓位价值计算 |

## 回测输出

### 绩效报告

```
=======================================================
                   回测绩效报告
=======================================================
策略总收益率 (Total Return):        XX.XX%
基准总收益率 (Benchmark Return):    XX.XX%
超额收益 (Alpha):                   XX.XX%
-------------------------------------------------------
年化收益率 (Annualized Return):     XX.XX%
年化波动率 (Annualized Volatility): XX.XX%
最大回撤 (Max Drawdown):            XX.XX%
夏普比率 (Sharpe Ratio):            X.XX
-------------------------------------------------------
交易次数 (买入/卖出):               N / N
总手续费成本 (Trading Cost):          X.XXXXXX (XX.XX%)
  ├─ 买入手续费:                     X.XXXXXX
  └─ 卖出手续费:                     X.XXXXXX
=======================================================
```

### 可视化

程序输出策略净值曲线 vs 基准净值对比图：

- **红实线**：策略净值（扣除手续费后）
- **蓝虚线**：标的基准净值

## 数据源对比

| 数据源 | 费用 | Token | 数据质量 | 推荐场景 |
|------|------|------|------|------|
| Baostock | 完全免费 | 不需要 | 良好 | 个人回测 / 教学 |
| Tushare Pro | 免费(基础) + 付费(进阶) | 需要（积分制） | 极好 | 机构级 / 深度研究 |
| AkShare | 免费 | 不需要 | 一般（接口波动） | 快速探索 / 通用 |

详细记录见 [docs/data_source_selection.md](docs/data_source_selection.md)。

## 注意事项

- 当前为简化版回测，未考虑**滑点**、**涨跌停限制**、**停牌**、**最低佣金 5 元**等因素
- 策略参数为示例值，实际使用需要**参数扫描**和**样本外验证**
- 手续费按固定费率计算，未随券商差异化调整
- 回测结果仅供参考，不构成投资建议
