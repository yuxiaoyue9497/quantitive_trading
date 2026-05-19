from __future__ import annotations
import baostock as bs
import pandas as pd


def fetch_daily_kline_baostock(
    code: str,
    start_date: str,
    end_date: str,
    adjustflag: str = "3"  # "3"=不复权，存原始数据
) -> pd.DataFrame:
    """拉取单个股票的日线行情（baostock）。
    
    返回 DataFrame: [date, code, open, high, low, close, preclose, 
                     volume, amount, adj_factor, tradestatus, pct_chg]
    日期列是 'YYYY-MM-DD' 字符串。
    """
    lg = bs.login()
    try:
        rs = bs.query_history_k_data_plus(
            code=code,
            fields="date,code,open,high,low,close,preclose,volume,amount,adjustfactor,pct_chg",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag=adjustflag,
        )
        if rs.error_code != '0':
            return pd.DataFrame()
        df = rs.get_data()
    finally:
        bs.logout()

    if df.empty:
        return df

    # 列名对齐
    col_map = {
        "adjustfactor": "adj_factor",
    }
    df.rename(columns=col_map, inplace=True)

    # 数值列转换
    for col in ["open", "high", "low", "close", "preclose", "volume", "amount", "adj_factor", "pct_chg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # tradestatus 字段 baostock 不一定返回，默认 0
    if "tradestatus" not in df.columns:
        df["tradestatus"] = 0

    # 确保 code 列
    if "code" not in df.columns:
        df["code"] = code

    return df


def fetch_daily_kline_akshare(
    code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """拉取单个股票的日线行情（akshare 备选）。"""
    try:
        import akshare as ak
    except ImportError:
        raise ImportError("AkShare 数据源需要安装 akshare: uv add akshare")

    symbol = code.split(".")[-1]
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date.replace("-", ""),
        end_date=end_date.replace("-", ""),
        adjust="",  # 不复权
    )
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume",
    })
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 补充 baostock 兼容字段
    df["preclose"] = df["close"].shift(1)
    df["preclose"] = df["preclose"].fillna(df["close"].iloc[0] / 1.1 if df["close"].iloc[0] else 0)
    df["amount"] = df.get("成交额", pd.Series(dtype=float))
    df["adj_factor"] = 1.0
    df["tradestatus"] = 0
    df["pct_chg"] = df["close"].pct_change() * 100
    df["code"] = code

    df = df.drop("date", axis=1).set_index("date") if "date" in df.columns else df

    return df


KLINE_FIELDS = [
    "date", "code", "open", "high", "low", "close", "preclose",
    "volume", "amount", "adj_factor", "tradestatus", "pct_chg",
]
