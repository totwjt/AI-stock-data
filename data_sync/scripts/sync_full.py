#!/usr/bin/env python3
"""
全量同步脚本 - 补齐近三年历史数据

使用方法:
    python sync_full.py                    # 同步全部5张表
    python sync_full.py --tables daily     # 仅同步日线数据
    python sync_full.py --tables daily adj_factor  # 同步指定表

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
from datetime import datetime
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 同步表配置
SYNC_TABLES = {
    'stock_daily': {
        'class': DailySync,
        'method': 'sync_full',
        'description': '股票日线行情',
    },
    'stock_adj_factor': {
        'class': AdjFactorSync,
        'method': 'sync_full',
        'description': '复权因子',
    },
    'index_daily': {
        'class': IndexDailySync,
        'method': 'sync_full',
        'description': '指数日线行情',
    },
    'stock_daily_basic': {
        'class': DailyBasicSync,
        'method': 'sync_full',
        'description': '每日基本面指标',
    },
    'stock_factor_pro': {
        'class': StkFactorProSync,
        'method': 'sync_full',
        'description': '技术面因子',
    },
}


async def sync_stock_basic(db):
    """同步股票基础信息和交易日历（前置条件）"""
    logger.info("=" * 60)
    logger.info("同步股票基础信息...")
    
    try:
        sync = StockBasicSync(db)
        await sync.sync_full()
        logger.info("股票基础信息同步完成 ✓")
    except Exception as e:
        logger.error(f"股票基础信息同步失败: {e}")
        raise


async def sync_trade_calendar(db):
    """同步交易日历（前置条件）"""
    logger.info("=" * 60)
    logger.info("同步交易日历...")
    
    try:
        sync = TradeCalendarSync(db)
        await sync.sync_full()
        logger.info("交易日历同步完成 ✓")
    except Exception as e:
        logger.error(f"交易日历同步失败: {e}")
        raise


async def sync_table(db, table_name: str):
    """同步单个表"""
    if table_name not in SYNC_TABLES:
        logger.warning(f"未知表名: {table_name}")
        return 0
    
    config = SYNC_TABLES[table_name]
    sync_class = config['class']
    sync_method = config['method']
    
    logger.info("=" * 60)
    logger.info(f"同步表: {table_name} ({config['description']})")
    
    start_time = datetime.now()
    
    try:
        sync = sync_class(db)
        sync_method_func = getattr(sync, sync_method)
        count = await sync_method_func()
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"{table_name} 同步完成: +{count} 条, 耗时 {duration:.1f}秒 ✓")
        return count
        
    except Exception as e:
        logger.error(f"{table_name} 同步失败: {e}")
        raise


async def run_full_sync(tables: list = None, sync_order: list = None):
    """
    执行全量同步
    
    Args:
        tables: 要同步的表列表，None表示全部
        sync_order: 同步顺序
    """
    await init_db()
    
    # 默认同步顺序（基础表优先）
    default_order = [
        'stock_basic',
        'trade_cal',
        'stock_adj_factor',
        'stock_daily',
        'stock_daily_basic',
        'index_daily',
        'stock_factor_pro',
    ]
    
    if sync_order is None:
        sync_order = default_order
    
    # 过滤要同步的表
    if tables is None:
        tables_to_sync = sync_order
    else:
        tables_to_sync = [t for t in sync_order if t in tables]
    
    logger.info("=" * 60)
    logger.info("开始全量同步")
    logger.info(f"同步表: {tables_to_sync}")
    logger.info(f"时间范围: 近3年")
    logger.info("=" * 60)
    
    total_start = datetime.now()
    total_counts = {}
    
    async with async_session() as db:
        for table_name in tables_to_sync:
            try:
                if table_name in ['stock_basic', 'trade_cal']:
                    # 基础表单独处理
                    if table_name == 'stock_basic':
                        await sync_stock_basic(db)
                    else:
                        await sync_trade_calendar(db)
                else:
                    count = await sync_table(db, table_name)
                    total_counts[table_name] = count
                    
            except Exception as e:
                logger.error(f"表 {table_name} 同步出错: {e}")
                # 继续执行其他表
                continue
    
    total_duration = (datetime.now() - total_start).total_seconds()
    
    logger.info("=" * 60)
    logger.info("全量同步完成!")
    logger.info(f"总耗时: {total_duration:.1f} 秒")
    logger.info("各表同步结果:")
    for table, count in total_counts.items():
        logger.info(f"  {table}: +{count} 条")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='全量同步脚本 - 补齐近三年历史数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python sync_full.py
    python sync_full.py --tables daily
    python sync_full.py --tables daily adj_factor
        """
    )
    
    parser.add_argument(
        '--tables',
        nargs='+',
        choices=list(SYNC_TABLES.keys()) + ['all'],
        default=['all'],
        help='要同步的表 (默认全部)'
    )
    
    args = parser.parse_args()
    
    # 解析表列表
    if 'all' in args.tables:
        tables = None
    else:
        tables = args.tables
    
    try:
        asyncio.run(run_full_sync(tables))
    except KeyboardInterrupt:
        logger.info("用户中断同步")
        sys.exit(1)
    except Exception as e:
        logger.error(f"同步失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
