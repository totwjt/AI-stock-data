import pandas as pd
from datetime import datetime, timedelta
from typing import List, Set, Dict
import asyncio
from sqlalchemy import select, func
from data_sync.sync.base import BaseSync
from data_sync.models.stock_factor_pro import StockFactorPro
from data_sync.models.trade_calendar import TradeCalendar
from data_sync.tushare_client import tushare_client
from data_sync.sync.sync_state import sync_state_manager


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
    
    async def _get_existing_trade_dates(self) -> Set[str]:
        result = await self.db.execute(
            select(StockFactorPro.trade_date).distinct()
        )
        return set(row[0] for row in result.fetchall())
    
    async def _get_expected_trade_dates(self, year: int) -> List[str]:
        result = await self.db.execute(
            select(TradeCalendar.cal_date)
            .where(TradeCalendar.cal_date >= f"{year}0101")
            .where(TradeCalendar.cal_date <= f"{year}1231")
            .where(TradeCalendar.is_open == 1)
        )
        return [row[0] for row in result.fetchall()]
    
    async def verify_year(self, year: int) -> Dict:
        expected_dates = await self._get_expected_trade_dates(year)
        existing_dates = await self._get_existing_trade_dates()
        
        today = datetime.now()
        current_year = today.year
        is_before_16 = today.hour < 16
        
        expected_set = set(expected_dates)
        actual_set = existing_dates & expected_set
        
        if year == current_year and is_before_16:
            yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
            expected_set = {d for d in expected_set if f"{year}0101" <= d <= yesterday}
            actual_set = actual_set & expected_set
            note = f'16点前，验证范围: {year}0101 ~ {yesterday}'
        else:
            note = ''
        
        missing_set = expected_set - actual_set
        
        result = {
            'year': year,
            'verified': len(actual_set) == len(expected_set) and len(expected_set) > 0,
            'expected_dates': len(expected_set),
            'actual_dates': len(actual_set),
            'missing_dates': sorted(missing_set),
            'note': note
        }
        
        if result['verified']:
            sync_state_manager.mark_year_verified('stk_factor_pro', year, len(expected_set))
        else:
            sync_state_manager.mark_year_incomplete('stk_factor_pro', year)
        
        return result
    
    async def verify_all_years(self, start_year: int = None, end_year: int = None) -> List[Dict]:
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = end_year - 10
        
        results = []
        for year in range(end_year, start_year - 1, -1):
            self.logger.info(f"验证 {year} 年...")
            result = await self.verify_year(year)
            results.append(result)
        
        return results
    
    async def _get_sync_status(self) -> dict:
        result = await self.db.execute(
            select(
                func.count(StockFactorPro.ts_code).label('total_records'),
                func.count(func.distinct(StockFactorPro.ts_code)).label('total_stocks'),
                func.count(func.distinct(StockFactorPro.trade_date)).label('total_dates'),
            )
        )
        row = result.first()
        return {
            'total_records': row.total_records or 0,
            'total_stocks': row.total_stocks or 0,
            'total_dates': row.total_dates or 0,
        }
    
    async def sync(self, start_year: int = None, end_year: int = None, max_concurrent: int = 10):
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = end_year - 10
        
        start_time = datetime.now()
        self.logger.info(f"=== 批量同步开始 ===")
        self.logger.info(f"年份范围: {start_year} - {end_year}")
        
        total_synced = 0
        
        for year in range(end_year, start_year - 1, -1):
            if sync_state_manager.is_year_verified('stk_factor_pro', year):
                self.logger.info(f"[{year}] 已验证，跳过")
                continue
            
            self.logger.info(f"[{year}] 开始同步...")
            
            existing_dates = await self._get_existing_trade_dates()
            expected_dates = await self._get_expected_trade_dates(year)
            
            missing_dates = [d for d in expected_dates if d not in existing_dates]
            
            if not missing_dates:
                self.logger.info(f"[{year}] 无缺失数据")
                sync_state_manager.mark_year_verified('stk_factor_pro', year, len(expected_dates))
                continue
            
            self.logger.info(f"[{year}] 缺失 {len(missing_dates)} 个日期")
            
            year_synced = 0
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def sync_one_date(trade_date: str):
                nonlocal year_synced
                async with semaphore:
                    try:
                        df = self.fetch_data(trade_date=trade_date)
                        if df is None or df.empty:
                            return
                        
                        data_list = self.transform_data(df)
                        if not data_list:
                            return
                        
                        count = await self.upsert_data(data_list, auto_commit=False)
                        year_synced += count
                        self.logger.info(f"[{year}] {trade_date}: +{count}")
                    except Exception as e:
                        self.logger.warning(f"[{year}] {trade_date} 失败: {e}")
            
            tasks = [sync_one_date(d) for d in missing_dates]
            await asyncio.gather(*tasks)
            
            await self.db.commit()
            
            total_synced += year_synced
            self.logger.info(f"[{year}] 完成: +{year_synced} 条")
            
            verify_result = await self.verify_year(year)
            if verify_result['verified']:
                self.logger.info(f"[{year}] 验证通过")
            else:
                self.logger.warning(f"[{year}] 验证不完整 ({verify_result['actual_dates']}/{verify_result['expected_dates']})")
        
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"=== 批量同步完成 ===")
        self.logger.info(f"总耗时: {duration:.1f} 秒")
        self.logger.info(f"新增数据: {total_synced} 条")
        
        return total_synced
    
    async def sync_full(self, start_year: int = None, end_year: int = None):
        return await self.sync(start_year, end_year)
    
    async def sync_incremental(self, start_date: str = None, end_date: str = None):
        return await self.sync(start_date, end_date)
    
    async def sync_history_by_year(self, start_year: int = None, end_year: int = None, force: bool = False):
        return await self.sync(start_year, end_year)
    
    async def sync_year_by_trade_date(self, year: int, max_concurrent: int = 10, force: bool = False):
        return await self.sync(year, year)
    
    async def sync_recent(self, days: int = 3):
        today = datetime.now()
        trade_dates = []
        
        # 16:00 后包含当天
        include_today = today.hour >= 16
        
        for i in range(0 if include_today else 1, days + 20):
            if i == 0:
                date_str = today.strftime('%Y%m%d')
            else:
                check_date = today - timedelta(days=i)
                date_str = check_date.strftime('%Y%m%d')
            
            result = await self.db.execute(
                select(TradeCalendar.cal_date)
                .where(TradeCalendar.cal_date == date_str)
                .where(TradeCalendar.is_open == 1)
            )
            if result.fetchone():
                trade_dates.append(date_str)
                if len(trade_dates) >= days:
                    break
        
        if not trade_dates:
            self.logger.info("未找到最近的交易日")
            return 0
        
        self.logger.info(f"增量同步最近 {len(trade_dates)} 个交易日: {trade_dates}")
        
        # 直接同步这些日期的数据
        semaphore = asyncio.Semaphore(10)
        total_synced = 0
        
        async def sync_one_date(trade_date: str):
            nonlocal total_synced
            async with semaphore:
                try:
                    df = self.fetch_data(trade_date=trade_date)
                    if df is None or df.empty:
                        self.logger.warning(f"{trade_date}: 无数据")
                        return
                    
                    data_list = self.transform_data(df)
                    if not data_list:
                        return
                    
                    count = await self.upsert_data(data_list, auto_commit=False)
                    total_synced += count
                    self.logger.info(f"{trade_date}: +{count}")
                except Exception as e:
                    self.logger.warning(f"{trade_date} 失败: {e}")
        
        tasks = [sync_one_date(d) for d in trade_dates]
        await asyncio.gather(*tasks)
        await self.db.commit()
        
        self.logger.info(f"增量同步完成: +{total_synced} 条")
        return total_synced