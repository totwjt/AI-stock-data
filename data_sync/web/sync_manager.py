"""
同步任务管理器

负责管理同步任务的状态、并发控制和任务队列
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """同步任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SyncTask:
    """同步任务数据类"""
    task_id: str
    table_name: str
    status: SyncStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    records_count: int = 0
    error_message: Optional[str] = None
    progress: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "table_name": self.table_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "records_count": self.records_count,
            "error_message": self.error_message,
            "progress": self.progress,
        }


class SyncManager:
    """同步任务管理器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.active_tasks: Dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self.task_info: Dict[str, SyncTask] = {}  # task_id -> SyncTask
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        logger.info(f"SyncManager initialized with max_concurrent={max_concurrent}")
    
    async def submit_sync(
        self,
        table_name: str,
        sync_func,
        *args,
        **kwargs
    ) -> str:
        """提交同步任务"""
        task_id = str(uuid.uuid4())
        
        task_info = SyncTask(
            task_id=task_id,
            table_name=table_name,
            status=SyncStatus.PENDING,
            start_time=datetime.now(),
        )
        
        async with self._lock:
            self.task_info[task_id] = task_info
        
        task = asyncio.create_task(
            self._run_sync_task(task_id, sync_func, *args, **kwargs)
        )
        
        async with self._lock:
            self.active_tasks[task_id] = task
        
        logger.info(f"Submitted sync task {task_id} for table {table_name}")
        return task_id
    
    async def _run_sync_task(
        self,
        task_id: str,
        sync_func,
        *args,
        **kwargs
    ):
        """执行同步任务"""
        async with self.semaphore:
            try:
                async with self._lock:
                    if task_id in self.task_info:
                        self.task_info[task_id].status = SyncStatus.RUNNING
                
                logger.info(f"Starting sync task {task_id}")
                
                result = await sync_func(*args, **kwargs)
                
                async with self._lock:
                    if task_id in self.task_info:
                        task = self.task_info[task_id]
                        task.status = SyncStatus.COMPLETED
                        task.end_time = datetime.now()
                        task.records_count = result if isinstance(result, int) else 0
                        task.progress = 100.0
                
                logger.info(f"Sync task {task_id} completed successfully")
                
            except asyncio.CancelledError:
                async with self._lock:
                    if task_id in self.task_info:
                        task = self.task_info[task_id]
                        task.status = SyncStatus.STOPPED
                        task.end_time = datetime.now()
                logger.info(f"Sync task {task_id} was cancelled")
                raise
                
            except Exception as e:
                async with self._lock:
                    if task_id in self.task_info:
                        task = self.task_info[task_id]
                        task.status = SyncStatus.FAILED
                        task.end_time = datetime.now()
                        task.error_message = str(e)
                logger.error(f"Sync task {task_id} failed: {str(e)}")
                raise
                
            finally:
                async with self._lock:
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
    
    async def stop_task(self, task_id: str) -> bool:
        """停止指定任务"""
        async with self._lock:
            if task_id not in self.active_tasks:
                return False
            
            task = self.active_tasks[task_id]
            task.cancel()
            
            # 等待任务真正停止
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Task {task_id} did not stop within timeout")
            except asyncio.CancelledError:
                pass
            
            return True
    
    async def get_task_status(self, task_id: str) -> Optional[SyncTask]:
        """获取任务状态"""
        async with self._lock:
            return self.task_info.get(task_id)
    
    async def get_all_tasks(self) -> Dict[str, SyncTask]:
        """获取所有任务状态"""
        async with self._lock:
            return dict(self.task_info)
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务（24小时前的完成/失败任务）"""
        now = datetime.now()
        async with self._lock:
            to_remove = []
            for task_id, task in self.task_info.items():
                if task.end_time:
                    age = (now - task.end_time).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.task_info[task_id]
                logger.info(f"Cleaned up old task {task_id}")


# 全局同步管理器实例
sync_manager = SyncManager(max_concurrent=3)