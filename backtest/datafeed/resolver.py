"""数据源解析器 - 根据配置动态选择数据源"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AbstractDataSource
from .baostock import BaostockDataSource
from .akshare import AkShareDataSource
from .tushare import TushareDataSource

if TYPE_CHECKING:
    pass

# 数据源注册表
_DATASOURCE_REGISTRY: dict[str, type[AbstractDataSource]] = {
    "baostock": BaostockDataSource,
    "akshare": AkShareDataSource,
    "tushare": TushareDataSource,
}


def resolve_data_source(
    name: str = "baostock",
    **fetch_kwargs: Any,
) -> AbstractDataSource:
    """根据名称解析数据源适配器。

    参数：
        name: 数据源名称
        **fetch_kwargs: 传递给 fetch() 方法的额外参数（如 tushare 的 token）

    返回：
        AbstractDataSource 实例
    """
    cls = _DATASOURCE_REGISTRY.get(name.lower())
    if cls is None:
        supported = ", ".join(_DATASOURCE_REGISTRY.keys())
        raise ValueError(
            f"不支持的数据源: '{name}'。支持的源: [{supported}]"
        )
    # 将额外参数存储在实例上，fetch 时使用
    instance = cls()
    if fetch_kwargs:
        for k, v in fetch_kwargs.items():
            setattr(instance, k, v)
    return instance


def register_data_source(name: str, cls: type[AbstractDataSource]) -> None:
    """注册自定义数据源适配器。

    示例：
        register_data_source("mydatasource", MyDataSource)
    """
    _DATASOURCE_REGISTRY[name.lower()] = cls
