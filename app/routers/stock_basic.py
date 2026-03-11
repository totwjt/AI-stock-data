from fastapi import APIRouter, Query
from typing import Optional, List
from app.tushare_client import tushare_client

router = APIRouter(prefix="/stock", tags=["股票基础信息"])


@router.get("/list")
async def get_stock_list(
    exchange: Optional[str] = Query(None, description="交易所: SSE/SZSE/BSE"),
    list_status: Optional[str] = Query("L", description="上市状态: L/D/P"),
    fields: Optional[str] = Query(None, description="返回字段，逗号分隔")
):
    """
    获取股票列表
    - exchange: 交易所 SSE上交所 SZSE深交所 BSE北交所
    - list_status: L上市 D退市 P暂停
    """
    kwargs = {}
    if exchange:
        kwargs["exchange"] = exchange
    if list_status:
        kwargs["list_status"] = list_status
    if fields:
        kwargs["fields"] = fields
    
    try:
        df = tushare_client.get_stock_basic(**kwargs)
        if df is None:
            return {"code": 500, "message": "Tushare 返回空数据", "data": [], "total": 0}
        # 处理 nan 值，转换为 None 以符合 JSON 规范
        data = df.replace({float('nan'): None}).to_dict(orient="records")
        return {"code": 0, "data": data, "total": len(df)}
    except Exception as e:
        return {"code": 500, "message": f"获取数据失败: {str(e)}", "data": [], "total": 0}


@router.get("/daily")
async def get_daily(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
    fields: Optional[str] = Query(None, description="返回字段")
):
    """
    获取日线行情
    """
    kwargs = {"ts_code": ts_code}
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    if fields:
        kwargs["fields"] = fields
    
    try:
        df = tushare_client.get_daily(**kwargs)
        if df is None:
            return {"code": 500, "message": "Tushare 返回空数据", "data": [], "total": 0}
        # 处理 nan 值，转换为 None 以符合 JSON 规范
        data = df.replace({float('nan'): None}).to_dict(orient="records")
        return {"code": 0, "data": data, "total": len(df)}
    except Exception as e:
        return {"code": 500, "message": f"获取数据失败: {str(e)}", "data": [], "total": 0}


@router.get("/trade_cal")
async def get_trade_cal(
    exchange: str = Query("SSE", description="交易所"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD")
):
    """
    获取交易日历
    """
    kwargs = {"exchange": exchange}
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    
    try:
        df = tushare_client.get_trade_cal(**kwargs)
        if df is None:
            return {"code": 500, "message": "Tushare 返回空数据", "data": [], "total": 0}
        # 处理 nan 值，转换为 None 以符合 JSON 规范
        data = df.replace({float('nan'): None}).to_dict(orient="records")
        return {"code": 0, "data": data, "total": len(df)}
    except Exception as e:
        return {"code": 500, "message": f"获取数据失败: {str(e)}", "data": [], "total": 0}
