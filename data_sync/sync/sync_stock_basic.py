import pandas as pd
from typing import Optional
from data_sync.sync.base import BaseSync
from data_sync.models.stock_basic import StockBasic
from data_sync.tushare_client import tushare_client


class StockBasicSync(BaseSync):
    """股票基础信息同步"""
    
    def get_table_model(self):
        return StockBasic
    
    def fetch_data(self, **kwargs):
        """从 Tushare 获取股票基础信息"""
        return tushare_client.get_stock_basic(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        """转换股票基础数据"""
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient='records')
        
        transformed = []
        for record in records:
            transformed.append({
                'ts_code': record.get('ts_code'),
                'symbol': record.get('symbol'),
                'name': record.get('name'),
                'area': record.get('area'),
                'industry': record.get('industry'),
                'market': record.get('market'),
                'list_status': record.get('list_status'),
                'list_date': record.get('list_date'),
                'delist_date': record.get('delist_date'),
                'is_hs': record.get('is_hs'),
            })
        
        return transformed