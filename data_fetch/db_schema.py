"""数据库表结构定义 (stock_data.db 和 factor_raw.db)"""

from __future__ import annotations

import sqlite3


def stock_info_sql() -> str:
    """CREATE TABLE stock_info"""
    stmt = (
        "CREATE TABLE IF NOT EXISTS stock_info ("
        "    code          TEXT PRIMARY KEY,"
        "    name          TEXT,"
        "    industry      TEXT,"
        "    listed_date   TEXT,"
        "    delisted_date TEXT,"
        "    exchange      TEXT,"
        "    board         TEXT,"
        "    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP"
        ");"
    )
    return stmt


def index_constituents_sql() -> str:
    """CREATE TABLE index_constituents + 索引"""
    table_sql = (
        "CREATE TABLE IF NOT EXISTS index_constituents ("
        "    index_code    TEXT,"
        "    stock_code    TEXT,"
        "    effective_date TEXT,"
        "    weight        REAL,"
        "    PRIMARY KEY (index_code, stock_code, effective_date)"
        ");"
    )
    idx_sql = (
        "CREATE INDEX IF NOT EXISTS idx_index_const_date "
        "ON index_constituents(index_code, effective_date);"
    )
    return table_sql + " " + idx_sql


def daily_kline_sql() -> str:
    """CREATE TABLE daily_kline + 索引"""
    table_sql = (
        "CREATE TABLE IF NOT EXISTS daily_kline ("
        "    code          TEXT,"
        "    date          DATE,"
        "    open          REAL,"
        "    high          REAL,"
        "    low           REAL,"
        "    close         REAL,"
        "    preclose      REAL,"
        "    volume        REAL,"
        "    amount        REAL,"
        "    adj_factor    REAL,"
        "    tradestatus   INTEGER,"
        "    pct_chg       REAL,"
        "    PRIMARY KEY (code, date)"
        ");"
    )
    idx_sql = (
        "CREATE INDEX IF NOT EXISTS idx_kline_code "
        "ON daily_kline(code);"
    )
    return table_sql + " " + idx_sql


def financial_qtr_sql() -> str:
    """CREATE TABLE financial_qtr + 索引"""
    table_sql = (
        "CREATE TABLE IF NOT EXISTS financial_qtr ("
        "    code          TEXT,"
        "    report_date   DATE,"
        "    publish_date  DATE,"
        "    pe_ttm        REAL,"
        "    pb            REAL,"
        "    roe           REAL,"
        "    net_profit_grow REAL,"
        "    revenue_grow  REAL,"
        "    gross_margin  REAL,"
        "    net_margin    REAL,"
        "    debt_to_asset REAL,"
        "    operating_cash REAL,"
        "    PRIMARY KEY (code, report_date)"
        ");"
    )
    idx_sql = (
        "CREATE INDEX IF NOT EXISTS idx_fin_code "
        "ON financial_qtr(code);"
    )
    return table_sql + " " + idx_sql


def daily_market_cap_sql() -> str:
    """CREATE TABLE daily_market_cap"""
    return (
        "CREATE TABLE IF NOT EXISTS daily_market_cap ("
        "    code          TEXT,"
        "    date          DATE,"
        "    total_market_cap REAL,"
        "    total_mkt_cap REAL,"
        "    freely_turnover REAL,"
        "    PRIMARY KEY (code, date)"
        ");"
    )


def factor_versions_sql() -> str:
    """CREATE TABLE factor_versions"""
    return (
        "CREATE TABLE IF NOT EXISTS factor_versions ("
        "    version_id    TEXT PRIMARY KEY,"
        "    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "    description   TEXT"
        ");"
    )


def factor_data_sql() -> str:
    """CREATE TABLE factor_data + 索引"""
    table_sql = (
        "CREATE TABLE IF NOT EXISTS factor_data ("
        "    version_id    TEXT,"
        "    code          TEXT,"
        "    date          DATE,"
        "    factor_name   TEXT,"
        "    factor_value  REAL,"
        "    status        TEXT,"
        "    PRIMARY KEY (version_id, code, date, factor_name)"
        ");"
    )
    idx_sql = (
        "CREATE INDEX IF NOT EXISTS idx_factor_date_name "
        "ON factor_data(date, factor_name);"
    )
    return table_sql + " " + idx_sql


# stock_data.db 表名列表
SCHEMA_STOCK_TABLES: list[str] = [
    "stock_info",
    "index_constituents",
    "daily_kline",
    "financial_qtr",
    "daily_market_cap",
]

# factor_raw.db 表名列表
SCHEMA_FACTOR_TABLES: list[str] = [
    "factor_versions",
    "factor_data",
]

# 全部表名（合并）
SCHEMA_TABLES: list[str] = [
    *SCHEMA_STOCK_TABLES,
    *SCHEMA_FACTOR_TABLES,
]

# stock_data.db 建表函数映射
STOCK_TABLE_FUNCS: dict[str, str] = {
    "stock_info": stock_info_sql,
    "index_constituents": index_constituents_sql,
    "daily_kline": daily_kline_sql,
    "financial_qtr": financial_qtr_sql,
    "daily_market_cap": daily_market_cap_sql,
}

# factor_raw.db 建表函数映射
FACTOR_TABLE_FUNCS: dict[str, str] = {
    "factor_versions": factor_versions_sql,
    "factor_data": factor_data_sql,
}

# 表主键列映射 (用于 upsert)
TABLE_PRIMARY_KEYS: dict[str, list[str]] = {
    "stock_info": ["code"],
    "index_constituents": ["index_code", "stock_code", "effective_date"],
    "daily_kline": ["code", "date"],
    "financial_qtr": ["code", "report_date"],
    "daily_market_cap": ["code", "date"],
    "factor_versions": ["version_id"],
    "factor_data": ["version_id", "code", "date", "factor_name"],
}


def create_all_stock_tables(conn: sqlite3.Connection) -> None:
    """在 conn 上创建 stock_data.db 的全部表."""
    for name, func in STOCK_TABLE_FUNCS.items():
        sql = func()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
    conn.commit()


def create_all_factor_tables(conn: sqlite3.Connection) -> None:
    """在 conn 上创建 factor_raw.db 的全部表."""
    for name, func in FACTOR_TABLE_FUNCS.items():
        sql = func()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
    conn.commit()


def create_all_tables(
    stock_conn: sqlite3.Connection,
    factor_conn: sqlite3.Connection | None = None,
) -> None:
    """创建 stock_data.db 和可选的 factor_raw.db 的全部表."""
    create_all_stock_tables(stock_conn)
    if factor_conn is not None:
        create_all_factor_tables(factor_conn)
