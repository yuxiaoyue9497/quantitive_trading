from __future__ import annotations
import baostock as bs
import pandas as pd


INDEX_MAP = {
    "hs300": "000300.SH",  # 沪深300
    "zz500": "000905.SH",  # 中证500
    "zz1000": "000852.SH", # 中证1000
    "hs50": "000016.SH",   # 上证50
}

INDEX_NAMES = {v: k for k, v in INDEX_MAP.items()}


def fetch_index_constituents(
    index_code: str,
    date: str,
) -> pd.DataFrame:
    """拉取某日指数成分股。
    
    Args:
        index_code: '000300.SH', '000905.SH' 等
        date: 'YYYY-MM-DD'
    
    Returns:
        DataFrame: [index_code, stock_code, weight]
    """
    lg = bs.login()
    try:
        rs = bs.query_hs300_stocks(index_code) if "300" in index_code else None
        if rs is None:
            rs = bs.query_zh_ah_index(code=index_code, start_date=date, end_date=date)

        result = []
        if rs and rs.error_code == '0':
            while rs.next():
                result.append(rs.get_row_data())

        if result:
            df = pd.DataFrame(result, columns=rs.fields)
        else:
            df = pd.DataFrame(columns=["index_code", "stock_code"])
    except Exception:
        df = pd.DataFrame(columns=["index_code", "stock_code"])
    finally:
        bs.logout()

    df["index_code"] = index_code
    df["effective_date"] = date
    df["weight"] = 1.0 / len(df) if not df.empty else 0.0

    return df[["index_code", "stock_code", "effective_date", "weight"]]


def fetch_historical_constituents(
    index_key: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """拉取指数成分股历史（用于避免幸存者偏置）。"""
    index_code = INDEX_MAP.get(index_key, index_key)
    all_dfs = []

    # 按季度拉取
    current = start_date
    while current <= end_date:
        try:
            df = fetch_index_constituents(index_code, current)
            if not df.empty:
                all_dfs.append(df)
        except Exception:
            pass  # 缺失数据跳过
        # 按季度推进
        month = int(current.split("-")[1])
        year = int(current.split("-")[0])
        month += 3
        if month > 12:
            month -= 12
            year += 1
        current = f"{year}-{month:02d}-01"
        if current > end_date:
            break

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame(columns=["index_code", "stock_code", "effective_date", "weight"])
