# 多因子选股模型回测框架：规划方案

> **状态**：规划阶段，尚未开始开发
> **创建时间**：2025-05-19
> **范围**：数据层 + 因子层 + 组合回测引擎，不包含底层交易规则修改 TODO

---

## 一、需求总结

当前框架：**单标的 → 策略 → 回测 → 指标**。每次只跑一只股票。

目标：**全市场选股 → 多因子打分 → 组合回测 → 绩效归因**。

核心需求：
1. **数据本地化**：拉取接口数据存入 SQLite，回测从 SQLite 读取。不每次重复请求 API。
2. **增量更新**：支持全量更新 + 增量更新（新增交易日/新上市股票自动拉取）。
3. **多因子计算**：技术面/基本面/另类因子，可插拔，计算结果存库。
4. **组合回测**：全市场评分选股，定期调仓，多股持有，仓位可分配。
5. **绩效归因**：因子贡献度分析，行业/市值风格偏误检测。

---

## 二、目录结构

```
quantitive_trading/
├── main.py                            # 单标的回测（保持不变）
├── pyproject.toml
│
├── data/
│   └── sqlite/
│       ├── stock_data.db              # 行情 + 基础信息
│       ├── factor_raw.db              # 因子原始计算值
│       └── portfolio.db               # 组合持仓/交易记录 (回测阶段生成)
│
├── data_fetch/                        # ┌─ 数据层（新增）
│   ├── __init__.py                    # │
│   ├── sqlite_store.py                # │ SQLite 连接池 + 建表/迁移
│   ├── db_schema.py                   # │ schema 定义 + migrations
│   ├── base_downloader.py             # │ AbstractDownloader
│   ├── baostock_client.py             # │ baostock 接口
│   ├── akshare_client.py              # │ akshare 接口
│   ├── tushare_client.py              # │ tushare 接口
│   ├── stock_info.py                  # 股票基础信息（代码/名称/板块/上市日/退市日）
│   ├── index_constituents.py          # 指数成分股历史（沪深300/500/1000）
│   ├── daily_kline.py                 # 日线行情（OHLCV + adj_factor + tradestatus）
│   ├── financial_data.py              # 财务数据（PE/PB/ROE/净利增速...）
│   ├── market_caps.py                 # 每日市值数据
│   ├── updater.py                     # 统一调度：全量/增量/健康检查/异常修复
│   └── cache_health.py                # 覆盖率校验、缺失检测、数据新鲜度告警
│
├── factors/                           # ┌─ 因子层（新增）
│   ├── __init__.py                    # │
│   ├── base.py                        # │ FactorBase 抽象基类 + FactorConfig
│   ├── registry.py                    # │ 因子注册表（discover + register）
│   ├── engine.py                      # │ 因子计算引擎（DataFrame 批量计算 + DB 落库）
│   │                              # │ 依赖排序（因子 B 可能依赖因子 A 的结果）
│   │                              # │ 增量计算：只算新增交易日和新增股票
│   │                              # │ 版本化：每次计算生成 factor_version_id
│   ├── technical/                     # │ 技术面因子（无外部数据依赖）
│   │   ├── __init__.py
│   │   ├── momentum.py                # │ 动量：20/60/120 日收益率、价格/ATR
│   │   ├── reversal.py                # │ 反转：短期价格反转、RSI
│   │   ├── volatility.py              # │ 波动率：20/60 日波动、已实现波动率
│   │   ├── volume.py                  # │ 量价：量比、换手率、量价相关性
│   │   ├── trend.py                   # │ 趋势：均线发散、ADX、MACD 强度
│   │   └── mean_reversion.py          # │ 均值回归：布林带宽、偏离度
│   ├── fundamental/                   # │ 基本面因子（依赖财务数据）
│   │   ├── __init__.py
│   │   ├── profitability.py           # │ ROE、ROA、毛利率、净利率
│   │   ├── growth.py                  # │ 营收增速、净利增速、EPS 增速
│   │   ├── valuation.py               # │ PE/PB/PS/EV/EBITDA
│   │   ├── quality.py                 # │ 应占率、资产周转率、现金流质量
│   │   └──investment.py               # │ 固定资产周转、无形资产比
│   ├── alternative/                   # │ 另类因子
│   │   ├── __init__.py
│   │   └── market_structure.py        # │ 市值因子（流通市值/总市值）、换手率偏误
│   └── composite/                     # │ 复合因子
│       ├── __init__.py
│       └── alphafactor.py             # │ 多因子合成（等权/IC加权/PCA）
│
├── backtest/                          # ┌─ 回测层（重大扩展）
│   ├── engine.py                      # │ 现有单标的回测（不变）
│   ├── strategy/                      # │ 现有策略（不变）
│   └── multifactor/                   #   新增：多因子组合回测
│       ├── __init__.py
│       ├── portfolio.py               #   Portfolio 类：持仓/现金/权重
│       ├── rebalancer.py              #   调仓逻辑（日/周/月，等权/市值/IC加权）
│       ├── backtester.py              #   多标的回测核心：选股 → 建仓 → 调仓
│       ├── performance.py             #   多标的绩效：组合级夏普/Calmar/回撤
│       ├── attribution.py             #   因子归因：Brinson 归因 + 因子贡献分解
│       └── risk/                      #   风险分析
│           ├── __init__.py
│           ├── drawdown.py            #   最大回撤/波动的计算
│           └── style.py               #   风格偏误检测（市值/行业暴露）
│
├── docs/
│   ├── todos/                         # 现有 TODO
│   ├── performance_guide.md           # 现有绩效指南
│   └── plans/
│       └── multi_factor_backtest_framework.md  # 本文件
```

