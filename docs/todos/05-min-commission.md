# TODO: 最低佣金 5 元

## 现状
constants.py 中：
```
RATE_BUY = COMMISSION + TURN_FEE = 0.00036  # 3.6 bps
RATE_SELL = COMMISSION + TURN_FEE + TAX = 0.0136  # 13.6 bps
```
engine.py 第 30-33 行：`trading_cost = rate * position`，完全基于仓位金额计算。

## A股现实
券商佣金有 **最低 5 元** 的限制（实际可能因券商而异，但普遍如此）：
- 计算佣金 = max(按费率计算的佣金, 5 元)
- 即使你只买 100 元股票（佣金=0.36 元），券商也会收 5 元

## 影响
- **小额交易**（仓位 < 13,889 元）：佣金被严重低估
  - 例：买 5000 元，按费率佣金 = 1.8 元，但实际需交 5 元（多 178%）
- **高频交易**：小笔交易频率高时，总佣金被严重低估
- 回测中可能认为可频繁做 T，但真实成本会让你亏钱

## 实现建议
1. 修改 engine.py 的交易成本计算：
   ```python
   # 买
   buy_cost = max(position * TradingConsts.RATE_BUY, 5.0)
   # 卖
   sell_cost = max(position * TradingConsts.RATE_SELL, 5.0)  # 或印花税也有最低
   ```
2. 在constants.py 中添加：
   ```python
   MIN_COMMISSION = 5.0  # 最低佣金
   ```
3. 考虑印花税最低限制（如有，通常为 1 元）

## 优先级
🟠 中 — 小额高频交易场景下影响显著

## 涉及文件
- backtest/engine.py（交易成本计算）
- backtest/constants.py（增加最低佣金常量）
