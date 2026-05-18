"""数据源适配器包 — 支持 Baostock(默认)/AkShare/Tushare。

通过 resolve_data_source 动态选择数据源：
    adapter = resolve_data_source("baostock")
    df = adapter.fetch(code="sz.300750", start="2023-01-01", end="2025-12-31", adjust="2")

自定义数据源：
    class MyDataSource(AbstractDataSource):
        def fetch(self, code, start, end, adjust):
            ...
    register_data_source("my_source", MyDataSource)
"""

from __future__ import annotations

from .base import AbstractDataSource
from .baostock import BaostockDataSource
from .resolver import resolve_data_source, register_data_source

__all__ = [
    "AbstractDataSource",
    "BaostockDataSource",
    "resolve_data_source",
    "register_data_source",
]