---

## 三、数据层设计

### 3.1 SQLite schema（stock_data.db）

```sql
-- 股票基础信息
CREATE TABLE IF NOT EXISTS stock_info (
    code          TEXT PRIMARY KEY,   -- '000001.SZ'
    name          TEXT,
    industry      TEXT,               -- 申万一级行业
    listed_date   TEXT,               -- '20****-**-**'
    delisted_date TEXT,               -- NULL = 未退市
    exchange      TEXT,               -- 'SSE' / 'SZSE'
    board         TEXT,               -- 'Main' / 'ChiNext' / 'STAR' / 'BSE'
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 指数成分股历史（沪深300/中证500，解决成分股变化导致的幸存者偏置）
CREATE TABLE IF NOT EXISTS index_constituents (
    index_code    TEXT,              -- '000300.SH'
    stock_code    TEXT,
    effective_date TEXT,             -- 生效日期（成分调整日）
    weight        REAL,              -- 权重（可选，0.04 表示 4%）
    PRIMARY KEY (index_code, stock_code, effective_date)
);
CREATE INDEX idx_index_const_date ON index_constituents(index_code, effective_date);

-- 日线行情
CREATE TABLE IF NOT EXISTS daily_kline (
    code          TEXT,              -- '000001.SZ'
    date          DATE,              -- 'YYYY-MM-DD'
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    preclose      REAL,
    volume        REAL,
    amount        REAL,
    adj_factor    REAL,              -- 复权因子
    tradestatus   INTEGER,           -- 0=正常、1=停牌、2=涨跌停、3=退市
    pct_chg       REAL,
    PRIMARY KEY (code, date)
);
CREATE INDEX idx_kline_code ON daily_kline(code);

-- 财务数据（季报频率）
CREATE TABLE IF NOT EXISTS financial_qtr (
    code          TEXT,
    report_date   DATE,              -- 报告日期（季报）
    publish_date  DATE,              -- 披露日期（用于避免未来函数！）
    pe_ttm        REAL,
    pb            REAL,
    roe           REAL,
    net_profit_grow REAL,            -- 净利润同比增速
    revenue_grow  REAL,              -- 营收同比增速
    gross_margin  REAL,
    net_margin    REAL,
    debt_to_asset REAL,
    operating_cash REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX idx_fin_code ON financial_qtr(code);

-- 每日市值
CREATE TABLE IF NOT EXISTS daily_market_cap (
    code          TEXT,
    date          DATE,
    total_market_cap REAL,            -- 流通市值
    total_mkt_cap REAL,              -- 总市值
    freely_turnover REAL,            -- 换手率
    PRIMARY KEY (code, date)
);
```

