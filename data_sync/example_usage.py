"""
数据同步模块使用示例

演示如何使用数据同步模块同步数据到 PostgreSQL
"""

import asyncio
import logging
from datetime import datetime

from data_sync.database import async_session, init_db
from data_sync.sync import StockBasicSync, DailySync


async def example_sync_stock_basic():
    """示例：同步股票基础信息"""
    print("开始同步股票基础信息...")
    
    await init_db()
    async with async_session() as db:
        sync = StockBasicSync(db)
        
        count = await sync.sync_with_retry(sync.sync_full)
        print(f"同步完成，共 {count} 条数据")


async def example_sync_daily():
    """示例：同步日线行情"""
    print("开始同步日线行情...")
    
    await init_db()
    async with async_session() as db:
        sync = DailySync(db)
        
        start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        count = await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
        print(f"同步完成，共 {count} 条数据")


async def main():
    """运行示例"""
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("数据同步模块使用示例")
    print("=" * 50)
    
    await example_sync_stock_basic()
    print()
    
    await example_sync_daily()
    print()
    
    print("=" * 50)
    print("示例完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())