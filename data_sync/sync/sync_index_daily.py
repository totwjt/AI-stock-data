import pandas as pd
from datetime import datetime
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
    
    async def sync_incremental(self, start_date: str = None, end_date: str = None, ts_code: str = None):
        """增量同步 - 支持指定指数代码"""
        if not ts_code:
            raise ValueError("ts_code 是必填参数")
        
        if not start_date:
            start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        start_time = datetime.now()
        self.logger.info(f"开始增量同步 {self.__class__.__name__}, 指数: {ts_code}, 日期范围: {start_date} - {end_date}")
        
        try:
            df = self.fetch_data(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                self.logger.warning("未获取到数据")
                return 0
            
            data_list = self.transform_data(df)
            
            total = 0
            for i in range(0, len(data_list), self.batch_size):
                batch = data_list[i:i + self.batch_size]
                count = await self.upsert_data(batch)
                total += count
                self.logger.info(f"已写入 {total} 条数据")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"增量同步完成，共写入 {total} 条数据，耗时 {duration:.2f} 秒")
            return total
            
        except Exception as e:
            self.logger.error(f"增量同步失败: {str(e)}")
            await self.db.rollback()
            raise
    
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