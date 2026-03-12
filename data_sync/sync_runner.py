"""
数据同步入口脚本

使用方法:
    python -m data_sync.sync_runner [sync_type] [options]

sync_type:
    full            全量同步
    incremental     增量同步
    stock_basic     同步股票基础信息
    trade_cal       同步交易日历
    daily           同步日线行情
    adj_factor      同步复权因子
    daily_basic     同步每日指标
    index_daily     同步指数行情
    all             同步所有数据

options:
    --start_date    开始日期 (YYYYMMDD)
    --end_date      结束日期 (YYYYMMDD)
"""

import asyncio
import argparse
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


async def run_sync(sync_type: str, start_date: str = None, end_date: str = None):
    """运行同步任务"""
    await init_db()
    
    async with async_session() as db:
        if sync_type == "stock_basic":
            sync = StockBasicSync(db)
            await sync.sync_with_retry(sync.sync_full)
        elif sync_type == "trade_cal":
            sync = TradeCalendarSync(db)
            await sync.sync_with_retry(sync.sync_full)
        elif sync_type == "daily":
            sync = DailySync(db)
            await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
        elif sync_type == "adj_factor":
            sync = AdjFactorSync(db)
            await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
        elif sync_type == "daily_basic":
            sync = DailyBasicSync(db)
            await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
        elif sync_type == "index_daily":
            sync = IndexDailySync(db)
            await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
        elif sync_type == "all":
            await run_sync("stock_basic", start_date, end_date)
            await run_sync("trade_cal", start_date, end_date)
            await run_sync("daily", start_date, end_date)
            await run_sync("adj_factor", start_date, end_date)
            await run_sync("daily_basic", start_date, end_date)
            await run_sync("index_daily", start_date, end_date)
        else:
            raise ValueError(f"未知的同步类型: {sync_type}")


def main():
    parser = argparse.ArgumentParser(description="数据同步工具")
    parser.add_argument(
        "sync_type",
        choices=["full", "incremental", "stock_basic", "trade_cal", "daily", 
                 "adj_factor", "daily_basic", "index_daily", "all"],
        help="同步类型"
    )
    parser.add_argument("--start_date", help="开始日期 YYYYMMDD")
    parser.add_argument("--end_date", help="结束日期 YYYYMMDD")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    sync_type = args.sync_type
    if sync_type == "full":
        sync_type = "stock_basic"
    elif sync_type == "incremental":
        sync_type = "daily"
    
    try:
        asyncio.run(run_sync(sync_type, args.start_date, args.end_date))
        print(f"同步完成: {sync_type}")
    except Exception as e:
        print(f"同步失败: {str(e)}")
        raise


if __name__ == "__main__":
    main()