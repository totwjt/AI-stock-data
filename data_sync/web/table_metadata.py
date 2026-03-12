"""
表描述元数据配置

定义每个表的中文名称、描述和同步类型
"""

# 表描述元数据
TABLE_METADATA = {
    "stock_basic": {
        "name": "股票基础信息",
        "description": "A股市场所有股票的基本信息，包括股票代码、名称、所属交易所、上市状态等",
        "sync_type": "全量",
        "fields": [
            "ts_code", "symbol", "name", "area", "industry", "market",
            "list_status", "list_date", "delist_date", "is_hs"
        ]
    },
    "trade_calendar": {
        "name": "交易日历",
        "description": "A股市场交易日历信息，包括交易日期和是否交易",
        "sync_type": "全量",
        "fields": ["exchange", "cal_date", "is_open"]
    },
    "daily": {
        "name": "日线行情",
        "description": "股票每日OHLC行情数据，包括开盘价、最高价、最低价、收盘价、成交量等",
        "sync_type": "增量",
        "fields": [
            "ts_code", "trade_date", "open", "high", "low", "close",
            "pre_close", "change", "pct_chg", "vol", "amount"
        ]
    },
    "adj_factor": {
        "name": "复权因子",
        "description": "股票复权因子，用于计算前复权和后复权价格",
        "sync_type": "增量",
        "fields": ["ts_code", "trade_date", "adj_factor"]
    },
    "daily_basic": {
        "name": "每日指标",
        "description": "股票每日基本面指标，包括市盈率、市净率、股息率、市值等",
        "sync_type": "增量",
        "fields": [
            "ts_code", "trade_date", "close", "turnover_rate", "volume_ratio",
            "pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm",
            "total_share", "float_share", "total_mv", "circ_mv"
        ]
    },
    "index_daily": {
        "name": "指数行情",
        "description": "主要指数（如上证指数、深证成指）的每日行情数据",
        "sync_type": "增量",
        "fields": [
            "ts_code", "trade_date", "open", "high", "low", "close",
            "pre_close", "change", "pct_chg", "vol", "amount"
        ]
    }
}


def get_table_metadata(table_name: str) -> dict:
    """获取指定表的元数据"""
    return TABLE_METADATA.get(table_name, {
        "name": table_name,
        "description": "未知表",
        "sync_type": "未知",
        "fields": []
    })


def get_all_tables_metadata() -> dict:
    """获取所有表的元数据"""
    return TABLE_METADATA


def get_syncable_tables() -> list:
    """获取可同步的表列表"""
    return list(TABLE_METADATA.keys())


def get_full_sync_tables() -> list:
    """获取全量同步的表列表"""
    return [k for k, v in TABLE_METADATA.items() if v["sync_type"] == "全量"]


def get_incremental_sync_tables() -> list:
    """获取增量同步的表列表"""
    return [k for k, v in TABLE_METADATA.items() if v["sync_type"] == "增量"]