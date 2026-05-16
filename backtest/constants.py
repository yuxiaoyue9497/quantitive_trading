"""量化回测框架常量定义"""


class TradingConsts:
    """A股交易费率常量"""
    COMMISSION = 0.0003      # 万三佣金
    TURN_FEE = 0.00006       # 万零六过户费
    TAX = 0.001              # 千一印花税 (仅卖出)
    RATE_BUY = COMMISSION + TURN_FEE
    RATE_SELL = COMMISSION + TURN_FEE + TAX


class BacktestConsts:
    """回测引擎常量"""
    TRADING_DAYS = 242       # A股年交易日
    RISK_FREE_RATE = 0.02    # 无风险利率


class DataConsts:
    """数据源常量"""
    BAOSTOCK_ADJUST = "2"    # 2=前复权
    BAOSTOCK_FREQ = "d"      # d=日K
    BAOSTOCK_FIELDS = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg"
