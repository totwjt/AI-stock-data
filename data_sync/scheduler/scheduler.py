import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from data_sync.database import async_session, init_db
from data_sync.sync import (
    StockBasicSync,
    TradeCalendarSync,
    DailySync,
    AdjFactorSync,
    DailyBasicSync,
    IndexDailySync,
)


class DataSyncScheduler:
    """数据同步调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger("scheduler")
        
    async def sync_daily_task(self):
        """同步日线行情任务"""
        self.logger.info("开始执行日线行情同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = DailySync(db)
                start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
                end_date = datetime.now().strftime("%Y%m%d")
                await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
            self.logger.info("日线行情同步任务完成")
        except Exception as e:
            self.logger.error(f"日线行情同步任务失败: {str(e)}")
    
    async def sync_adj_factor_task(self):
        """同步复权因子任务"""
        self.logger.info("开始执行复权因子同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = AdjFactorSync(db)
                start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
                end_date = datetime.now().strftime("%Y%m%d")
                await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
            self.logger.info("复权因子同步任务完成")
        except Exception as e:
            self.logger.error(f"复权因子同步任务失败: {str(e)}")
    
    async def sync_daily_basic_task(self):
        """同步每日指标任务"""
        self.logger.info("开始执行每日指标同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = DailyBasicSync(db)
                start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
                end_date = datetime.now().strftime("%Y%m%d")
                await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
            self.logger.info("每日指标同步任务完成")
        except Exception as e:
            self.logger.error(f"每日指标同步任务失败: {str(e)}")
    
    async def sync_index_daily_task(self):
        """同步指数行情任务"""
        self.logger.info("开始执行指数行情同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = IndexDailySync(db)
                start_date = (datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
                end_date = datetime.now().strftime("%Y%m%d")
                await sync.sync_with_retry(sync.sync_incremental, start_date, end_date)
            self.logger.info("指数行情同步任务完成")
        except Exception as e:
            self.logger.error(f"指数行情同步任务失败: {str(e)}")
    
    async def sync_stock_basic_full_task(self):
        """同步股票基础信息全量任务（每周一次）"""
        self.logger.info("开始执行股票基础信息全量同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = StockBasicSync(db)
                await sync.sync_with_retry(sync.sync_full)
            self.logger.info("股票基础信息全量同步任务完成")
        except Exception as e:
            self.logger.error(f"股票基础信息全量同步任务失败: {str(e)}")
    
    async def sync_trade_calendar_full_task(self):
        """同步交易日历全量任务（每周一次）"""
        self.logger.info("开始执行交易日历全量同步任务")
        try:
            await init_db()
            async with async_session() as db:
                sync = TradeCalendarSync(db)
                await sync.sync_with_retry(sync.sync_full)
            self.logger.info("交易日历全量同步任务完成")
        except Exception as e:
            self.logger.error(f"交易日历全量同步任务失败: {str(e)}")
    
    def start(self):
        """启动调度器"""
        # 每日增量同步（行情类数据）
        self.scheduler.add_job(
            self.sync_daily_task,
            trigger=CronTrigger(hour=16, minute=30),
            id="sync_daily",
            name="同步日线行情"
        )
        
        self.scheduler.add_job(
            self.sync_adj_factor_task,
            trigger=CronTrigger(hour=16, minute=35),
            id="sync_adj_factor",
            name="同步复权因子"
        )
        
        self.scheduler.add_job(
            self.sync_daily_basic_task,
            trigger=CronTrigger(hour=16, minute=40),
            id="sync_daily_basic",
            name="同步每日指标"
        )
        
        self.scheduler.add_job(
            self.sync_index_daily_task,
            trigger=CronTrigger(hour=16, minute=45),
            id="sync_index_daily",
            name="同步指数行情"
        )
        
        # 每周全量同步（基础表）
        self.scheduler.add_job(
            self.sync_stock_basic_full_task,
            trigger=CronTrigger(day_of_week=0, hour=2, minute=0),
            id="sync_stock_basic_full",
            name="全量同步股票基础信息"
        )
        
        self.scheduler.add_job(
            self.sync_trade_calendar_full_task,
            trigger=CronTrigger(day_of_week=0, hour=2, minute=30),
            id="sync_trade_calendar_full",
            name="全量同步交易日历"
        )
        
        self.scheduler.start()
        self.logger.info("数据同步调度器已启动")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    scheduler = DataSyncScheduler()
    scheduler.start()
    
    # 保持程序运行
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        scheduler.scheduler.shutdown()
        print("调度器已停止")


if __name__ == "__main__":
    main()