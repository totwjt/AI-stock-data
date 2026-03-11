from fastapi import APIRouter, Query
from typing import Optional
from app.tushare_client import tushare_client

router = APIRouter(prefix="/indicators", tags=["技术指标"])


@router.get("/daily_basic")
async def get_daily_basic(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYYMMDD"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
    fields: Optional[str] = Query(None, description="返回字段")
):
    """
    获取每日基本面指标
    包含: 收盘价、换手率、量比、市盈率、市净率、市销率、股息率、总股本、流通股本、总市值、流通市值
    """
    kwargs = {}
    if ts_code:
        kwargs["ts_code"] = ts_code
    if trade_date:
        kwargs["trade_date"] = trade_date
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    if fields:
        kwargs["fields"] = fields
    
    df = tushare_client.get_daily_basic(**kwargs)
    return {"code": 0, "data": df.to_dict(orient="records"), "total": len(df)}


@router.get("/factors")
async def get_factors(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYYMMDD"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD")
):
    """
    获取技术面因子数据
    包含: MACD、KDJ、RSI、布林带、ATR、DMI、CCI、BBI、OBV等大量技术指标
    """
    kwargs = {"ts_code": ts_code}
    if trade_date:
        kwargs["trade_date"] = trade_date
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    
    df = tushare_client.get_stk_factor_pro(**kwargs)
    return {"code": 0, "data": df.to_dict(orient="records"), "total": len(df)}
