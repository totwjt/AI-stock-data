#!/usr/bin/env python3
"""
数据完整性验证脚本 - 验证近3年数据是否完整

使用方法:
    python sync_verify.py                    # 验证全部表
    python sync_verify.py --tables daily      # 仅验证日线数据
    python sync_verify.py --tables daily adj_factor  # 验证指定表

目标表:
    stock_daily       - 股票日线行情
    stock_adj_factor  - 复权因子
    index_daily       - 指数日线行情
    stock_daily_basic - 每日基本面指标
    stock_factor_pro  - 技术面因子
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_sync.database import async_session, init_db
from data_sync.sync import (
    DailySync,
    AdjFactorSync,
    DailyBasicSync,
    IndexDailySync,
    StkFactorProSync,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TableVerifier:
    
    def __init__(self, db):
        self.db = db
        self.now = datetime.now()
        self.current_year = self.now.year
        self.is_before_16 = self.now.hour < 16
        self.today_str = self.now.strftime('%Y%m%d')
        self.yesterday_str = (self.now - timedelta(days=1)).strftime('%Y%m%d')
    
    def get_year_end_date(self, year: int) -> str:
        if year == self.current_year:
            if self.is_before_16:
                return self.yesterday_str
            return self.today_str
        return f"{year}1231"
    
    async def verify_stock_daily(self) -> dict:
        sync = DailySync(self.db)
        results = []
        total_expected = 0
        total_actual = 0
        complete_years = 0
        
        for year in [self.current_year - 2, self.current_year - 1, self.current_year]:
            result = await sync.verify_year(year)
            results.append(result)
            total_expected += result['expected_dates']
            total_actual += result['actual_dates']
            if result['verified']:
                complete_years += 1
        
        return {
            'table': 'stock_daily',
            'description': '股票日线行情',
            'years': results,
            'total_expected': total_expected,
            'total_actual': total_actual,
            'complete_years': complete_years,
            'total_years': len(results),
            'coverage': total_actual / total_expected if total_expected > 0 else 0,
        }
    
    async def verify_stock_adj_factor(self) -> dict:
        sync = AdjFactorSync(self.db)
        
        from data_sync.models.trade_calendar import TradeCalendar
        from data_sync.models.stock_basic import StockBasic
        from sqlalchemy import select, func, and_, or_
        
        start_date = f"{self.current_year - 2}0101"
        end_date = self.get_year_end_date(self.current_year)
        
        expected_counts = await sync.get_expected_trade_date_counts_by_ts_code(start_date, end_date)
        actual_counts = await sync.get_actual_trade_date_counts_by_ts_code(start_date, end_date)
        
        total_expected = sum(expected_counts.values())
        total_actual = sum(actual_counts.values())
        complete_codes = sum(1 for code, exp in expected_counts.items() if actual_counts.get(code, 0) >= exp * 0.98)
        total_codes = len(expected_counts)
        
        missing_codes = [
            code for code, exp in expected_counts.items()
            if actual_counts.get(code, 0) < exp * 0.98
        ]
        
        return {
            'table': 'stock_adj_factor',
            'description': '复权因子',
            'total_expected': total_expected,
            'total_actual': total_actual,
            'complete_codes': complete_codes,
            'total_codes': total_codes,
            'coverage': total_actual / total_expected if total_expected > 0 else 0,
            'missing_sample': missing_codes[:10],
        }
    
    async def verify_index_daily(self) -> dict:
        from data_sync.models.trade_calendar import TradeCalendar
        from data_sync.models.index_daily import IndexDaily
        from sqlalchemy import select, func
        
        all_expected = 0
        all_actual = 0
        year_details = []
        
        for year in [self.current_year - 2, self.current_year - 1, self.current_year]:
            year_start = f"{year}0101"
            year_end = self.get_year_end_date(year)
            
            result = await self.db.execute(
                select(func.count(TradeCalendar.cal_date))
                .where(TradeCalendar.cal_date >= year_start)
                .where(TradeCalendar.cal_date <= year_end)
                .where(TradeCalendar.is_open == 1)
            )
            expected = result.scalar() or 0
            
            result = await self.db.execute(
                select(func.count(func.distinct(IndexDaily.trade_date)))
                .where(IndexDaily.trade_date >= year_start)
                .where(IndexDaily.trade_date <= year_end)
            )
            actual = result.scalar() or 0
            
            all_expected += expected
            all_actual += actual
            year_details.append({
                'year': year,
                'expected': expected,
                'actual': actual,
                'verified': actual >= expected * 0.98 if expected > 0 else False,
            })
        
        return {
            'table': 'index_daily',
            'description': '指数日线行情',
            'years': year_details,
            'total_expected': all_expected,
            'total_actual': all_actual,
            'coverage': all_actual / all_expected if all_expected > 0 else 0,
        }
    
    async def verify_stock_daily_basic(self) -> dict:
        from data_sync.models.trade_calendar import TradeCalendar
        from data_sync.models.stock_daily_basic import StockDailyBasic
        from sqlalchemy import select, func
        
        all_expected = 0
        all_actual = 0
        year_details = []
        
        for year in [self.current_year - 2, self.current_year - 1, self.current_year]:
            year_start = f"{year}0101"
            year_end = self.get_year_end_date(year)
            
            result = await self.db.execute(
                select(func.count(TradeCalendar.cal_date))
                .where(TradeCalendar.cal_date >= year_start)
                .where(TradeCalendar.cal_date <= year_end)
                .where(TradeCalendar.is_open == 1)
            )
            expected = result.scalar() or 0
            
            result = await self.db.execute(
                select(func.count(func.distinct(StockDailyBasic.trade_date)))
                .where(StockDailyBasic.trade_date >= year_start)
                .where(StockDailyBasic.trade_date <= year_end)
            )
            actual = result.scalar() or 0
            
            all_expected += expected
            all_actual += actual
            year_details.append({
                'year': year,
                'expected': expected,
                'actual': actual,
                'verified': actual >= expected * 0.98 if expected > 0 else False,
            })
        
        return {
            'table': 'stock_daily_basic',
            'description': '每日基本面指标',
            'years': year_details,
            'total_expected': all_expected,
            'total_actual': all_actual,
            'coverage': all_actual / all_expected if all_expected > 0 else 0,
        }
    
    async def verify_stock_factor_pro(self) -> dict:
        sync = StkFactorProSync(self.db)
        results = []
        total_expected = 0
        total_actual = 0
        complete_years = 0
        
        for year in [self.current_year - 2, self.current_year - 1, self.current_year]:
            result = await sync.verify_year(year)
            results.append(result)
            total_expected += result['expected_dates']
            total_actual += result['actual_dates']
            if result['verified']:
                complete_years += 1
        
        return {
            'table': 'stock_factor_pro',
            'description': '技术面因子',
            'years': results,
            'total_expected': total_expected,
            'total_actual': total_actual,
            'complete_years': complete_years,
            'total_years': len(results),
            'coverage': total_actual / total_expected if total_expected > 0 else 0,
        }


def print_result(result: dict):
    coverage = result['coverage'] * 100
    status = "✓ 完整" if coverage >= 98 else ("⚠ 部分" if coverage >= 50 else "✗ 不完整")
    
    print(f"\n{'='*60}")
    print(f"{result['table']} ({result['description']})")
    print(f"{'='*60}")
    print(f"覆盖度: {coverage:.1f}% {status}")
    print(f"预期交易日: {result['total_expected']}, 实际: {result['total_actual']}")
    
    if 'complete_years' in result:
        print(f"完整年份: {result['complete_years']}/{result['total_years']}")
    
    if 'years' in result:
        print("\n各年份详情:")
        for year_info in result['years']:
            if isinstance(year_info, dict) and 'year' in year_info:
                expected = year_info.get('expected_dates', year_info.get('expected', 0))
                actual = year_info.get('actual_dates', year_info.get('actual', 0))
                verified = year_info.get('verified', False)
                note = year_info.get('note', '')
                
                year_coverage = actual / expected * 100 if expected > 0 else 0
                year_status = "✓" if verified else "✗"
                
                note_str = f" ({note})" if note else ""
                print(f"  {year_info['year']}: {actual}/{expected} ({year_coverage:.1f}%) {year_status}{note_str}")
    
    if 'complete_codes' in result:
        print(f"完整股票: {result['complete_codes']}/{result['total_codes']}")
    
    if 'missing_sample' in result and result['missing_sample']:
        print(f"缺失股票示例: {result['missing_sample'][:5]}")


async def verify_tables(tables: list = None):
    await init_db()
    
    verifier_map = {
        'stock_daily': 'verify_stock_daily',
        'stock_adj_factor': 'verify_stock_adj_factor',
        'index_daily': 'verify_index_daily',
        'stock_daily_basic': 'verify_stock_daily_basic',
        'stock_factor_pro': 'verify_stock_factor_pro',
    }
    
    if tables is None:
        tables = list(verifier_map.keys())
    
    now = datetime.now()
    time_note = "16点前不含今天" if now.hour < 16 else "含今天"
    
    print("\n" + "="*60)
    print("数据完整性验证报告")
    print(f"验证范围: 近3年 ({now.year-2} - {now.year})")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M')} ({time_note})")
    print("="*60)
    
    results = {}
    
    async with async_session() as db:
        verifier = TableVerifier(db)
        
        for table in tables:
            if table not in verifier_map:
                logger.warning(f"未知表: {table}")
                continue
            
            try:
                verify_method = getattr(verifier, verifier_map[table])
                result = await verify_method()
                results[table] = result
                print_result(result)
            except Exception as e:
                logger.error(f"验证 {table} 失败: {e}")
                import traceback
                traceback.print_exc()
                results[table] = {'table': table, 'error': str(e)}
    
    print("\n" + "="*60)
    print("汇总")
    print("="*60)
    
    total_coverage = sum(r.get('coverage', 0) for r in results.values()) / len(results) if results else 0
    complete_tables = sum(1 for r in results.values() if r.get('coverage', 0) >= 0.98)
    
    for table, result in results.items():
        coverage = result.get('coverage', 0) * 100
        mark = "✓" if coverage >= 98 else ("⚠" if coverage >= 50 else "✗")
        print(f"  {mark} {table}: {coverage:.1f}%")
    
    print(f"\n总体覆盖度: {total_coverage:.1f}%")
    print(f"完整表格: {complete_tables}/{len(results)}")


def main():
    parser = argparse.ArgumentParser(
        description='数据完整性验证脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python sync_verify.py
    python sync_verify.py --tables daily
    python sync_verify.py --tables daily adj_factor
        """
    )
    
    parser.add_argument(
        '--tables',
        nargs='+',
        choices=['stock_daily', 'stock_adj_factor', 'index_daily', 
                 'stock_daily_basic', 'stock_factor_pro', 'all'],
        default=['all'],
        help='要验证的表 (默认全部)'
    )
    
    args = parser.parse_args()
    
    tables = None if 'all' in args.tables else args.tables
    
    try:
        asyncio.run(verify_tables(tables))
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"验证失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
