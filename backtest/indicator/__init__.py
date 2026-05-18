"""技术指标模块 — 量价/趋势类指标。

所有指标都接受 DataFrame 并返回添加了新列的 DataFrame。
指标列名与函数名一致，方便策略使用。

使用示例：
    >>> from backtest.indicator import rsi, bollinger_bands
    >>> df = rsi(df, period=14)        # df['rsi']
    >>> df = bollinger_bands(df, n=20) # df['ma'], df['upper'], df['lower']
"""
