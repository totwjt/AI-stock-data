"""
同步API接口

提供Web接口用于触发同步任务和查询同步状态
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging

from data_sync.database import async_session, init_db
from data_sync.sync import (
    StockBasicSync,
    TradeCalendarSync,
    DailySync,
    AdjFactorSync,
    DailyBasicSync,
    IndexDailySync,
)
from .sync_manager import sync_manager, SyncStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """同步请求模型"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SyncResponse(BaseModel):
    """同步响应模型"""
    task_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    table_name: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    records_count: int
    error_message: Optional[str] = None
    progress: float


# 表名到同步类的映射
TABLE_SYNC_MAP = {
    "stock_basic": StockBasicSync,
    "trade_calendar": TradeCalendarSync,
    "daily": DailySync,
    "adj_factor": AdjFactorSync,
    "daily_basic": DailyBasicSync,
    "index_daily": IndexDailySync,
}


@router.post("/{table_name}", response_model=SyncResponse)
async def start_sync(table_name: str, request: SyncRequest = SyncRequest()):
    """
    开始同步指定表
    
    - **table_name**: 表名 (stock_basic, trade_calendar, daily, adj_factor, daily_basic, index_daily)
    - **start_date**: 开始日期 (YYYYMMDD)，增量同步时可选
    - **end_date**: 结束日期 (YYYYMMDD)，增量同步时可选
    """
    if table_name not in TABLE_SYNC_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"未知的表名: {table_name}. 支持的表: {list(TABLE_SYNC_MAP.keys())}"
        )
    
    # 初始化数据库
    await init_db()
    
    # 创建数据库会话
    async with async_session() as db:
        sync_class = TABLE_SYNC_MAP[table_name]
        sync_instance = sync_class(db)
        
        # 判断同步类型
        if table_name in ["stock_basic", "trade_calendar"]:
            # 全量同步
            sync_func = sync_instance.sync_full
            args = ()
            kwargs = {}
        else:
            # 增量同步
            sync_func = sync_instance.sync_incremental
            args = ()
            kwargs = {
                "start_date": request.start_date,
                "end_date": request.end_date,
            }
        
        # 提交同步任务
        task_id = await sync_manager.submit_sync(
            table_name=table_name,
            sync_func=sync_func,
            *args,
            **kwargs
        )
        
        return SyncResponse(
            task_id=task_id,
            message=f"同步任务已提交: {table_name}"
        )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询同步任务状态
    
    - **task_id**: 任务ID
    """
    task = await sync_manager.get_task_status(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 不存在"
        )
    
    return TaskStatusResponse(
        task_id=task.task_id,
        table_name=task.table_name,
        status=task.status.value,
        start_time=task.start_time.isoformat(),
        end_time=task.end_time.isoformat() if task.end_time else None,
        records_count=task.records_count,
        error_message=task.error_message,
        progress=task.progress,
    )


@router.get("/status", response_model=List[TaskStatusResponse])
async def get_all_tasks_status():
    """
    查询所有同步任务状态
    """
    tasks = await sync_manager.get_all_tasks()
    
    return [
        TaskStatusResponse(
            task_id=task.task_id,
            table_name=task.table_name,
            status=task.status.value,
            start_time=task.start_time.isoformat(),
            end_time=task.end_time.isoformat() if task.end_time else None,
            records_count=task.records_count,
            error_message=task.error_message,
            progress=task.progress,
        )
        for task in tasks.values()
    ]


@router.post("/stop/{task_id}")
async def stop_task(task_id: str):
    """
    停止同步任务
    
    - **task_id**: 任务ID
    """
    stopped = await sync_manager.stop_task(task_id)
    
    if not stopped:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {task_id} 不存在或已结束"
        )
    
    return {"message": f"任务 {task_id} 已停止"}


@router.get("/tables")
async def get_syncable_tables():
    """
    获取可同步的表列表
    """
    return {
        "tables": list(TABLE_SYNC_MAP.keys()),
        "full_sync": ["stock_basic", "trade_calendar"],
        "incremental_sync": ["daily", "adj_factor", "daily_basic", "index_daily"],
    }