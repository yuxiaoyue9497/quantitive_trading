"""SQLiteStore - SQLite 连接管理 + CRUD + upsert + 迁移"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from .db_schema import TABLE_PRIMARY_KEYS, create_all_stock_tables

_LOCAL = threading.local()


def _ensure_dir(db_path: str) -> None:
    """确保目录存在."""
    parent = Path(db_path).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def _get_local_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接."""
    if not hasattr(_LOCAL, "_conn"):
        _LOCAL._conn = sqlite3.connect(_LOCAL._db_path, timeout=30.0)
        _LOCAL._conn.execute("PRAGMA journal_mode=WAL")
        _LOCAL._conn.execute("PRAGMA foreign_keys=ON")
        _LOCAL._conn.row_factory = sqlite3.Row
    return _LOCAL._conn


class SQLiteStore:
    """SQLiteStore - 连接池 + CRUD + upsert + 迁移.

    Args:
        db_path: SQLite 数据库文件路径.

    Example:
        >>> with SQLiteStore("data/sqlite/stock_data.db") as store:
        ...     store.init_schema()
        ...     rows = store.query("SELECT * FROM stock_info;")
        ...     codes = store.get_all_codes("stock_info")
    """

    def __init__(self, db_path: str) -> None:
        _ensure_dir(db_path)
        self.db_path = db_path
        self._init = False

    def init_schema(self) -> None:
        """执行 db_schema.create_all_stock_tables 创建所有表."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        create_all_stock_tables(conn)
        conn.close()
        self._init = True

    # --------------- 内部工具 ---------------- #

    @contextmanager
    def _conn(self) -> Any:
        """获取连接上下文管理器（自动 commit/rollback）."""
        _ensure_dir(self.db_path)
        if not hasattr(_LOCAL, "_db_path"):
            _LOCAL._db_path = self.db_path
        conn = _get_local_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _ensure_row_factory(self) -> None:
        """确保 row_factory 已设为 sqlite3.Row."""
        conn = _get_local_conn()
        if conn.row_factory is not sqlite3.Row:
            conn.row_factory = sqlite3.Row

    # --------------- 查询 ---------------- #

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """执行 SELECT 查询，返回 dict 列表."""
        with self._conn() as conn:
            self._ensure_row_factory()
            cursor = conn.execute(sql, params)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        """执行 SELECT 查询，返回第一行 dict 或 None."""
        with self._conn() as conn:
            self._ensure_row_factory()
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [d[0] for d in cursor.description] if cursor.description else []
            return dict(zip(columns, row))

    def query_df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """执行 SELECT 查询，返回 DataFrame."""
        with self._conn() as conn:
            self._ensure_row_factory()
            return pd.read_sql_query(sql, conn, params=params)

    # --------------- 写入 ---------------- #

    def execute(self, sql: str, params: tuple = ()) -> None:
        """执行一条 SQL（INSERT / UPDATE / DELETE / DDL）."""
        with self._conn() as conn:
            conn.execute(sql, params)

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """批量执行 SQL."""
        if not params_list:
            return
        with self._conn() as conn:
            conn.executemany(sql, params_list)

    # --------------- Upsert ---------------- #

    def upsert(self, table: str, records: list[dict]) -> int:
        """根据表的主键进行 upsert.

        Args:
            table: 表名.
            records: 记录列表，每个元素是 {col: value}.

        Returns:
            upsert 的记录数.
        """
        if not records:
            return 0

        first_record: dict[str, Any] = records[0]
        columns = list(first_record.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)

        sql = (
            f"INSERT OR REPLACE INTO {table} ({col_names}) "
            f"VALUES ({placeholders})"
        )

        params_list = [tuple(r[col] for col in columns) for r in records]
        self.execute_many(sql, params_list)
        return len(records)

    def upsert_from_df(self, df: pd.DataFrame, table: str) -> int:
        """从 DataFrame upsert 到表."""
        records = df.replace(
            {float("nan"): None, float("inf"): None, float("-inf"): None}
        ).fillna(None).to_dict(orient="records")
        return self.upsert(table, records)

    # --------------- 批量操作 ---------------- #

    def batch_upsert_kline(self, records: list[tuple]) -> int:
        """针对 daily_kline 表的优化批量 upsert, 使用 ON CONFLICT DO UPDATE.

        Args:
            records: list of (code, date, open, high, low, close,
                     preclose, volume, amount, adj_factor,
                     tradestatus, pct_chg).

        Returns:
            upsert的记录数.
        """
        if not records:
            return 0

        columns = [
            "code", "date", "open", "high", "low", "close", "preclose",
            "volume", "amount", "adj_factor", "tradestatus", "pct_chg",
        ]
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        pk_set = frozenset(["code", "date"])
        updates = [f"{c} = excluded.{c}" for c in columns if c not in pk_set]

        sql = (
            f"INSERT INTO daily_kline ({col_names}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(code, date) DO UPDATE SET "
            + ", ".join(updates)
        )

        self.execute_many(sql, records)
        return len(records)

    # --------------- 迁移 ---------------- #

    def migrate(self, version: str) -> None:
        """版本迁移钩子.

        可用此方法注册已执行过的迁移版本. 子类可重写以执行具体迁移逻辑.

        Args:
            version: 迁移版本号字符串.
        """
        if not hasattr(self, "_migrations"):
            self._migrations: dict[str, bool] = {}
        self._migrations[version] = True

    # --------------- 上下文管理器 ---------------- #

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # --------------- 辅助方法 ---------------- #

    def table_exists(self, table: str) -> bool:
        """检查表是否存在."""
        row = self.query_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table,),
        )
        return row is not None

    def get_latest_date(self, table: str, code: str) -> str | None:
        """获取某只股票在表中的最新日期（date 列）."""
        result = self.query_one(
            f"SELECT MAX(date) as d FROM {table} WHERE code=?;",
            (code,),
        )
        if result and result.get("d"):
            return str(result["d"])
        return None

    def get_all_codes(self, table: str) -> list[str]:
        """获取表中所有股票代码."""
        rows = self.query(f"SELECT DISTINCT code FROM {table};")
        return [r["code"] for r in rows] if rows else []

    # --------------- 生命周期 ---------------- #

    def close(self) -> None:
        """关闭当前线程的连接并清理."""
        if hasattr(_LOCAL, "_conn") and _LOCAL._conn:
            _LOCAL._conn.close()
            _LOCAL._conn = None
        if hasattr(_LOCAL, "_db_path"):
            del _LOCAL._db_path
