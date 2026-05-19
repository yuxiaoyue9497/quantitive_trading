from __future__ import annotations
import baostock as bs
import pandas as pd


FINANCIAL_FIELDS = (
    "s_info_code,date,s_report_date,s_end_date,"
    "pe_ttm,pb,roe,np_growth_rate,op_income_yoy_yoy,"
    "gross_margin,net_profit_margin,npl_interest_ratio,"
    "total_asset_turn,grossprofit_margin,netprofit_margin,"
    "debt_to_assets,ocfps"
)


def fetch_financial_qtr(
    code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """拉取财务数据（季报）。
    
    返回 DataFrame: [code, report_date, publish_date, ...financial fields]
    report_date=publish_date 用于规避未来函数。
    """
    lg = bs.login()
    try:
        rs = bs.query_profit_data(code, start_year=start_date[:4], end_year=end_date[:4])
        if rs.error_code != '0':
            return pd.DataFrame(columns=["code", "report_date", "publish_date",
                                         "pe_ttm", "pb", "roe", "net_profit_grow",
                                         "revenue_grow", "gross_margin", "net_margin",
                                         "debt_to_asset", "operating_cash"])
        df_list = []
        while rs.next():
            df_list.append(rs.get_row_data())
        df = pd.DataFrame(df_list, columns=rs.fields)
    finally:
        bs.logout()

    if df.empty:
        return pd.DataFrame(columns=["code", "report_date", "publish_date",
                                     "pe_ttm", "pb", "roe", "net_profit_grow",
                                     "revenue_grow", "gross_margin", "net_margin",
                                     "debt_to_asset", "operating_cash"])

    col_map = {
        's_info_code': 'code',
        's_end_date': 'report_date',
        's_report_date': 'publish_date',
        'roe': 'roe',
        'np_growth_rate': 'net_profit_grow',
        'op_income_yoy_yoy': 'revenue_grow',
        'grossprofit_margin': 'gross_margin',
        'netprofit_margin': 'net_margin',
        'debt_to_assets': 'debt_to_asset',
    }
    df.rename(columns=col_map, inplace=True)

    # 补充 pb, pe_ttm (baostock profit_data 不含 PB/PE)
    if 'pb' not in df.columns:
        df['pb'] = None
    if 'pe_ttm' not in df.columns:
        df['pe_ttm'] = None
    if 'operating_cash' not in df.columns:
        df['operating_cash'] = None

    for col in ["pe_ttm", "pb", "roe", "net_profit_grow", "revenue_grow",
                "gross_margin", "net_margin", "debt_to_asset", "operating_cash"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[["code", "report_date", "publish_date", "pe_ttm", "pb", "roe",
               "net_profit_grow", "revenue_grow", "gross_margin", "net_margin",
               "debt_to_asset", "operating_cash"]]


def fetch_fin_valuation(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """拉取估值数据（估值指标）。"""
    lg = bs.login()
    try:
        rs = bs.query_stock_billboard_info(code, start_date, end_date)
        if rs.error_code != '0':
            return pd.DataFrame(columns=["code", "date", "pe_ttm", "pb"])
        df_list = []
        while rs.next():
            df_list.append(rs.get_row_data())
        df = pd.DataFrame(df_list, columns=rs.fields)
    finally:
        bs.logout()

    if df.empty:
        return pd.DataFrame(columns=["code", "date", "pe_ttm", "pb"])

    col_map = {
        's_info_code': 'code',
        'trade_date': 'date',
        'pe0': 'pe_ttm',
        'pb0': 'pb',
    }
    df.rename(columns=col_map, inplace=True)

    # 数值列转换
    for col in ["pe_ttm", "pb"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
