"""数据源适配器包 - 支持 Baostock(默认)/AkShare/Tushare"""

from __future__ import annotations

from .base import AbstractDataSource
from .baostock import BaostockDataSource
from .resolver import resolve_data_source

__all__ = [
    "AbstractDataSource",
    "BaostockDataSource",
    "resolve_data_source",
]