### 3.2 SQLite schema（factor_raw.db）

```sql
-- 因子计算值（按 version 分组）
CREATE TABLE IF NOT EXISTS factor_versions (
    version_id    TEXT PRIMARY KEY,    -- 'v20250519_001'
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    description   TEXT                 -- 计算说明
);

CREATE TABLE IF NOT EXISTS factor_data (
    version_id    TEXT,
    code          TEXT,
    date          DATE,
    factor_name   TEXT,
    factor_value  REAL,
    status        TEXT,                -- 'valid' / 'nan' / 'outlier'
    PRIMARY KEY (version_id, code, date, factor_name)
);
CREATE INDEX idx_factor_date_name ON factor_data(date, factor_name);
```

### 3.3 数据更新策略

```
data_fetch/updater.py:

调度逻辑（crontab / CLI 一次性执行）：
  1. 全量更新：拉取所有股票 + 所有历史数据
  2. 增量更新（每日）：只拉取最新交易日数据
  3. 财务数据更新：季度更新
  4. 成分股更新：月度/季度更新沪深300等

增量更新流程：
  for code in all_stocks:
    existing = db.query("SELECT max(date) WHERE code=? GROUP BY code")
    start_date = existing + 1 day
    kline = api.query(code, start_date, today)  # 只拉增量
    db.upsert(daily_kline, kline)
    
  # 增量计算：只计算新增日期 + 涉及因子
  for factor_name, factor_obj in registry:
    factor_obj.partial_compute(start_date=today, codes=all_stocks)
    
  # 因子数据增量更新
  factor_df = factor_obj.compute(start_date=today)  # pandas.DataFrame
  factor_store.upsert(factor_df)
```

### 3.4 数据健康检查

```python
cache_health.py:

- 股票覆盖率：每个交易日有多少股票有数据（应 > 4000）
- 缺失检测：连续停牌超过 X 日标记告警
- 数据新鲜度：最新数据日期 vs 当前日期
- 数据一致性：前复权价格 vs 原始价格换算验证
- 异常检测：当日涨跌幅 > 15% 的股票（非ST）标记
```

---

## 四、因子层设计

### 4.1 因子抽象基类

```python
# factors/base.py

@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    description: str
    requires: list[str]          # 依赖的其他因子（如 BOLL 依赖 MA）
    need_raw_data: bool = True   # 是否需要原始行情
    need_financial: bool = True  # 是否需要财务数据
    lookback_days: int = 250     # 回看窗口
    output_name: str | None = None  # 输出列名（默认 name）

class Factor(ABC):
    """因子基类"""
    name: str
    depends: Sequence[str]       # 依赖的其他因子

    def __init__(self, config: FactorConfig | None = None):
        self.config = config or FactorConfig(name=self.name)

    @abstractmethod
    def compute(self, df: pd.DataFrame, db: SQLiteStore) -> pd.Series:
        """输入 DataFrame(含 OHLCV)，输出 Factor.Series
    
    def partial_compute(self, codes: list[str], start_date: str, db: SQLiteStore):
        # 增量计算钩子
        ...

    # 标准化（横截面 Z-Score / 去极值）
    def normalize(self, s: pd.Series, method: str = 'zscore') -> pd.Series:
        ...
```

### 4.2 因子计算引擎

