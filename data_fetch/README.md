# data_fetch — A 股数据获取与本地化管理

数据层：从 baostock/akshare 拉取 A 股数据，持久化到 SQLite，支持全量/增量更新 + 健康检查。

## 快速开始

```bash
# 安装依赖
uv add baostock

# 初始化数据库（创建表结构）
data-fetch init

# 首次全量更新（股票列表 + 日线行情 + 财务数据 + 指数成分股）
data-fetch update --full

# 每日定时增量更新（仅拉取新增交易日数据）
data-fetch update --incremental

# 仅更新财务数据
data-fetch update --financial

# 仅更新指数成分股
data-fetch update --constituents

# 健康检查
data-fetch health
```

## 目录结构

```
data_fetch/
├── __init__.py           # 统一导出 fetcher 和常量
├── cli.py                # CLI 入口 (data-fetch)
├── db_schema.py          # 数据库表结构定义 (stock_data.db + factor_raw.db)
├── sqlite_store.py       # SQLiteStore: 连接管理 + CRUD + upsert + 迁移
├── daily_kline.py        # 日线行情 (baostock 主力 / akshare 备选)
├── financial_data.py     # 季度财务数据 (PE/PB/ROE/增速...)
├── index_constituents.py # 指数成分股 (沪深300/500/1000/上证50)
├── updater.py            # DataUpdater: 全量/增量/财务/成分股调度
└── cache_health.py       # 数据健康检查: 新鲜度/覆盖率/异常告警
```

## 数据库结构

`data/sqlite/stock_data.db` 包含 5 张表：

### stock_info — 股票基础信息

| 列             | 类型   | 说明                    |
| -------------- | ------ | ----------------------- |
| code           | TEXT PK | 股票代码 '000001.SZ'   |
| name           | TEXT   | 股票名称                |
| industry       | TEXT   | 申万一级行业            |
| listed_date    | TEXT   | 上市日期 'YYYY-MM-DD'   |
| delisted_date  | TEXT   | 退市日期 (NULL=未退市) |
| exchange       | TEXT   | 'SSE' / 'SZSE'         |
| board          | TEXT   | 'Main' / 'ChiNext'     |
| updated_at     | DATETIME | 最后更新时间          |

### index_constituents — 指数成分股

| 列             | 类型   | 说明                  |
| -------------- | ------ | --------------------- |
| index_code     | TEXT   | 指数代码 '000300.SH'  |
| stock_code     | TEXT   | 成分股代码            |
| effective_date | DATE   | 生效日期              |
| weight         | REAL   | 权重                  |

PK: (index_code, stock_code, effective_date)

### daily_kline — 日线行情

| 列          | 类型    | 说明             |
| ----------- | ------- | ---------------- |
| code        | TEXT    | 股票代码         |
| date        | DATE    | 交易日期         |
| open        | REAL    | 开盘价           |
| high        | REAL    | 最高价           |
| low         | REAL    | 最低价           |
| close       | REAL    | 收盘价           |
| preclose    | REAL    | 前收盘价         |
| volume      | REAL    | 成交量           |
| amount      | REAL    | 成交额           |
| adj_factor  | REAL    | 复权因子         |
| tradestatus | INTEGER | 交易状态 (0=正常) |
| pct_chg     | REAL    | 涨跌幅 (%)       |

PK: (code, date)

### financial_qtr — 季度财务数据

| 列             | 类型   | 说明                |
| -------------- | ------ | ------------------- |
| code           | TEXT   | 股票代码            |
| report_date    | DATE   | 报告期 (季报)       |
| publish_date   | DATE   | 披露日期 (防未来函数) |
| pe_ttm         | REAL   | PE(TTM)            |
| pb             | REAL   | PB                  |
| roe            | REAL   | ROE                 |
| net_profit_grow| REAL   | 净利润同比增速      |
| revenue_grow   | REAL   | 营收同比增速        |
| gross_margin   | REAL   | 毛利率              |
| net_margin     | REAL   | 净利率              |
| debt_to_asset  | REAL   | 资产负债率          |
| operating_cash | REAL   | 每股经营现金流      |

PK: (code, report_date)

### daily_market_cap — 每日市值

