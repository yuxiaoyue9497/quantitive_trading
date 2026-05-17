"""数据源抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class AbstractDataSource(ABC):
    """数据源适配器基类"""

    @abstractmethod
    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str | None = "2",
    ) -> pd.DataFrame:
        """拉取日K数据并标准化。

        返回 DataFrame 列名必须为: [date, open, high, low, close, volume]
        date 为 datetime 类型，设为索引，已按时间排序。
        """
        ...