```python
# factors/engine.py

class FactorEngine:
    """因子计算引擎
    
    特点：
    1. 依赖排序：拓扑排序，先算 MA 再算 MACD
    2. 批量计算：一次性对全市场计算，利用 DataFrame.apply/groupby
    3. 增量计算：只算新增日期的因子
    4. 版本化：每次生成新的 version_id
    5. 缓存：已计算的因子结果存 DB，不重复计算
    """

    def compute_all(self, codes: list[str], start_date: str, end_date: str, 
                    factor_names: list[str], version: str, db: SQLiteStore) -> dict:
        # 拓扑排序因子依赖
        topo = self.topological_sort(factor_names)
        
        results = {}
        for fname in topo:
            factor = registry.get(fname)
            deps = factor.depends
            
            # 检查依赖因子是否已计算
            dep_results = {d: results[d] for d in deps}
            df = db.fetch(daily_kline, codes, start_date, end_date)
            
            if df.empty:
                continue
                
            # 计算
            values = factor.compute(df)  # pd.Series
            factor_store.upsert(
                version=version, factor_name=fname, values=values
            )
            results[fname] = values
            
        return results
```

### 4.3 因子清单（建议第一批实现）

| 分类 | 因子代码 | 因子名称 | 说明 | 依赖 |
|------|------|------|------|------|
| **动量** | MOM_20D | 20日动量 | 20日收益率 | 无 |
| | MOM_60D | 60日动量 | 60日收益率 | 无 |
| | MOM_120D | 120日动量 | 120日收益率 | 无 |
| | PRICE_TO_ATR | 价格/ATR | 价格相对波动幅度 | volatility_ATR_14 |
| **反转** | REV_5D | 5日反转 | 短期均值回归 | 无 |
| | REV_20D | 20日反转 | 中期均值回归 | 无 |
| | RSI_14 | RSI(14) | 相对强弱指数 | volatility_ATR_14 |
| **波动** | VOL_20D | 20日波动率 | 已实现波动率 | 无 |
| | VOL_60D | 60日波动率 | 长期波动率 | 无 |
| | BOLL_BAND | 布林带宽度 | 波动区间变化 | ma_均线 |
| | SKew_20 | 收益偏度 | 尾部风险 | momentum |
| **量价** | VOL_RATIO | 量比 | 当日/20日均量 | 无 |
| | TURN_RATE | 换手率 | 流通市值换手 | market_cap |
| | VOL_PR_CORR | 量价相关 | 20日量价相关性 | |
| | AMIHUD | 流动性（Amihud） | 收益/成交额 | volume |
| **趋势** | MA_DIVER | 均线发散度 | MA5/MA20 差值百分比 | ma_均线 |
| | ADX_14 | 趋势强度 | 平均方向指数 | volatility_ATR_14 |
| | MACD_SIGNAL | MACD信号强度 | DIF/DEA 偏离度 | momentum |
| **基本面** | ROE_TTM | ROE(TTM) | 总资产收益率 | financial_qtr |
| | PE_TTM | 市盈率 | 滚动市盈率 | |
| | PB | 市净率 | 市净率 | |
| | GROSS_MARGIN | 毛利率 | 毛利润/营业收入 | |
| | REV_GROW | 营收增速 | 营收同比增速 | |
| | NP_GROW | 净利增速 | 净利同比增速 | |
| | Q_OPS_CASH | 经营现金流质量 | 经营现金流净利润比 | |
| | INV_TURNOVER | 存货周转率 | 营业成本/存货 | |
| **市值** | MARKET_CAP | 市值 | 流通市值（亿） | daily_market_cap |
| | MARKET_CAP_RANK | 市值排位 | 全市场百分位排名 | |
| | LIQUIDITY | 日均成交额 | 过去 20 天日均成交额 | volume |
| **复合** | ALPHA_1 | 等权多因子 | 等权合成技术因子 | |
| | ALPHA_2 | IC加权多因子 | IC加权合成 | |

### 4.4 因子计算中的关键注意事项

1. **财报披露延迟**：
   - ROE 是季报数据，披露时存在 **滞后**
   - 财报披露日（publish_date）可能晚于报告日（report_date）
   - **必须用披露日计算，而非报告日**，否则有未来函数

2. **停牌/涨跌停处理**：
   - 计算因子时跳过停牌日
   - 停牌期间值延续上一个有效值还是填 NaN？→ 建议填 NaN
   - 涨跌停股票不纳入因子计算（如换手率因子需排除涨跌停股票）

