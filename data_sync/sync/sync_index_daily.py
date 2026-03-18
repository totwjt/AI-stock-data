import pandas as pd
from datetime import datetime
from typing import List, Set
import asyncio
from sqlalchemy import select, func
from data_sync.sync.base import BaseSync
from data_sync.models.index_daily import IndexDaily
from data_sync.tushare_client import tushare_client


class IndexDailySync(BaseSync):
    
    INDEX_CODES = ["000001.SH", "399001.SZ", "399006.SZ", "000300.SH"]
    
    def get_table_model(self):
        return IndexDaily
    
    def fetch_data(self, **kwargs):
        return tushare_client.get_index_daily(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
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
    
    async def _get_existing_trade_dates(self) -> Set[str]:
        result = await self.db.execute(
            select(IndexDaily.trade_date).distinct()
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
    
    async def _get_sync_status(self) -> dict:
        result = await self.db.execute(
            select(
                func.count(IndexDaily.ts_code).label('total_records'),
                func.count(func.distinct(IndexDaily.ts_code)).label('total_stocks'),
                func.count(func.distinct(IndexDaily.trade_date)).label('total_dates'),
            )
        )
        row = result.first()
        return {
            'total_records': row.total_records or 0,
            'total_stocks': row.total_stocks or 0,
            'total_dates': row.total_dates or 0,
        }
    
    async def sync_year(self, year: int, max_concurrent: int = 5):
        start_time = datetime.now()
        self.logger.info(f"开始同步 {year} 年指数数据")
        
        try:
            existing_dates = await self._get_existing_trade_dates()
            trade_dates = await self._get_trade_dates_of_year(year)
            need_sync = [d for d in trade_dates if d not in existing_dates]
            
            self.logger.info(f"{year} 年: 已有 {len(existing_dates)} 个交易日，需同步 {len(need_sync)} 个")
            
            if not need_sync:
                return 0
            
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def sync_one_date(trade_date: str):
                async with semaphore:
                    try:
                        all_data = []
                        for ts_code in self.INDEX_CODES:
                            df = self.fetch_data(ts_code=ts_code, trade_date=trade_date)
                            if df is not None and not df.empty:
                                all_data.append(df)
                        
                        if not all_data:
                            return 0
                        
                        import pandas as pd
                        combined_df = pd.concat(all_data, ignore_index=True)
                        data_list = self.transform_data(combined_df)
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
    
    async def sync_all_years(self, start_year: int = None, end_year: int = None):
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = end_year - 10
        
        start_time = datetime.now()
        
        status = await self._get_sync_status()
        self.logger.info(f"当前同步状态: {status['total_stocks']} 个指数, {status['total_dates']} 个交易日")
        self.logger.info(f"开始全量同步，年份范围: {start_year} - {end_year}")
        
        try:
            total_count = 0
            
            for year in range(end_year, start_year - 1, -1):
                count = await self.sync_year(year)
                total_count += count
            
            status = await self._get_sync_status()
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"全量同步完成: {status['total_stocks']} 个指数, {status['total_dates']} 个交易日, 共 {status['total_records']} 条记录, 耗时 {duration:.2f} 秒")
            
            return total_count
            
        except Exception as e:
            self.logger.error(f"全量同步失败: {str(e)}")
            raise
    
    async def sync_incremental(self):
        end_year = datetime.now().year
        start_year = end_year - 10
        
        status = await self._get_sync_status()
        
        for year in range(end_year, start_year - 1, -1):
            trade_dates = await self._get_trade_dates_of_year(year)
            existing_dates = await self._get_existing_trade_dates()
            need_sync = [d for d in trade_dates if d not in existing_dates]
            
            if need_sync:
                max_date = max(need_sync)
                self.logger.info(f"增量同步: 最新缺失日期 {max_date}")
                
                all_data = []
                for ts_code in self.INDEX_CODES:
                    df = self.fetch_data(ts_code=ts_code, trade_date=max_date)
                    if df is not None and not df.empty:
                        all_data.append(df)
                
                if not all_data:
                    return 0
                
                import pandas as pd
                combined_df = pd.concat(all_data, ignore_index=True)
                data_list = self.transform_data(combined_df)
                if not data_list:
                    return 0
                
                count = await self.upsert_data(data_list)
                return count
        
        self.logger.info("所有数据已同步，无需增量")
        return 0
