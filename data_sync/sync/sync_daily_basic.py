import pandas as pd
from data_sync.sync.base import BaseSync
from data_sync.models.stock_daily_basic import StockDailyBasic
from data_sync.tushare_client import tushare_client


class DailyBasicSync(BaseSync):
    """每日基本面指标同步"""
    
    def get_table_model(self):
        return StockDailyBasic
    
    def fetch_data(self, **kwargs):
        """从 Tushare 获取每日基本面指标"""
        return tushare_client.get_daily_basic(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        """转换每日基本面指标数据"""
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient='records')
        
        transformed = []
        for record in records:
            transformed.append({
                'ts_code': record.get('ts_code'),
                'trade_date': record.get('trade_date'),
                'close': record.get('close'),
                'turnover_rate': record.get('turnover_rate'),
                'turnover_rate_f': record.get('turnover_rate_f'),
                'volume_ratio': record.get('volume_ratio'),
                'pe': record.get('pe'),
                'pe_ttm': record.get('pe_ttm'),
                'pb': record.get('pb'),
                'ps': record.get('ps'),
                'ps_ttm': record.get('ps_ttm'),
                'dv_ratio': record.get('dv_ratio'),
                'dv_ttm': record.get('dv_ttm'),
                'total_share': record.get('total_share'),
                'float_share': record.get('float_share'),
                'free_share': record.get('free_share'),
                'total_mv': record.get('total_mv'),
                'circ_mv': record.get('circ_mv'),
            })
        
        return transformed