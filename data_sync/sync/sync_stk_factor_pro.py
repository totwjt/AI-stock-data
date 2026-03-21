import pandas as pd
from datetime import datetime, timedelta
from typing import List, Set, Dict
import asyncio
import math
from sqlalchemy import select, func
from data_sync.sync.base import BaseSync
from data_sync.models.stock_factor_pro import StockFactorPro
from data_sync.models.trade_calendar import TradeCalendar
from data_sync.tushare_client import tushare_client
from data_sync.sync.sync_state import sync_state_manager


class StkFactorProSync(BaseSync):
    manual_full_min_coverage_ratio = 0.98
    manual_full_batch_size = 5
    manual_full_batch_sleep = 2.0
    
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
    
    async def sync(self, start_year: int = None, end_year: int = None, max_concurrent: int = 1):
        """
        批量同步技术面因子数据
        
        max_concurrent: 并发数，默认1（避免触发Tushare限流）
        """
        # 限流：每分钟约30次请求，单请求约2秒，1并发+0延迟刚好不超限
        if max_concurrent > 3:
            self.logger.warning(f"并发数 {max_concurrent} 过高，可能触发限流，已自动降为1")
            max_concurrent = 1
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
                    await asyncio.sleep(0.2)
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
    
    async def sync_full(
        self,
        start_date: str = None,
        end_date: str = None,
        start_year: int = None,
        end_year: int = None,
    ):
        if start_year is not None or end_year is not None:
            return await self.sync(start_year, end_year)
        return await self.sync_recent_history(start_date, end_date)
    
    async def sync_incremental(self, start_date: str = None, end_date: str = None):
        if start_date or end_date:
            return await self.sync_recent_history(start_date, end_date)
        return await self.sync_recent()
    
    async def sync_history_by_year(self, start_year: int = None, end_year: int = None, force: bool = False):
        if start_year is not None or end_year is not None:
            return await self.sync(start_year, end_year)
        return await self.sync_recent_history()
    
    async def sync_year_by_trade_date(self, year: int, max_concurrent: int = 1, force: bool = False):
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
        
        semaphore = asyncio.Semaphore(1)
        total_synced = 0
        
        async def sync_one_date(trade_date: str):
            nonlocal total_synced
            async with semaphore:
                await asyncio.sleep(0.2)
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

    async def _get_year_coverage(self, year: int) -> Dict:
        expected_dates = await self._get_expected_trade_dates(year)
        actual_counts = await self.get_actual_counts_by_trade_date(f"{year}0101", f"{year}1231")
        
        today = datetime.now()
        current_year = today.year
        is_before_16 = today.hour < 16
        
        if year == current_year and is_before_16:
            yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
            expected_dates = [d for d in expected_dates if d <= yesterday]
        
        if not expected_dates:
            return {'year': year, 'coverage': 1.0, 'expected': 0, 'actual': 0, 'skip': True}
        
        actual = sum(1 for d in expected_dates if actual_counts.get(d, 0) > 0)
        coverage = actual / len(expected_dates) if expected_dates else 0
        
        return {
            'year': year,
            'coverage': coverage,
            'expected': len(expected_dates),
            'actual': actual,
            'skip': coverage >= self.manual_full_min_coverage_ratio
        }
    
    async def _get_month_coverage(self, year: int, month: int) -> Dict:
        month_start = f"{year}{month:02d}01"
        if month == 12:
            month_end = f"{year + 1}0101"
        else:
            month_end = f"{year}{month + 1:02d}01"
        
        result = await self.db.execute(
            select(TradeCalendar.cal_date)
            .where(TradeCalendar.cal_date >= month_start)
            .where(TradeCalendar.cal_date < month_end)
            .where(TradeCalendar.is_open == 1)
        )
        expected_dates = [row[0] for row in result.fetchall()]
        
        today = datetime.now()
        current_year = today.year
        is_before_16 = today.hour < 16
        
        if year == current_year and is_before_16:
            yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
            expected_dates = [d for d in expected_dates if d <= yesterday]
        
        if not expected_dates:
            return {'year': year, 'month': month, 'coverage': 1.0, 'expected': 0, 'actual': 0, 'skip': True}
        
        actual_counts = await self.get_actual_counts_by_trade_date(expected_dates[0], expected_dates[-1])
        actual = sum(1 for d in expected_dates if actual_counts.get(d, 0) > 0)
        coverage = actual / len(expected_dates) if expected_dates else 0
        
        return {
            'year': year,
            'month': month,
            'coverage': coverage,
            'expected': len(expected_dates),
            'actual': actual,
            'skip': coverage >= self.manual_full_min_coverage_ratio
        }
    
    async def _get_missing_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        actual_counts = await self.get_actual_counts_by_trade_date(start_date, end_date)
        target_coverage = await self.get_max_trade_date_coverage(start_date, end_date)
        min_required = math.ceil(target_coverage * self.manual_full_min_coverage_ratio) if target_coverage > 0 else 0
        
        trade_dates = await self.get_trade_dates_in_range(start_date, end_date)
        missing = []
        for trade_date in trade_dates:
            existing = actual_counts.get(trade_date, 0)
            if existing <= 0 or (min_required > 0 and existing < min_required):
                missing.append(trade_date)
        return missing

    async def sync_recent_history(self, start_date: str = None, end_date: str = None):
        start_date, end_date = self.get_manual_sync_date_range(start_date, end_date)
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        self.logger.info(f"stock_factor_pro 手动全量补齐: {start_date} - {end_date}")
        
        years_to_sync = []
        
        for year in range(end_year, start_year - 1, -1):
            year_info = await self._get_year_coverage(year)
            self.logger.info(f"[{year}] 覆盖度: {year_info['actual']}/{year_info['expected']} ({year_info['coverage']*100:.1f}%)")
            
            if year_info['skip']:
                self.logger.info(f"[{year}] 跳过 (≥{self.manual_full_min_coverage_ratio*100:.0f}%)")
                continue
            
            months_to_sync = []
            
            for month in range(1, 13):
                month_info = await self._get_month_coverage(year, month)
                
                if month_info['expected'] == 0:
                    continue
                
                if month_info['skip']:
                    self.logger.info(f"  [{year}-{month:02d}] 跳过 ({month_info['actual']}/{month_info['expected']})")
                    continue
                
                months_to_sync.append(month)
            
            if not months_to_sync:
                continue
            
            year_missing = []
            for month in months_to_sync:
                if month == 12:
                    month_start = f"{year}{month:02d}01"
                    month_end = f"{year + 1}0101"
                else:
                    month_start = f"{year}{month:02d}01"
                    month_end = f"{year}{month + 1:02d}01"
                
                missing = await self._get_missing_trade_dates(month_start, month_end)
                year_missing.extend(missing)
                if missing:
                    self.logger.info(f"  [{year}-{month:02d}] 需补: {len(missing)} 天")
            
            if year_missing:
                years_to_sync.append({'year': year, 'missing': year_missing})
        
        all_missing = []
        for y in years_to_sync:
            all_missing.extend(y['missing'])
        
        if not all_missing:
            self.logger.info("stock_factor_pro 近三年无需手动补齐")
            return 0

        self.logger.info(f"待补: {len(all_missing)} 个交易日")

        total_synced = 0
        semaphore = asyncio.Semaphore(1)
        total_batches = math.ceil(len(all_missing) / self.manual_full_batch_size)
        processed_batches = 0

        async def sync_one_date(trade_date: str):
            nonlocal total_synced
            async with semaphore:
                await asyncio.sleep(0.5)
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
                    self.logger.warning(f"{trade_date} 补齐失败: {e}")

        for i in range(0, len(all_missing), self.manual_full_batch_size):
            batch = all_missing[i:i + self.manual_full_batch_size]
            await asyncio.gather(*[sync_one_date(d) for d in batch])
            await self.db.commit()
            processed_batches += 1
            if i + self.manual_full_batch_size < len(all_missing):
                await asyncio.sleep(self.manual_full_batch_sleep)
                self.logger.info(f"stock_factor_pro 批次进度: {processed_batches}/{total_batches}")

        self.logger.info(f"stock_factor_pro 手动全量补齐完成: +{total_synced} 条")
        return total_synced
