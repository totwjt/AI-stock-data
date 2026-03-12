import pandas as pd
from data_sync.sync.base import BaseSync
from data_sync.models.stock_adj_factor import StockAdjFactor
from data_sync.tushare_client import tushare_client


class AdjFactorSync(BaseSync):
    """复权因子同步"""
    
    def get_table_model(self):
        return StockAdjFactor
    
    def fetch_data(self, **kwargs):
        """从 Tushare 获取复权因子"""
        return tushare_client.get_adj_factor(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        """转换复权因子数据"""
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient='records')
        
        transformed = []
        for record in records:
            transformed.append({
                'ts_code': record.get('ts_code'),
                'trade_date': record.get('trade_date'),
                'adj_factor': record.get('adj_factor'),
            })
        
        return transformed