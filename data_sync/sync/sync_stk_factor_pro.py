import pandas as pd
from datetime import datetime
from typing import List, Set
import asyncio
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
    
    async def _get_existing_trade_dates_for_year(self, year: int) -> Set[str]:
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        
        result = await self.db.execute(
            select(StockFactorPro.trade_date)
            .where(StockFactorPro.trade_date >= start_date)
            .where(StockFactorPro.trade_date <= end_date)
            .distinct()
        )
        return set(row[0] for row in result.fetchall())
    
    async def _get_trade_dates_of_year(self, year: int) -> List[str]:
        from data_sync.models.trade_calendar import TradeCalendar
        
        result = await self.db.execute(
            select(TradeCalendar.cal_date)
            .where(TradeCalendar.cal_date >= f"{year}0101")
            .where(TradeCalendar.cal_date <= f"{year}1231")
            .where(TradeCalendar.is_open == 1)
        )
        return [row[0] for row in result.fetchall()]
    
    async def sync_year_by_trade_date(self, year: int, max_concurrent: int = 10):
        start_time = datetime.now()
        self.logger.info(f"开始同步 {year} 年数据（按交易日批量获取）")
        
        try:
            existing_dates = await self._get_existing_trade_dates_for_year(year)
            self.logger.info(f"{year} 年已有 {len(existing_dates)} 个交易日数据")
            
            trade_dates = await self._get_trade_dates_of_year(year)
            need_sync = [d for d in trade_dates if d not in existing_dates]
            
            self.logger.info(f"{year} 年需要同步 {len(need_sync)} 个交易日")
            
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def sync_one_date(trade_date: str):
                async with semaphore:
                    try:
                        df = self.fetch_data(trade_date=trade_date)
                        if df is None or df.empty:
                            return 0
                        
                        data_list = self.transform_data(df)
                        if not data_list:
                            return 0
                        
                        return await self.upsert_data(data_list)
                    except Exception as e:
                        self.logger.warning(f"日期 {trade_date} 同步失败: {e}")
                        return 0
            
            tasks = [sync_one_date(d) for d in need_sync]
            results = await asyncio.gather(*tasks)
            
            total_count = sum(results)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"{year} 年同步完成，新增 {total_count} 条数据，耗时 {duration:.2f} 秒")
            
            return total_count
            
        except Exception as e:
            self.logger.error(f"{year} 年同步失败: {str(e)}")
            raise
    
    async def sync_history_by_year(self, start_year: int = None, end_year: int = None):
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = datetime.now().year - 10
        
        start_time = datetime.now()
        self.logger.info(f"开始按年同步，年份范围: {start_year} - {end_year}")
        
        try:
            total_count = 0
            
            for year in range(end_year, start_year - 1, -1):
                count = await self.sync_year_by_trade_date(year)
                total_count += count
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"同步完成，共写入 {total_count} 条数据，耗时 {duration:.2f} 秒")
            
            return total_count
            
        except Exception as e:
            self.logger.error(f"同步失败: {str(e)}")
            raise