3. **横截面标准化**（去极值 + Z-Score）：
   ```python
   # 截面 Z-Score
   factor_z = (x - x.mean(axis=0)) / x.std(axis=0)
   
   # 去极值（MAD）
   median = x.median(axis=0)
   mad = np.abs(x - median).median(axis=0)
   factor_cleaned = x.clip(median - 3*mad*1.4826, median + 3*mad*1.4826)
   
   # 中性化（可选）
   # 回归：factor = beta * industry_dummy + noise
   ```

4. **因子合成**（多因子合成一个综合打分）：
   - **等权法**：所有因子权重相同 → 最简单
   - **IC加权法**：因子信息系数（信息比率）越大 → 历史表现越好
   - **PCA 降噪**：对高度相关因子做主成分分析 → 降维
   - **回归最优**：对每个因子回归未来收益率，取回归系数

---

## 五、组合回测引擎设计

### 5.1 backtester.py

```python
# backtest/multifactor/backtester.py

class MultiFactorBacktest:
    """多因子组合回测器
    
    用法示例：
        engine = MultiFactorBacktest(
            portfolio=Portfolio(starting_cash=1_000_000),
            stock_pool='all_a',           # 'hs300' / 'zz500' / 'all_a'
            rebalance_freq='M',           # 'W'/'M'/'Q'
            factor_weights=None,           # None = 等权, dict = 自定义权重
            position_weight='equal',       # 'equal' / 'market_cap' / 'ic_weighted'
            n_stocks=50,                   # 持有股票数
            max_single_stock=10,           # 单股最大权重 %
            trading_rules=TRADING_RULES,   # 滑点、涨跌停、T+1 等
            start_date='2020-01-01',
            end_date='2023-12-31'
        )
        result = engine.run()
    """

    def run(self) -> PortfolioResult:
        # 1. 计算全市场因子
        factors = self.factor_engine.compute_all(
            codes=self.stock_pool.codes,
            start=self.start_date,
            end=self.end_date
        )
        
        # 2. 合成因子打分
        scores = self.score_composite(factors)  # 每只股票一个综合分
        
        # 3. 按日遍历（事件驱动逐行）
        for date in trading_days:
            if not self._is_rebalance_day(date): continue
            
            stocks = self._top_n_stocks(scores[date], n=self.n_stocks)
            
            for stock in stocks:
                self._rebalance_portfolio(date, stock, target_weight)
            
        return self._build_result()
    
    def _rebalance_portfolio(self, date: str, stock: str, target_weight: float):
        # 当前持仓：
        # for existing_stock in portfolio.holdings:
        #     if existing == stock and weight ≈ target: continue
        #     portfolio.sell(existing_stock, full_position)  # 先卖出旧仓
        
        # 现金分配，考虑最小交易单位（100股）
        alloc_amount = portfolio.cash * target_weight
        shares = int(alloc_amount * (1 - slippage) / price / 100) * 100
        
        cost = self._calc_cost(shares, price, side='buy')
        portfolio.buy(stock, shares, price, cost)
```

### 5.2 回测规则（结合 TODO 清单修正）

在回测引擎中集成之前 TODO 文档中列出的修正项：

```python
class TradingRules:
    """交易规则配置（从 TODO 逐项实现）"""
    
    SLIPPAGE_RATE = 0.001          # 滑点 0.1%
    MIN_COMMISSION = 5.0           # 最低佣金 5 元
    MIN_TRADING_UNIT = 100         # 最小 1 手
    LIMIT_UP_RATIO = 0.10          # 涨跌停比例
    LIMIT_UP_RATIO_CREAT = 0.20    # 科创板/创业板
    T_PLUS_1 = True                # T+1 约束
    
    def can_trade(self, stock: str, date: str, side: str) -> bool:
        if self._is_suspended(stock, date): return False
        if self._is_limit_up_or_down(stock, date, side): return False
        if self._t_plus_1_check(stock, date, side): return False
        return True
```

---

## 六、数据维护方案详解

### 6.1 updater.py 的调度方式