| 列             | 类型   | 说明          |
| -------------- | ------ | ------------- |
| code           | TEXT   | 股票代码      |
| date           | DATE   | 日期          |
| total_market_cap| REAL  | 流通市值      |
| total_mkt_cap  | REAL   | 总市值        |
| freely_turnover| REAL   | 换手率        |

PK: (code, date)

## 使用方式

### 1. 命令行

```bash
# 初始化
data-fetch init

# 增量更新
data-fetch update --incremental

# 全量更新 (首次使用)
data-fetch update --full

# 指定数据源和股票池
data-fetch update --full --pool hs300 --source baostock
```

### 2. Python API

```python
from data_fetch.sqlite_store import SQLiteStore
from data_fetch.daily_kline import fetch_daily_kline_baostock
from data_fetch.updater import run_full_update, run_incremental_update
from data_fetch.cache_health import check_health

# ----- 数据库操作 -----
store = SQLiteStore("data/sqlite/stock_data.db")
store.init_schema()  # 创建表

# 查询
df = store.query_df("SELECT * FROM daily_kline WHERE code = '000001.SZ'")

# upsert
df_new = fetch_daily_kline_baostock("600519.SH", "2025-01-01", "2025-01-31")
store.upsert_from_df(df_new, "daily_kline")

# 辅助方法
latest = store.get_latest_date("daily_kline", "000001.SZ")
codes = store.get_all_codes("stock_info")

store.close()

# ----- 一键更新 -----
run_full_update("data/sqlite/stock_data.db")
stats = run_incremental_update("data/sqlite/stock_data.db")

# ----- 健康检查 -----
check_health("data/sqlite/stock_data.db")
```

### 3. 直接调用 fetcher

```python
from data_fetch.daily_kline import fetch_daily_kline_baostock, fetch_daily_kline_akshare
from data_fetch.financial_data import fetch_financial_qtr, fetch_fin_valuation
from data_fetch.index_constituents import (
    INDEX_MAP, fetch_index_constituents,
    fetch_historical_constituents
)

# 个股日线 (不复权)
df = fetch_daily_kline_baostock("000001.SZ", "2024-01-01", "2024-12-31")

# 个股财务
df_fin = fetch_financial_qtr("000001.SZ", "2020-01-01", "2024-12-31")

# 沪深300成分股
df_hs300 = fetch_historical_constituents("hs300", "2020-01-01", "2024-12-31")
```

## 常量

| 常量              | 说明                  |
| ----------------- | --------------------- |
| `KLINE_FIELDS`    | 日线 12 字段名列表    |
| `FINANCIAL_FIELDS`| 财务 baostock 字段名  |
| `INDEX_MAP`       | {"hs300": "000300.SH", "zz500": "000905.SH", "zz500": "000905.SH", "zz1000": "000852.SH", "hs50": "000016.SH"} |
| `INDEX_NAMES`     | 反向映射 {code: key}  |

## 数据源

| 数据源    | 状态   | 费用   | 说明                  |
| --------- | ------ | ------ | --------------------- |
| baostock  | 主力   | 免费   | 无需 Token，稳定      |
| akshare   | 备选   | 免费   | 需 `uv add akshare`   |

## 数据更新策略

- **首次**: `update --full` — 拉取 1990-至今全量数据
- **日常**: `update --incremental` — 只拉新增交易日
- **增量逻辑**: 从已有最大日期 +1 天拉取到最新交易日
- **失败容忍**: 单只股票失败不影响整体，最多记录前 10 只错误日志
- **进度日志**: 每 100 只股票输出一次进度

## 健康检查

`check_health` 输出：

- **数据新鲜度**: 最新日期距今天的差距 (超过 7 天告警)
- **股票总数**: stock_info 表记录数
- **最小数据天数**: 数据最少股票的覆盖天数 (< 10 天告警)
- **异常涨跌**: 单日涨跌幅 >15% (非涨停/跌停状态) 的股票

## 技术细节

- 日期格式统一 `'YYYY-MM-DD'`
- 股票代码格式 `'000001.SZ'` / `'600519.SH'`
- SQLite WAL 模式 (提升并发写入性能)
- 自动创建 `data/sqlite/` 目录
- Python 内置 `sqlite3`，零额外依赖
