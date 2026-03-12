import pandas as pd
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
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
    
    async def sync_incremental(self, **kwargs):
        """增量同步 - 集合差集过滤，只同步新增股票"""
        start_time = datetime.now()
        self.logger.info(f"开始增量同步 {self.__class__.__name__}")
        
        try:
            # 1. 获取数据库已有股票列表
            existing_codes = await self._get_existing_ts_codes()
            self.logger.info(f"数据库已有 {len(existing_codes)} 只股票")
            
            # 2. 获取Tushare最新股票列表
            df = self.fetch_data(**kwargs)
            if df is None or df.empty:
                self.logger.warning("未获取到股票列表数据")
                return 0
            
            # 3. 集合差集找出新增股票
            all_ts_codes = set(df['ts_code'].tolist())
            new_ts_codes = all_ts_codes - existing_codes
            self.logger.info(f"发现 {len(new_ts_codes)} 只新增股票")
            
            if not new_ts_codes:
                self.logger.info("无新增股票，跳过同步")
                return 0
            
            # 4. 过滤新增股票数据
            new_df = df[df['ts_code'].isin(new_ts_codes)]
            data_list = self.transform_data(new_df)
            
            # 5. 批量写入新增股票
            total = 0
            for i in range(0, len(data_list), self.batch_size):
                batch = data_list[i:i + self.batch_size]
                count = await self.upsert_data(batch)
                total += count
                self.logger.info(f"已写入 {total} 条新增股票数据")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"增量同步完成，共写入 {total} 条新增股票数据，耗时 {duration:.2f} 秒")
            return total
            
        except Exception as e:
            self.logger.error(f"增量同步失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def _get_existing_ts_codes(self) -> set:
        """获取数据库中已有的股票代码"""
        result = await self.db.execute(
            select(StockBasic.ts_code)
        )
        return {row[0] for row in result.fetchall()}