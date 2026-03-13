"""
表描述管理器

提供每个表的字段描述和说明信息
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FieldDescription:
    """字段描述"""
    name: str
    type: str
    description: str
    is_primary_key: bool = False


@dataclass
class TableDescription:
    """表描述"""
    name: str
    description: str
    fields: List[FieldDescription]
    sync_type: str  # "full" 或 "incremental"


# 表描述配置
TABLE_DESCRIPTIONS: Dict[str, TableDescription] = {
    "stock_basic": TableDescription(
        name="stock_basic",
        description="股票基础信息表，包含股票代码、名称、行业等基本信息",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("symbol", "VARCHAR(10)", "股票代码（简化）"),
            FieldDescription("name", "VARCHAR(50)", "股票名称"),
            FieldDescription("area", "VARCHAR(20)", "地域"),
            FieldDescription("industry", "VARCHAR(20)", "行业"),
            FieldDescription("market", "VARCHAR(10)", "市场类型"),
            FieldDescription("list_status", "VARCHAR(1)", "上市状态（L=上市，D=退市，P=暂停）"),
            FieldDescription("list_date", "VARCHAR(10)", "上市日期"),
            FieldDescription("delist_date", "VARCHAR(10)", "退市日期"),
            FieldDescription("is_hs", "VARCHAR(1)", "是否沪深港通标的"),
        ],
        sync_type="full"
    ),
    "trade_calendar": TableDescription(
        name="trade_calendar",
        description="交易日历表，记录各交易所的交易日信息",
        fields=[
            FieldDescription("exchange", "VARCHAR(10)", "交易所代码", True),
            FieldDescription("cal_date", "VARCHAR(10)", "日历日期", True),
            FieldDescription("is_open", "INTEGER", "是否交易（1=交易日，0=非交易日）"),
        ],
        sync_type="full"
    ),
    "daily": TableDescription(
        name="daily",
        description="股票日线行情表（stock_daily），记录每日的开盘价、收盘价、成交量等",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("open", "FLOAT", "开盘价"),
            FieldDescription("high", "FLOAT", "最高价"),
            FieldDescription("low", "FLOAT", "最低价"),
            FieldDescription("close", "FLOAT", "收盘价"),
            FieldDescription("pre_close", "FLOAT", "前收盘价"),
            FieldDescription("change", "FLOAT", "涨跌额"),
            FieldDescription("pct_chg", "FLOAT", "涨跌幅（%）"),
            FieldDescription("vol", "FLOAT", "成交量（手）"),
            FieldDescription("amount", "FLOAT", "成交额（千元）"),
        ],
        sync_type="incremental"
    ),
    "adj_factor": TableDescription(
        name="adj_factor",
        description="股票复权因子表（stock_adj_factor），记录每日的复权因子",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("adj_factor", "FLOAT", "复权因子"),
        ],
        sync_type="incremental"
    ),
    "daily_basic": TableDescription(
        name="daily_basic",
        description="股票每日基本面指标表（stock_daily_basic），包含市盈率、市净率等指标",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("close", "FLOAT", "收盘价"),
            FieldDescription("turnover_rate", "FLOAT", "换手率（%）"),
            FieldDescription("turnover_rate_f", "FLOAT", "换手率（自由流通股）"),
            FieldDescription("volume_ratio", "FLOAT", "量比"),
            FieldDescription("pe", "FLOAT", "市盈率（总市值/净利润）"),
            FieldDescription("pe_ttm", "FLOAT", "市盈率（TTM）"),
            FieldDescription("pb", "FLOAT", "市净率（总市值/净资产）"),
            FieldDescription("ps", "FLOAT", "市销率（总市值/营业收入）"),
            FieldDescription("ps_ttm", "FLOAT", "市销率（TTM）"),
            FieldDescription("dv_ratio", "FLOAT", "股息率（%）"),
            FieldDescription("dv_ttm", "FLOAT", "股息率（TTM，%）"),
            FieldDescription("total_share", "FLOAT", "总股本（万股）"),
            FieldDescription("float_share", "FLOAT", "流通股本（万股）"),
            FieldDescription("free_share", "FLOAT", "自由流通股本（万股）"),
            FieldDescription("total_mv", "FLOAT", "总市值（万元）"),
            FieldDescription("circ_mv", "FLOAT", "流通市值（万元）"),
        ],
        sync_type="incremental"
    ),
    "index_daily": TableDescription(
        name="index_daily",
        description="指数行情表，记录每日指数的开盘价、收盘价等",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "指数代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("open", "FLOAT", "开盘价"),
            FieldDescription("high", "FLOAT", "最高价"),
            FieldDescription("low", "FLOAT", "最低价"),
            FieldDescription("close", "FLOAT", "收盘价"),
            FieldDescription("pre_close", "FLOAT", "前收盘价"),
            FieldDescription("change", "FLOAT", "涨跌额"),
            FieldDescription("pct_chg", "FLOAT", "涨跌幅（%）"),
            FieldDescription("vol", "FLOAT", "成交量（手）"),
            FieldDescription("amount", "FLOAT", "成交额（千元）"),
        ],
        sync_type="incremental"
    ),
    "stk_factor_pro": TableDescription(
        name="stk_factor_pro",
        description="股票技术面因子表（专业版），包含MACD、KDJ、RSI等大量技术指标",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("close", "FLOAT", "收盘价"),
            FieldDescription("macd", "FLOAT", "MACD指标"),
            FieldDescription("kdj_k", "FLOAT", "KDJ-K值"),
            FieldDescription("rsi_6", "FLOAT", "RSI-6日"),
            FieldDescription("boll_upper", "FLOAT", "布林带上轨"),
            FieldDescription("atr", "FLOAT", "平均真实波幅"),
            FieldDescription("cci", "FLOAT", "顺势指标"),
            FieldDescription("bbi", "FLOAT", "多空指标"),
            FieldDescription("obv", "FLOAT", "能量潮"),
        ],
        sync_type="incremental"
    ),
    "stk_factor_pro_history": TableDescription(
        name="stk_factor_pro_history",
        description="股票技术面因子表（历史数据），按年份分段同步",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
            FieldDescription("year", "INTEGER", "年份（用于分区）"),
        ],
        sync_type="incremental"
    ),
    "stk_factor_pro_daily": TableDescription(
        name="stk_factor_pro_daily",
        description="股票技术面因子表（每日增量），按交易日期同步全部股票",
        fields=[
            FieldDescription("ts_code", "VARCHAR(20)", "股票代码", True),
            FieldDescription("trade_date", "VARCHAR(10)", "交易日期", True),
        ],
        sync_type="incremental"
    ),
}


def get_table_description(table_name: str) -> Optional[TableDescription]:
    """获取表描述"""
    return TABLE_DESCRIPTIONS.get(table_name)


def get_all_table_descriptions() -> List[TableDescription]:
    """获取所有表描述"""
    return list(TABLE_DESCRIPTIONS.values())