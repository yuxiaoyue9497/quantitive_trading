"""数据获取模块 - 统一入口，支持多数据源

通过 resolve_data_source 配置选择数据源：
- baostock (默认): 无需 Token，数据完整
- akshare: 开源免费，覆盖全 A 股
- tushare: 需要 Token，数据更专业
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .datafeed.base import AbstractDataSource
from .datafeed.resolver import resolve_data_source

__all__ = ["resolve_data_source", "AbstractDataSource", "fetch_stock_data"]


def fetch_stock_data(
    code: str,
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    source: str = "baostock",
    adjust: str | None = "2",
    **kwargs: Any,
) -> pd.DataFrame:
    """统一的数据获取入口。

    参数：
        code:     股票代码，如 "sz.300750"
        start:    开始日期 YYYY-MM-DD
        end:      结束日期 YYYY-MM-DD
        source:   数据源名称 ("baostock" | "akshare" | "tushare")
        adjust:   复权方式 (None/1=不复权/2=前复权/3=后复权)
        **kwargs: 数据源额外参数，如 tushare 的 token

    返回：
        列名 [date, open, high, low, close, volume] 的 DataFrame，
        date 为 datetime 索引，已按时间排序。
    """
    adapter: AbstractDataSource = resolve_data_source(source, **kwargs)
    return adapter.fetch(
        code=code,
        start=start,
        end=end,
        adjust=adjust,
    )
