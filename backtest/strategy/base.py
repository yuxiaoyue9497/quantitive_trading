"""策略基类 — 所有策略必须从此抽象基类继承。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class StrategyConfig:
    """策略配置 — 子类可添加自定义字段。"""

    parameters: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.parameters[key] = value


class BaseStrategy(ABC):
    """策略基类。

    子类实现:
        __init__: 初始化配置
        compute(df) → df: 向策略 DataFrame 添加 signal 列及相关列
    """

    name: str = "base"

    def __init__(self, **kwargs: Any) -> None:
        self.config = StrategyConfig(parameters=kwargs)

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame | tuple[pd.DataFrame, pd.Series]:
        """处理行情 DataFrame，返回 (df, signal) 或仅 df。

        DataFrame 必须包含 close 列，signal 列取值 [0, 1]。
        """
        ...

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """支持策略实例直接调用：s = DualMaStrategy(); df = s(df)。"""
        return self.compute(df)
