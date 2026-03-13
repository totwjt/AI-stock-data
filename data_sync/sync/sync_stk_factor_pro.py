import pandas as pd
from datetime import datetime
from typing import List
from sqlalchemy import select, func
from data_sync.sync.base import BaseSync
from data_sync.models.stock_factor_pro import StockFactorPro
from data_sync.models.stock_basic import StockBasic
from data_sync.tushare_client import tushare_client


class StkFactorProSync(BaseSync):
    
    def get_table_model(self):
        return StockFactorPro
    
    def fetch_data(self, **kwargs):
        return tushare_client.get_stk_factor_pro(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        return df.to_dict(orient='records')
    
    async def _get_listed_stock_codes(self) -> List[str]:
        result = await self.db.execute(
            select(StockBasic.ts_code)
        )
        return [row[0] for row in result.fetchall()]
    
    async def _has_data_for_year(self, ts_code: str, year: int) -> bool:
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        
        result = await self.db.execute(
            select(func.count(StockFactorPro.trade_date))
            .where(StockFactorPro.ts_code == ts_code)
            .where(StockFactorPro.trade_date >= start_date)
            .where(StockFactorPro.trade_date <= end_date)
        )
        count = result.scalar()
        return count is not None and count > 0
    
    async def sync_stock_by_year(self, ts_code: str, year: int):
        if await self._has_data_for_year(ts_code, year):
            self.logger.debug(f"股票 {ts_code} 在 {year} 年已有数据，跳过")
            return 0
        
        start_time = datetime.now()
        self.logger.info(f"开始同步股票 {ts_code} 的 {year} 年数据")
        
        try:
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            
            df = self.fetch_data(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                self.logger.info(f"股票 {ts_code} 在 {year} 年无数据")
                return 0
            
            data_list = self.transform_data(df)
            
            if not data_list:
                self.logger.info(f"股票 {ts_code} 在 {year} 年数据转换结果为空")
                return 0
            
            count = await self.upsert_data(data_list)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"股票 {ts_code} 在 {year} 年同步完成，写入 {count} 条数据，耗时 {duration:.2f} 秒")
            
            return count
            
        except Exception as e:
            self.logger.error(f"股票 {ts_code} 在 {year} 年同步失败: {str(e)}")
            raise
    
    async def sync_history_by_year(self, start_year: int = None, end_year: int = None):
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = datetime.now().year - 10
        
        start_time = datetime.now()
        self.logger.info(f"开始按年份分段同步历史数据，年份范围: {start_year} - {end_year} （优先同步最近年份）")
        
        try:
            stock_codes = await self._get_listed_stock_codes()
            self.logger.info(f"获取到 {len(stock_codes)} 只股票")
            
            total_count = 0
            
            for year in range(end_year, start_year - 1, -1):
                self.logger.info(f"开始同步 {year} 年数据...")
                
                for i, ts_code in enumerate(stock_codes):
                    try:
                        count = await self.sync_stock_by_year(ts_code, year)
                        total_count += count
                        
                        if (i + 1) % 10 == 0:
                            self.logger.info(f"已处理 {i + 1}/{len(stock_codes)} 只股票，当前年份 {year}")
                    
                    except Exception as e:
                        self.logger.warning(f"股票 {ts_code} 在 {year} 年同步失败: {str(e)}")
                        continue
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"按年份分段同步完成（优先最近年份），共写入 {total_count} 条数据，耗时 {duration:.2f} 秒")
            
            return total_count
            
        except Exception as e:
            self.logger.error(f"按年份分段同步失败: {str(e)}")
            raise
