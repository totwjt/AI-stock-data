import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import tuple_

from data_sync.config import settings
from data_sync.tushare_client import tushare_client


class BaseSync(ABC):
    """同步任务基类"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = self._setup_logger()
        self.batch_size = settings.batch_size
        self.retry_times = settings.retry_times
        self.retry_delay = settings.retry_delay
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger(f"sync.{self.__class__.__name__}")
        logger.setLevel(settings.log_level)
        
        if not logger.handlers:
            handler = logging.FileHandler(
                f"{settings.log_dir}/data_sync.log",
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def get_table_model(self):
        """获取数据库表模型"""
        pass
    
    @abstractmethod
    def fetch_data(self, **kwargs):
        """从 Tushare 获取数据"""
        pass
    
    @abstractmethod
    def transform_data(self, df):
        """数据转换"""
        pass
    
    async def upsert_data(self, data_list: list, auto_commit: bool = True):
        """UPSERT 数据到数据库
        
        Args:
            data_list: 数据列表
            auto_commit: 是否自动提交事务，默认为True
                        设置为False时，需要在外部手动提交事务
        """
        if not data_list:
            return 0
        
        model = self.get_table_model()
        table = model.__table__
        
        # 使用 ON CONFLICT DO UPDATE 进行 UPSERT
        primary_keys = [col.name for col in table.primary_key.columns]
        
        # 去重：确保同一主键只出现一次
        seen_keys = set()
        deduplicated_data = []
        for item in reversed(data_list):
            key = tuple(item.get(pk) for pk in primary_keys)
            if key not in seen_keys:
                seen_keys.add(key)
                deduplicated_data.append(item)
        
        # 保持原始顺序
        deduplicated_data = list(reversed(deduplicated_data))
        
        # PostgreSQL 参数限制：32767
        if deduplicated_data:
            field_count = len(deduplicated_data[0])
        else:
            field_count = len(table.columns)
        max_params = 32767
        max_batch_size = (max_params // field_count) - 10
        
        total_count = 0
        
        # 分批处理，避免超过 PostgreSQL 参数限制
        for i in range(0, len(deduplicated_data), max_batch_size):
            batch = deduplicated_data[i:i + max_batch_size]
            
            insert_stmt = pg_insert(table).values(batch)
            
            stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=primary_keys
            )
            
            result = await self.db.execute(stmt)
            total_count += result.rowcount if hasattr(result, 'rowcount') else len(batch)
        
        if auto_commit:
            await self.db.commit()
        
        return total_count
    
    async def sync_full(self, **kwargs):
        """全量同步"""
        start_time = datetime.now()
        self.logger.info(f"开始全量同步 {self.__class__.__name__}")
        
        try:
            df = self.fetch_data(**kwargs)
            if df is None or df.empty:
                self.logger.warning("未获取到数据")
                return 0
            
            data_list = self.transform_data(df)
            
            total = 0
            for i in range(0, len(data_list), self.batch_size):
                batch = data_list[i:i + self.batch_size]
                count = await self.upsert_data(batch)
                total += count
                self.logger.info(f"已写入 {total} 条数据")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"全量同步完成，共写入 {total} 条数据，耗时 {duration:.2f} 秒")
            return total
            
        except Exception as e:
            self.logger.error(f"全量同步失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def sync_incremental(self, start_date: str = None, end_date: str = None):
        """增量同步"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        start_time = datetime.now()
        self.logger.info(f"开始增量同步 {self.__class__.__name__}, 日期范围: {start_date} - {end_date}")
        
        try:
            df = self.fetch_data(start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                self.logger.warning("未获取到数据")
                return 0
            
            data_list = self.transform_data(df)
            
            total = 0
            for i in range(0, len(data_list), self.batch_size):
                batch = data_list[i:i + self.batch_size]
                count = await self.upsert_data(batch)
                total += count
                self.logger.info(f"已写入 {total} 条数据")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"增量同步完成，共写入 {total} 条数据，耗时 {duration:.2f} 秒")
            return total
            
        except Exception as e:
            self.logger.error(f"增量同步失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def sync_with_retry(self, sync_func, *args, **kwargs):
        """带重试机制的同步"""
        for attempt in range(self.retry_times):
            try:
                return await sync_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_times - 1:
                    raise
                self.logger.warning(
                    f"同步失败，第 {attempt + 1} 次重试: {str(e)}"
                )
                await asyncio.sleep(self.retry_delay)