```
数据更新入口：data_fetch/updater.py / cli: data_fetch/cli.py

CLI 命令：
  $ python -m data_fetch update --full         # 全量更新（首次）
  $ python -m data_fetch update --incremental   # 增量更新（每日自动）
  $ python -m data_fetch update --financial     # 财务数据更新
  $ python -m data_fetch update --constituents  # 指数成分股更新
  $ python -m data_fetch health                 # 数据健康检查
```

### 6.2 存储方式选择

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|-----|
| SQLite 存全部 | 简单，一次读取，兼容好 | 磁盘占用大，查询性能中等 | ✅ 推荐首期 |
| SQLite 行情 + Parquet 存因子数据 | 因子数据量大，Parquet 读写快，列压缩 | 多文件管理 | ✅ 推荐二期 |
| 全部 Parquet | 性能最优，支持分布式 | 多文件碎片化，增量更新复杂 | 长期可选 |

**推荐：首期用 SQLite，因子数据量大后迁移 Parquet + SQLite schema 混合方案。**

### 6.3 数据更新流程（全量）

```
全量更新流程（updater.py）：

第1步：获取股票池
  → 拉取所有 A 股上市/退市信息 → stock_info 表

第2步：获取成分股历史
  → 拉取沪深300/中证500成分股历史 → index_constituents 表
  → 用于回测选股池（解决幸存者偏置）

第3步：拉取全部日线行情 → daily_kline 表
  API: baostock.query_history_k_data_plus(code, start='1990-01-01', end=today)
  或 akshare.stock_zh_a_hist(symbol=code, period='daily')
  → 按 code/date 唯一键 upsert

第4步：拉取财务数据 → financial_qtr 表（季报频率）
  → 拉取 PE/PB/ROE/净利增速...
  → 注意：财报有披露延迟，用 publish_date 而非 report_date

第5步：拉取市值数据 → daily_market_cap 表

第6步：因子计算 → factor_raw.db
  → 运行 FactorEngine.compute_all()
  → 所有因子按 version_id 分组存储

第7步：数据健康检查
  → 覆盖率、缺失数、涨跌幅异常
  → 输出健康报告
```

### 6.4 数据更新流程（增量/每日自动）

```
增量更新流程（每日）：

第1步：检查最新交易日
  latest_date = SELECT MAX(date) FROM daily_kline GROUP BY code  → 取最大
  if latest_date < today:  # 有增量
    for code in active_stocks:
      kline = api.query(code, latest_date+1, today)  # 只拉增量
      db.upsert(daily_kline, kline)
  else:
    skip.  # 没有增量

第2步：拉取新上市股票的基本信息
  每日新上市的公司

第3步：计算最新日期的因子值
  FactorEngine.partial_compute(start_date=new_date, codes=all_codes)

第4步：更新成分股（季度）
  沪深300/500 指数成分每年调整 ~2 次，定期更新
```

### 6.5 调度方式

```bash
# 方式一：crontab（最简单）
# 每日 16:30（收盘后）自动增量更新
30 16 * * 1-5 cd /path/quantitive_trading && python -m data_fetch update --incremental

# 方式二：uv task 一键运行（手动触发）
# pyproject.toml 中配置
[project.scripts]
data-fetch = "data_fetch.cli:cli"

# 方式三：Docker + cron（容器化部署）
```

---

## 七、回测数据读取接口

回测时从 SQLite 读取，不直接调 API：

```python
# 统一数据读取接口：不再通过 API 请求，而是通过 SQLiteStore 读取
from data_fetch.sqlite_store import SQLiteStore

store = SQLiteStore("data/sqlite/stock_data.db")

# 回测入口接口：MultiFactorDataFeed
# 从 SQLite 读取，封装 DataFrame 接口，对上层透明

class MultiFactorDataFeed:
    """统一数据喂养接口（回测期只读 SQLite）"""
    
    def __init__(self, db_path: str):
        self.store = SQLiteStore(db_path)
    
    def fetch_daily_kline(self, codes: list[str], start: str, end: str) -> pd.DataFrame:
        """返回 DataFrame，列含 [date, code, open, high, low, close, volume, adj_factor]"""
        return self.store.query_daily_kline(codes, start, end)
    
    def fetch_factor_scores(self, version_id: str, codes: list[str]) -> pd.DataFrame:
        """返回 DataFrame: [code, date, factor_name, factor_value]"""
        return self.store.query_factors(version_id, codes)
    
    def fetch_financial(self, codes: list[str], max_report_date: str) -> pd.DataFrame:
        """财务数据：用 max_report_date 避免未来函数"""
        return self.store.query_financial(codes, max_report_date)
    
    def fetch_market_cap(self, codes: list[str], start: str, end: str) -> pd.DataFrame:
        return self.store.query_market_cap(codes, start, end)
```

