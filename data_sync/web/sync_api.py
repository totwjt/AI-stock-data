"""
同步API接口

提供Web接口用于触发同步任务和查询同步状态
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
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
from data_sync.sync.sync_state import sync_state_manager
from .table_descriptions import (
    get_table_description,
    get_all_table_descriptions,
    TableDescription,
    FieldDescription,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])


class VerifyRequest(BaseModel):
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class VerifyResponse(BaseModel):
    task_id: str
    message: str


class VerifyResult(BaseModel):
    year: int
    verified: bool
    expected_dates: int
    actual_dates: int
    missing_dates: List[str]


class SyncRequest(BaseModel):
    """同步请求模型"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    sync_type: Optional[str] = None


class ScheduleRequest(BaseModel):
    """定时同步请求模型"""
    tables: Optional[List[str]] = None


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
        if request.sync_type == "incremental":
            sync_func_name = "sync_incremental"
            func_kwargs = {}
        else:
            sync_func_name = "sync_all_years"
            func_kwargs = {
                "start_year": None,
                "end_year": None,
            }
    elif table_name == "stk_factor_pro":
        sync_func_name = "sync"
        func_kwargs = {}
    elif table_name == "daily":
        sync_func_name = "sync"
        func_kwargs = {}
    elif table_name in ["daily_basic", "index_daily"]:
        if request.sync_type == "incremental":
            sync_func_name = "sync_incremental"
            func_kwargs = {}
        else:
            sync_func_name = "sync_all_years"
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


@router.post("/verify/{table_name}", response_model=VerifyResponse)
async def start_verify(table_name: str, request: VerifyRequest = VerifyRequest()):
    """开始验证指定表的数据完整性"""
    if table_name not in TABLE_SYNC_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"未知的表名: {table_name}. 支持的表: {list(TABLE_SYNC_MAP.keys())}"
        )
    
    await init_db()
    
    sync_class = TABLE_SYNC_MAP[table_name]
    
    async def verify_task_wrapper():
        async with async_session() as db:
            sync_instance = sync_class(db)
            
            if hasattr(sync_instance, 'verify_all_years'):
                return await sync_instance.verify_all_years(
                    start_year=request.start_year,
                    end_year=request.end_year
                )
            elif hasattr(sync_instance, 'verify_year'):
                return await sync_instance.verify_year(
                    request.start_year or datetime.now().year
                )
            else:
                return [{"error": f"{table_name} 不支持验证功能"}]
    
    task_id = await sync_manager.submit_sync(
        table_name=f"verify_{table_name}",
        sync_func=verify_task_wrapper,
    )
    
    return VerifyResponse(
        task_id=task_id,
        message=f"验证任务已提交: {table_name}"
    )


@router.get("/verify/status/{table_name}")
async def get_verify_status(table_name: str):
    """获取指定表的验证状态"""
    table_state = sync_state_manager.get_table_state(table_name)
    
    results = []
    for year_str, state in table_state.items():
        results.append({
            "year": int(year_str),
            "verified": state.get("verified", False),
            "verified_at": state.get("verified_at"),
            "trade_dates": state.get("trade_dates", 0)
        })
    
    return {
        "table_name": table_name,
        "verified_years": [r["year"] for r in results if r["verified"]],
        "incomplete_years": [r["year"] for r in results if not r["verified"]],
        "details": sorted(results, key=lambda x: x["year"], reverse=True)
    }


@router.get("/state/{table_name}")
async def get_sync_state(table_name: str):
    """获取表的同步状态"""
    table_state = sync_state_manager.get_table_state(table_name)
    
    return {
        "table_name": table_name,
        "state": table_state
    }


@router.delete("/state/{table_name}/{year}")
async def reset_sync_state(table_name: str, year: int):
    """重置指定年份的同步状态"""
    sync_state_manager.reset_year(table_name, year)
    return {"message": f"已重置 {table_name}.{year} 的同步状态"}


@router.post("/schedule", response_model=SyncResponse)
async def run_schedule_sync():
    """定时同步核心逻辑 - 被定时器和API调用"""
    await init_db()
    
    async with async_session() as db:
        results = []
        logger.info("=== 定时同步开始 ===")
        
        # 1. stock_basic 全量替换
        try:
            stock_basic_sync = StockBasicSync(db)
            basic_count = await stock_basic_sync.sync_full()
            results.append(f"stock_basic: +{basic_count}")
            logger.info(f"stock_basic: +{basic_count}")
        except Exception as e:
            results.append(f"stock_basic: 失败 - {e}")
            logger.error(f"stock_basic: 失败 - {e}")
        
        # 2. stock_daily 同步近3天
        try:
            daily_sync = DailySync(db)
            today = datetime.now()
            start_date = (today - timedelta(days=2)).strftime("%Y%m%d")
            end_date = today.strftime("%Y%m%d")
            daily_count = await daily_sync.sync_incremental(start_date=start_date, end_date=end_date)
            results.append(f"stock_daily: +{daily_count}")
            logger.info(f"stock_daily: +{daily_count}")
        except Exception as e:
            results.append(f"stock_daily: 失败 - {e}")
            logger.error(f"stock_daily: 失败 - {e}")
        
        # 3. stk_factor_pro 同步近3天
        try:
            stk_sync = StkFactorProSync(db)
            stk_count = await stk_sync.sync(start_year=today.year, end_year=today.year)
            results.append(f"stk_factor_pro: +{stk_count}")
            logger.info(f"stk_factor_pro: +{stk_count}")
        except Exception as e:
            results.append(f"stk_factor_pro: 失败 - {e}")
            logger.error(f"stk_factor_pro: 失败 - {e}")
        
        logger.info("=== 定时同步完成 ===")
        return "\n".join(results)


@router.post("/schedule", response_model=SyncResponse)
async def start_schedule_sync():
    """手动触发定时同步"""
    await init_db()
    
    async def schedule_sync_task():
        return await run_schedule_sync()
    
    task_id = await sync_manager.submit_sync(
        table_name="schedule",
        sync_func=schedule_sync_task,
    )
    
    return SyncResponse(
        task_id=task_id,
        message="定时同步已启动: stock_basic(全量), stock_daily(近3天), stk_factor_pro(近3天)"
    )


@router.post("/schedule/toggle")
async def toggle_schedule(enabled: bool):
    """开关定时任务"""
    from data_sync.web.app import scheduler
    
    if enabled:
        if not scheduler.running:
            scheduler.start()
        return {"message": "定时同步已启用", "enabled": True}
    else:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        return {"message": "定时同步已禁用", "enabled": False}