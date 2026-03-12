import pandas as pd
from data_sync.sync.base import BaseSync
from data_sync.models.index_daily import IndexDaily
from data_sync.tushare_client import tushare_client


class IndexDailySync(BaseSync):
    """指数行情同步"""
    
    def get_table_model(self):
        return IndexDaily
    
    def fetch_data(self, **kwargs):
        """从 Tushare 获取指数行情"""
        return tushare_client.get_index_daily(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        """转换指数行情数据"""
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient='records')
        
        transformed = []
        for record in records:
            transformed.append({
                'ts_code': record.get('ts_code'),
                'trade_date': record.get('trade_date'),
                'open': record.get('open'),
                'high': record.get('high'),
                'low': record.get('low'),
                'close': record.get('close'),
                'pre_close': record.get('pre_close'),
                'change': record.get('change'),
                'pct_chg': record.get('pct_chg'),
                'vol': record.get('vol'),
                'amount': record.get('amount'),
            })
        
        return transformed