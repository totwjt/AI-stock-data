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
    StkFactorProSync,
)
from .sync_manager import sync_manager, SyncStatus
from .table_descriptions import (
    get_table_description,
    get_all_table_descriptions,
    TableDescription,
    FieldDescription,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncRequest(BaseModel):
    """同步请求模型"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    sync_type: Optional[str] = None  # "full" 或 "incremental"


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


class FieldResponse(BaseModel):
    """字段响应模型"""
    name: str
    type: str
    description: str
    is_primary_key: bool


class TableDescriptionResponse(BaseModel):
    """表描述响应模型"""
    name: str
    description: str
    fields: List[FieldResponse]
    sync_type: str


# 表名到同步类的映射
TABLE_SYNC_MAP = {
    "stock_basic": StockBasicSync,
    "trade_calendar": TradeCalendarSync,
    "daily": DailySync,
    "adj_factor": AdjFactorSync,
    "daily_basic": DailyBasicSync,
    "index_daily": IndexDailySync,
    "stk_factor_pro": StkFactorProSync,
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
    
    sync_class = TABLE_SYNC_MAP[table_name]
    
    if table_name in ["stock_basic", "trade_calendar"]:
        if request.sync_type == "incremental":
            sync_func_name = "sync_incremental"
        else:
            sync_func_name = "sync_full"
        func_kwargs = {}
    elif table_name == "index_daily":
        sync_func_name = "sync_incremental"
        func_kwargs = {
            "start_date": request.start_date,
            "end_date": request.end_date,
            "ts_code": None,
        }
    elif table_name == "stk_factor_pro":
        sync_func_name = "sync_history_by_year"
        func_kwargs = {
            "start_year": None,
            "end_year": None,
        }
    else:
        sync_func_name = "sync_incremental"
        func_kwargs = {
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
    
    async def sync_task_wrapper():
        async with async_session() as db:
            sync_instance = sync_class(db)
            sync_func = getattr(sync_instance, sync_func_name)
            return await sync_func(**func_kwargs)
    
    task_id = await sync_manager.submit_sync(
        table_name=table_name,
        sync_func=sync_task_wrapper,
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
        "incremental_sync": ["daily", "adj_factor", "daily_basic", "index_daily", "stk_factor_pro"],
    }


@router.get("/descriptions", response_model=List[TableDescriptionResponse])
async def get_table_descriptions():
    """
    获取所有表的描述信息
    """
    descriptions = get_all_table_descriptions()
    
    return [
        TableDescriptionResponse(
            name=desc.name,
            description=desc.description,
            fields=[
                FieldResponse(
                    name=field.name,
                    type=field.type,
                    description=field.description,
                    is_primary_key=field.is_primary_key,
                )
                for field in desc.fields
            ],
            sync_type=desc.sync_type,
        )
        for desc in descriptions
    ]


@router.get("/descriptions/{table_name}", response_model=TableDescriptionResponse)
async def get_table_description_api(table_name: str):
    """
    获取指定表的描述信息
    
    - **table_name**: 表名
    """
    description = get_table_description(table_name)
    
    if not description:
        raise HTTPException(
            status_code=404,
            detail=f"表 {table_name} 的描述信息不存在"
        )
    
    return TableDescriptionResponse(
        name=description.name,
        description=description.description,
        fields=[
            FieldResponse(
                name=field.name,
                type=field.type,
                description=field.description,
                is_primary_key=field.is_primary_key,
            )
            for field in description.fields
        ],
        sync_type=description.sync_type,
    )