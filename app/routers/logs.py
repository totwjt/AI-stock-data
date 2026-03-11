from fastapi import APIRouter, Query, Response
from typing import Optional
from sqlalchemy import select, desc, func, delete
from app.database import async_session
from app.models.log import ApiLog

router = APIRouter(prefix="/logs", tags=["请求日志"])


@router.get("/list")
async def get_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    api_name: Optional[str] = Query(None, description="API名称筛选"),
    method: Optional[str] = Query(None, description="请求方法筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期")
):
    async with async_session() as session:
        query = select(ApiLog).order_by(desc(ApiLog.created_at))
        
        if api_name:
            query = query.where(ApiLog.api_name == api_name)
        if method:
            query = query.where(ApiLog.method == method)
        
        total = len((await session.execute(query)).scalars().all())
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        logs = result.scalars().all()
        
        return {
            "code": 0,
            "data": [{
                "id": log.id,
                "api_name": log.api_name,
                "method": log.method,
                "path": log.path,
                "params": log.params,
                "response_status": log.response_status,
                "response_time": log.response_time,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            } for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }


@router.get("/stats")
async def get_stats():
    async with async_session() as session:
        total_query = select(func.count(ApiLog.id))
        total_result = await session.execute(total_query)
        total = total_result.scalar() or 0
        
        success_query = select(func.count(ApiLog.id)).where(ApiLog.response_status < 400)
        success_result = await session.execute(success_query)
        success = success_result.scalar() or 0
        
        avg_time_query = select(func.avg(ApiLog.response_time))
        avg_time_result = await session.execute(avg_time_query)
        avg_time = avg_time_result.scalar() or 0
        
        api_count_query = select(
            ApiLog.api_name,
            func.count(ApiLog.id).label("count")
        ).group_by(ApiLog.api_name).order_by(desc("count")).limit(10)
        api_count_result = await session.execute(api_count_query)
        api_counts = [{"api_name": row[0], "count": row[1]} for row in api_count_result.all()]
        
        return {
            "code": 0,
            "data": {
                "total_requests": total,
                "success_requests": success,
                "failed_requests": total - success,
                "success_rate": round(success / total * 100, 2) if total > 0 else 0,
                "avg_response_time": round(avg_time, 2),
                "top_apis": api_counts
            }
        }


@router.delete("/clear")
async def clear_logs():
    async with async_session() as session:
        delete_stmt = delete(ApiLog)
        await session.execute(delete_stmt)
        await session.commit()
    
    return {"code": 0, "message": "日志已清空"}
