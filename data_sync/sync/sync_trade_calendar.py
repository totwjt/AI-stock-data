import pandas as pd
from data_sync.sync.base import BaseSync
from data_sync.models.trade_calendar import TradeCalendar
from data_sync.tushare_client import tushare_client


class TradeCalendarSync(BaseSync):
    """交易日历同步"""
    
    def get_table_model(self):
        return TradeCalendar
    
    def fetch_data(self, **kwargs):
        """从 Tushare 获取交易日历"""
        return tushare_client.get_trade_cal(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        """转换交易日历数据"""
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        
        records = df.to_dict(orient='records')
        
        transformed = []
        for record in records:
            transformed.append({
                'exchange': record.get('exchange'),
                'cal_date': record.get('cal_date'),
                'is_open': record.get('is_open'),
            })
        
        return transformed