---

## 八、开发优先级与里程碑

| 阶段 | 里程碑 | 工作内容 | 预计工作量 |
|------|------|------|------|
| **Phase 1** | 数据层搭建 | SQLite schema + SQLite 更新器 + 数据健康检查 | ~1 周 |
| **Phase 2** | 因子层搭建 | FactorBase + 引擎 + 首批因子 | ~2 周 |
| **Phase 3** | 组合回测 | portfolio.py + rebalancer.py + backtester.py | ~2 周 |
| **Phase 4** | 绩效归因 | attribution.py + risk 分析 + 归因报告 | ~1 周 |
| **Phase 5** | 数据质量 | 成分股历史 + 幸存者修正 + 健康检查 | ~1 周 |
| **Phase 6** | CLI 与文档 | 命令行 + docs/ + 示例 | ~0.5 周 |

### Phase 1: 数据层（最关键的基础）

| 文件 | 功能 |
|------|------|
| `data_fetch/db_schema.py` | 定义全部表结构 |
| `data_fetch/sqlite_store.py` | CRUD + upsert + 迁移 |
| `data_fetch/updater.py` | 全量 + 增量调度 |
| `data_fetch/daily_kline.py` | 日线行情拉取 |
| `data_fetch/financial_data.py` | 财务数据 |
| `data_fetch/index_constituents.py` | 指数成分股历史 |
| `data_fetch/cache_health.py` | 覆盖率/完整度/时效性校验 |
| `data_fetch/cli.py` | CLI 入口 |

### Phase 2: 因子层

| 文件 | 功能 |
|------|------|
| `factors/base.py` | Factor 基类 + 标准化 |
| `factors/registry.py` | 因子注册发现机制 |
| `factors/engine.py` | 因子计算引擎 |
| `factors/technical/` | 8-10 个技术因子 |
| `factors/fundamental/` | 5-6 个基本面 |
| `factors/composite/` | 等权/IC加权合成 |

### Phase 3: 组合回测

| 文件 | 功能 |
|------|------|
| `backtest/multifactor/portfolio.py` | Portfolio 状态（持仓/现金/成本）|
| `backtest/multifactor/rebalancer.py` | 调仓策略实现 |
| `backtest/multifactor/backtester.py` | 多标的事件驱动回测核心 |
| `backtest/multifactor/performance.py` | 组合绩效（日频净值 + 绩效指标）|
| `backtest/multifactor/attribution.py` | 因子归因 |
| `backtest/multifactor/risk/` | 分析/风格暴露 |

---

## 九、潜在风险与应对

### 风险 1：因子计算依赖财务数据时存在未来函数

**问题**：财报有披露日期（publish_date）和报告期（report_date）的区别。比如一季报的 report_date=2024-04-30, publish_date=2024-07-15，如果在 2024-05-01 计算因子时不该用到这份财报。

**解决**：数据存表时 **同时存 report_date 和 publish_date**，回测时只能用到 report_date <= trade_date 的数据。

### 风险 2：SQLite 在大量行情数据下性能瓶颈

**问题**：全 A 股约 5000+ 只股票 × 1000 个交易日 = 500 万行，查询可能变慢。

**解决**：
- 首期 SQLite 足够（500 万行 SQLite 查询 < 1s）
- 后续如果太慢，迁移到 **Parquet 文件**（列存，查询更快）

### 风险 3：多数据源一致性

**问题**：Baostock/AkShare/Tushare 的数据可能有差异（尤其停牌/涨跌幅/复权因子）。

