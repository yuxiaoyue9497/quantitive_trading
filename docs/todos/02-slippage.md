# TODO: 滑点

## 现状
engine.py 第 30-33 行计算手续费时，交易价格直接用信号触发日的 close/开盘价，
没有任何价格偏置。买入/卖出都按同一价格执行。

## A股现实
实际交易中，你的订单不能完全以"理想价格"成交：
- 买入：实际成交价 **高于** 目标价（买一价可能更高）
- 卖出：实际成交价 **低于** 目标价（卖一价可能更低）

典型滑点：
- 大盘蓝筹：0.1% ~ 0.3%（千分之一到千分之三）
- 中小盘股：0.5% ~ 1.0%（千分到百分之一）
- 涨停/跌停板：无法成交（滑点 = ∞）

## 影响
- 高频交易中，滑点会吃掉大量收益
- 中小盘标的回测偏乐观
- 极端行情下（连续涨跌停）回测完全失真

## 实现建议
1. 在 TradingConsts 或 Config 中增加 SLIPPAGE_RATE 项，按标的流动性分级配置：
   ```
   SLIPPAGE_LARGE_CAP = 0.001   # 大盘 0.1%
   SLIPPAGE_SMALL_CAP = 0.005   # 小盘 0.5%
   ```
2. 在回测中调整成交价格：
   ```
   actual_buy_price = target_price * (1 + slippage)
   actual_sell_price = target_price * (1 - slippage)
   ```
3. 或者更精细地用 high/low 价格模拟——买在当日均价偏向 high，卖在偏向 low

## 优先级
🔴 高 — 对高频/中小盘回测影响极大

## 涉及文件
- backtest/engine.py（run_backtest 交易成本计算）
- backtest/constants.py（建议新增滑点常量）
