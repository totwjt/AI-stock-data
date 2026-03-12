"""
数据同步测试脚本

用于测试各个同步功能是否正常工作
"""

import asyncio
import logging
from datetime import datetime

from data_sync.database import async_session, init_db
from data_sync.sync import (
    StockBasicSync,
    TradeCalendarSync,
    DailySync,
    AdjFactorSync,
    DailyBasicSync,
    IndexDailySync,
)


async def test_stock_basic():
    """测试股票基础信息同步"""
    print("测试股票基础信息同步...")
    await init_db()
    async with async_session() as db:
        sync = StockBasicSync(db)
        try:
            df = sync.fetch_data(list_status="L", limit=10)
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条股票基础数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def test_trade_calendar():
    """测试交易日历同步"""
    print("测试交易日历同步...")
    await init_db()
    async with async_session() as db:
        sync = TradeCalendarSync(db)
        try:
            df = sync.fetch_data(exchange="SSE", start_date="20250101", end_date="20250131")
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条交易日历数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def test_daily():
    """测试日线行情同步"""
    print("测试日线行情同步...")
    await init_db()
    async with async_session() as db:
        sync = DailySync(db)
        try:
            df = sync.fetch_data(ts_code="000001.SZ", start_date="20250101", end_date="20250110")
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条日线行情数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def test_adj_factor():
    """测试复权因子同步"""
    print("测试复权因子同步...")
    await init_db()
    async with async_session() as db:
        sync = AdjFactorSync(db)
        try:
            df = sync.fetch_data(ts_code="000001.SZ", start_date="20250101", end_date="20250110")
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条复权因子数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def test_daily_basic():
    """测试每日指标同步"""
    print("测试每日指标同步...")
    await init_db()
    async with async_session() as db:
        sync = DailyBasicSync(db)
        try:
            df = sync.fetch_data(ts_code="000001.SZ", start_date="20250101", end_date="20250110")
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条每日指标数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def test_index_daily():
    """测试指数行情同步"""
    print("测试指数行情同步...")
    await init_db()
    async with async_session() as db:
        sync = IndexDailySync(db)
        try:
            df = sync.fetch_data(ts_code="000001.SH", start_date="20250101", end_date="20250110")
            if df is not None and not df.empty:
                data_list = sync.transform_data(df)
                print(f"✓ 获取到 {len(data_list)} 条指数行情数据")
                return True
            else:
                print("✗ 未获取到数据")
                return False
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            return False


async def main():
    """运行所有测试"""
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("数据同步模块测试")
    print("=" * 50)
    
    tests = [
        test_stock_basic,
        test_trade_calendar,
        test_daily,
        test_adj_factor,
        test_daily_basic,
        test_index_daily,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    print("=" * 50)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 50)
    
    if all(results):
        print("✓ 所有测试通过")
    else:
        print("✗ 部分测试失败")


if __name__ == "__main__":
    asyncio.run(main())