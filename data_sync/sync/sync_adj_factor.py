import pandas as pd
from datetime import datetime
from typing import List
from sqlalchemy import select
from data_sync.sync.base import BaseSync
from data_sync.models.stock_adj_factor import StockAdjFactor
from data_sync.models.stock_basic import StockBasic
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
    
    async def sync_by_stock(self, start_date: str = None, end_date: str = None):
        """按股票列表逐只同步复权因子（只同步上市股票）"""
        start_time = datetime.now()
        self.logger.info(f"开始按股票同步复权因子，日期范围: {start_date} - {end_date}")
        
        try:
            # 1. 获取上市股票列表
            stock_codes = await self._get_listed_stock_codes()
            self.logger.info(f"获取到 {len(stock_codes)} 只上市股票")
            
            if not stock_codes:
                self.logger.warning("未找到上市股票")
                return 0
            
            # 2. 按股票逐只同步
            total = 0
            for i, ts_code in enumerate(stock_codes):
                try:
                    # 获取单只股票的复权因子
                    df = tushare_client.get_adj_factor(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if df is not None and not df.empty:
                        data_list = self.transform_data(df)
                        count = await self.upsert_data(data_list)
                        total += count
                        self.logger.info(f"[{i+1}/{len(stock_codes)}] {ts_code}: 写入 {count} 条数据")
                    else:
                        self.logger.info(f"[{i+1}/{len(stock_codes)}] {ts_code}: 无数据")
                        
                except Exception as e:
                    self.logger.warning(f"[{i+1}/{len(stock_codes)}] {ts_code}: 同步失败 - {str(e)}")
                    continue
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"按股票同步完成，共写入 {total} 条数据，耗时 {duration:.2f} 秒")
            return total
            
        except Exception as e:
            self.logger.error(f"按股票同步失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def _get_listed_stock_codes(self) -> List[str]:
        """获取股票列表（包括所有股票，因为list_status可能为空）"""
        result = await self.db.execute(
            select(StockBasic.ts_code)
        )
        return [row[0] for row in result.fetchall()]
    
    # 兼容旧的增量同步接口（按日期范围同步所有股票）
    async def sync_incremental(self, start_date: str = None, end_date: str = None):
        """增量同步 - 按日期范围同步（兼容旧接口）"""
        return await self.sync_by_stock(start_date, end_date)