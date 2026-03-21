import pandas as pd
from datetime import datetime, timedelta
from typing import List, Set, Dict
import asyncio
import math
from sqlalchemy import select, func
from data_sync.sync.base import BaseSync
from data_sync.models.stock_daily import StockDaily
from data_sync.models.trade_calendar import TradeCalendar
from data_sync.tushare_client import tushare_client
from data_sync.sync.sync_state import sync_state_manager


class DailySync(BaseSync):
    manual_full_min_coverage_ratio = 0.98
    
    def get_table_model(self):
        return StockDaily
    
    def fetch_data(self, **kwargs):
        return tushare_client.get_daily(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        
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
            select(StockDaily.trade_date).distinct()
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
        today_str = today.strftime('%Y%m%d')
        is_before_16 = today.hour < 16
        
        expected_set = set(expected_dates)
        actual_set = existing_dates & expected_set
        
        year_start = f"{year}0101"
        
        # 本年度特殊逻辑：16点前验证昨天到年初
        if year == current_year and is_before_16:
            yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
            # 期望：从年初一到昨天
            expected_set = {d for d in expected_set if year_start <= d <= yesterday}
            # 实际：从年初一到昨天
            actual_set = actual_set & expected_set
            note = f'16点前，验证范围: {year_start} ~ {yesterday}'
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
            sync_state_manager.mark_year_verified('stock_daily', year, len(expected_set))
        else:
            sync_state_manager.mark_year_incomplete('stock_daily', year)
        
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
                func.count(StockDaily.ts_code).label('total_records'),
                func.count(func.distinct(StockDaily.ts_code)).label('total_stocks'),
                func.count(func.distinct(StockDaily.trade_date)).label('total_dates'),
            )
        )
        row = result.first()
        return {
            'total_records': row.total_records or 0,
            'total_stocks': row.total_stocks or 0,
            'total_dates': row.total_dates or 0,
        }
    
    async def sync(self, start_year: int = None, end_year: int = None, max_concurrent: int = 10):
        """批量同步 - 唯一同步逻辑
        
        每次执行都：
        1. 读取状态文件，获取已验证年份
        2. 对未验证年份，查询缺失的日期
        3. 同步缺失日期
        4. 验证完成后标记年份为已验证
        """
        if end_year is None:
            end_year = datetime.now().year
        if start_year is None:
            start_year = end_year - 10
        
        start_time = datetime.now()
        self.logger.info(f"=== 批量同步开始 ===")
        self.logger.info(f"年份范围: {start_year} - {end_year}")
        
        total_synced = 0
        
        for year in range(end_year, start_year - 1, -1):
            if sync_state_manager.is_year_verified('stock_daily', year):
                self.logger.info(f"[{year}] 已验证，跳过")
                continue
            
            self.logger.info(f"[{year}] 开始同步...")
            
            existing_dates = await self._get_existing_trade_dates()
            expected_dates = await self._get_expected_trade_dates(year)
            
            missing_dates = [d for d in expected_dates if d not in existing_dates]
            
            if not missing_dates:
                self.logger.info(f"[{year}] 无缺失数据")
                sync_state_manager.mark_year_verified('stock_daily', year, len(expected_dates))
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
            is_complete = verify_result['verified']
            expected = verify_result['expected_dates']
            actual = verify_result['actual_dates']
            if is_complete:
                self.logger.info(f"[{year}] 验证通过 ✓")
            else:
                self.logger.warning(f"[{year}] 验证不完整 ({actual}/{expected})")
        
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
        """增量同步 - 同步指定日期范围的数据，默认近3天"""
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")
        
        start_time = datetime.now()
        self.logger.info(f"增量同步: 日期范围 {start_date} - {end_date}")
        
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        total_synced = 0
        
        for year in range(end_year, start_year - 1, -1):
            existing_dates = await self._get_existing_trade_dates()
            expected_dates = await self._get_expected_trade_dates(year)
            
            year_start = max(start_date, f"{year}0101")
            year_end = min(end_date, f"{year}1231")
            
            missing = [d for d in expected_dates if year_start <= d <= year_end and d not in existing_dates]
            
            if not missing:
                continue
            
            self.logger.info(f"[{year}] 同步 {len(missing)} 个日期")
            
            year_synced = 0
            semaphore = asyncio.Semaphore(10)
            
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
            
            tasks = [sync_one_date(d) for d in missing]
            await asyncio.gather(*tasks)
            await self.db.commit()
            
            total_synced += year_synced
        
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"增量同步完成: 共写入 {total_synced} 条，耗时 {duration:.2f} 秒")
        return total_synced
    
    async def sync_all_years(self, start_year: int = None, end_year: int = None):
        if start_year is not None or end_year is not None:
            return await self.sync(start_year, end_year)
        return await self.sync_recent_history()

    async def sync_recent_history(
        self,
        start_date: str = None,
        end_date: str = None,
        max_concurrent: int = 10,
    ):
        start_date, end_date = self.get_manual_sync_date_range(start_date, end_date)
        trade_dates = await self.get_trade_dates_in_range(start_date, end_date)
        actual_counts = await self.get_actual_counts_by_trade_date(start_date, end_date)
        target_coverage = await self.get_max_trade_date_coverage(start_date, end_date)

        if target_coverage <= 0:
            self.logger.info(f"stock_daily 手动全量补齐: {start_date} - {end_date}，当前无基准覆盖，按全部交易日补齐")
        else:
            self.logger.info(
                f"stock_daily 手动全量补齐: {start_date} - {end_date}，目标覆盖数 >= {target_coverage}"
            )

        missing_dates = []
        min_required = math.ceil(target_coverage * self.manual_full_min_coverage_ratio) if target_coverage > 0 else 0
        for trade_date in trade_dates:
            existing = actual_counts.get(trade_date, 0)
            if existing <= 0 or (min_required > 0 and existing < min_required):
                missing_dates.append(trade_date)

        if not missing_dates:
            self.logger.info("stock_daily 近三年无需手动补齐")
            return 0

        total_synced = 0
        semaphore = asyncio.Semaphore(max_concurrent)

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
                    self.logger.warning(f"{trade_date} 补齐失败: {e}")

        await asyncio.gather(*[sync_one_date(d) for d in missing_dates])
        await self.db.commit()
        self.logger.info(f"stock_daily 手动全量补齐完成: {len(missing_dates)} 个交易日, +{total_synced} 条")
        return total_synced
