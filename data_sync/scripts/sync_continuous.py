#!/usr/bin/env python3
"""
持续同步脚本 - 定时增量同步最新数据

使用方法:
    python sync_continuous.py                        # 使用默认配置运行
    python sync_continuous.py --interval 60          # 60秒间隔
    python sync_continuous.py --once                 # 仅运行一次
    python sync_continuous.py --tables daily adj_factor  # 仅同步指定表

功能:
    - 持续运行，定时同步最新数据
    - 支持配置同步间隔
    - 支持仅运行一次模式
    - 自动跳过已同步的数据
    - 记录同步状态和日志
"""

import asyncio
import argparse
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_sync.database import async_session, init_db
from data_sync.sync import (
    DailySync,
    AdjFactorSync,
    DailyBasicSync,
    IndexDailySync,
    StkFactorProSync,
    StockBasicSync,
    TradeCalendarSync,
)
from data_sync.config import settings

# 配置日志
log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            log_dir / 'sync_continuous.log',
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)


class ContinuousSyncRunner:
    """持续同步运行器"""
    
    def __init__(self, interval: int = 3600, tables: list = None):
        """
        Args:
            interval: 同步间隔（秒），默认3600（1小时）
            tables: 要同步的表列表，None表示全部
        """
        self.interval = interval
        self.tables = tables or [
            'stock_daily',
            'stock_adj_factor',
            'stock_daily_basic',
            'index_daily',
            'stock_factor_pro',
        ]
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # 同步顺序（基础表优先，但只在需要时同步）
        self.sync_order = [
            'stock_basic',
            'trade_cal',
            'stock_adj_factor',
            'stock_daily',
            'stock_daily_basic',
            'index_daily',
            'stock_factor_pro',
        ]
        
        # 基础表已同步标志（避免每次都检查）
        self._basic_synced = False
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备停止...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def stop(self):
        """停止同步"""
        logger.info("正在停止持续同步...")
        self.running = False
        self._shutdown_event.set()
    
    async def sync_stock_basic(self, db):
        """同步股票基础信息"""
        if self._basic_synced:
            return 0
        
        logger.info("同步股票基础信息...")
        try:
            sync = StockBasicSync(db)
            await sync.sync_full()
            self._basic_synced = True
            logger.info("股票基础信息同步完成 ✓")
            return 1
        except Exception as e:
            logger.warning(f"股票基础信息同步失败: {e}")
            return 0
    
    async def sync_trade_calendar(self, db):
        """同步交易日历"""
        logger.info("同步交易日历...")
        try:
            sync = TradeCalendarSync(db)
            await sync.sync_full()
            logger.info("交易日历同步完成 ✓")
            return 1
        except Exception as e:
            logger.warning(f"交易日历同步失败: {e}")
            return 0
    
    async def sync_table(self, db, table_name: str):
        """同步单个表（增量模式）"""
        sync_classes = {
            'stock_daily': DailySync,
            'stock_adj_factor': AdjFactorSync,
            'stock_daily_basic': DailyBasicSync,
            'index_daily': IndexDailySync,
            'stock_factor_pro': StkFactorProSync,
        }
        
        if table_name not in sync_classes:
            logger.warning(f"未知表名: {table_name}")
            return 0
        
        sync_class = sync_classes[table_name]
        
        logger.info(f"增量同步: {table_name}")
        
        try:
            sync = sync_class(db)
            # 使用增量同步方法
            count = await sync.sync_incremental()
            logger.info(f"{table_name} 增量同步完成: +{count} 条 ✓")
            return count
        except Exception as e:
            logger.warning(f"{table_name} 增量同步失败: {e}")
            return 0
    
    async def sync_all_tables(self, db):
        """同步所有配置的表"""
        logger.info("=" * 60)
        logger.info(f"开始增量同步，间隔 {self.interval} 秒")
        logger.info(f"同步表: {self.tables}")
        logger.info("=" * 60)
        
        total_counts = {}
        
        # 先确保基础表已同步
        if 'stock_basic' in self.tables:
            await self.sync_stock_basic(db)
        
        if 'trade_cal' in self.tables:
            await self.sync_trade_calendar(db)
        
        # 同步数据表
        for table_name in self.tables:
            if table_name in ['stock_basic', 'trade_cal']:
                continue
            
            try:
                count = await self.sync_table(db, table_name)
                total_counts[table_name] = count
            except Exception as e:
                logger.error(f"表 {table_name} 同步出错: {e}")
                continue
        
        return total_counts
    
    async def run_once(self):
        """执行一次同步"""
        await init_db()
        
        async with async_session() as db:
            return await self.sync_all_tables(db)
    
    async def run_continuous(self):
        """持续运行同步"""
        self._setup_signal_handlers()
        self.running = True
        
        await init_db()
        
        logger.info("=" * 60)
        logger.info("持续同步已启动")
        logger.info(f"同步间隔: {self.interval} 秒")
        logger.info(f"同步表: {self.tables}")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 60)
        
        while self.running:
            try:
                start_time = datetime.now()
                
                async with async_session() as db:
                    counts = await self.sync_all_tables(db)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                logger.info("=" * 60)
                logger.info(f"本轮同步完成，耗时 {duration:.1f} 秒")
                logger.info(f"各表增量: {counts}")
                
                # 计算下次同步时间
                next_sync = start_time + timedelta(seconds=self.interval)
                logger.info(f"下次同步: {next_sync.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)
                
                # 等待间隔或直到收到停止信号
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.interval
                    )
                    # 如果事件被设置，说明收到了停止信号
                    if self._shutdown_event.is_set():
                        break
                except asyncio.TimeoutError:
                    # 超时，继续下一次同步
                    continue
                    
            except Exception as e:
                logger.error(f"同步循环出错: {e}")
                # 出错后等待一段时间再重试
                await asyncio.sleep(60)
        
        logger.info("持续同步已停止")


async def main():
    parser = argparse.ArgumentParser(
        description='持续同步脚本 - 定时增量同步最新数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python sync_continuous.py                    # 默认运行（每小时同步）
    python sync_continuous.py --interval 1800     # 30分钟间隔
    python sync_continuous.py --once              # 仅运行一次
    python sync_continuous.py --tables daily       # 仅同步日线
        """
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='同步间隔秒数 (默认3600，即1小时)'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='仅运行一次，不持续'
    )
    
    parser.add_argument(
        '--tables',
        nargs='+',
        default=None,
        choices=['stock_daily', 'stock_adj_factor', 'stock_daily_basic', 
                 'index_daily', 'stock_factor_pro', 'stock_basic', 'trade_cal'],
        help='要同步的表 (默认全部)'
    )
    
    args = parser.parse_args()
    
    runner = ContinuousSyncRunner(
        interval=args.interval,
        tables=args.tables
    )
    
    try:
        if args.once:
            await runner.run_once()
        else:
            await runner.run_continuous()
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"持续同步失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