**解决**：
- **统一数据源**（推荐 Baostock 做主力源，因为免费且稳定）
- 提供数据一致性校验：跨源对比，差异 > 0.5% 标记
- 所有数据的 `adj_factor` 必须对齐到 **不复权** 基线

### 风险 4：因子数据存库方式

**问题**：因子数据量可能很大（5000×1000×50因子 = 2.5 亿行）。

**解决**：
- **首期方案**：SQLite，用 version 分区，定期清理旧版本
- **二期方案**：SQLite（结构）+ Parquet（内容），Parquet 做列存，压缩率高（~10x）

### 风险 5：复权因子更新导致历史数据不一致

**问题**：当新除权除息事件发生，之前存的复权价格需要重新换算。

**解决**：
- **存原始价格 + adj_factor，不存复权价格**。
- 回测期按需换算：`adj_price = raw_price × current_adj_factor / latest_adj_factor`
- 这样不需要重新计算历史数据

---

## 十、CLI 使用示例

```bash
# 1. 首次全量更新
python -m data_fetch update --full --source baostock

# 2. 日常增量更新（收盘后跑）
python -m data_fetch update --incremental

# 3. 健康检查
python -m data_fetch health
# 输出：
#   ✅ 最新数据日期：2025-05-18
#   ✅ 股票覆盖率：99.7%（4987+/5000）
#   ⚠ 缺失数据：32 只股票有 1 日以上数据缺失
#   ❌ 异常涨跌：6 只股票日涨幅 > 15%（非 ST）

# 4. 运行多因子回测
python -m backtest.multifactor run \
  --start 2020-01-01 --end 2023-12-31 \
  --factor-list momentum,volatility,valuation \
  --factor-weights 0.4 0.3 0.3 \
  --pool hs300 --n-stocks 30 \
  --weight equal \
  --rebalance M \
  --slippage 0.001 \
  --min-commission 5.0

# 5. 因子归因分析
python -m backtest.multifactor analyze --run <run_id> --attribution
# 输出：
#   === 因子归因 ===
#   动量因子贡献：+45.2% → 贡献度 52%
#   波动率因子贡献：-12.8% → 贡献度 8%
#   估值因子贡献：+29.6% → 贡献度 39%
#   === 风格暴露 ===
#   市值偏误：+15%（偏向中小盘）
#   行业偏误：消费 +28%, 金融 -12%
```

---

## 十一、与现有 TODO 清单的关系

本方案涉及对现有 TODO 中以下项的改造：

| 现有 TODO | 影响 | 本方案如何处理 |
|-----------|----|-------------|
| 05- 最高佣金 5 元 | 修改 | → 在回测引擎中内置 |
| 02- **滑点** | 修改 | → 在回测引擎中内置 |
| 03-**涨跌停** | 修改 | → 在回测引擎中内置 |
| 04- **停牌** | 修改 | → 在回测引擎中内置 |
| 06- **最小单位** | 修改 | → 在回测引擎中内置 |
| 07-**除权除息** | 影响 | → **数据层只存 adj_factor，不回算价格**，回测期按需换算 |
| 08-**数据质量** | 影响 | → 本方案 **新增** 数据层 + 健康检查 |
| 09- **仓位管理** | 影响 | → 本次是核心功能之一 |
| 01-**T+1** | 影响 | → T+1 在回测引擎中内置 |

---

## 十二、总结

**核心设计原则：**
1. **数据本地化**：API 数据 → SQLite，回测只读库，不反复调 API
2. **数据分层存储**：行情 / 财务 / 成分股 / 因子，各表独立
3. **因子计算独立于回测**：先算因子存库，回测时从 DB 读取
4. **增量更新**：首次全量，后续只更新增量日
5. **避免未来函数**：财报用 publish_date，不存复权价格
6. **可扩展**：新因子 = 新文件，不影响现有代码

**开发建议：**
按照 Phase 1 → Phase 2 → Phase 3 顺序推进，每阶段完成后验证可用再推进下一阶段。Phase 1 的 data_fetch 是一切的基础，最优先完成。
