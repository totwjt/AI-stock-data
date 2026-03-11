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
    
    try:
        df = tushare_client.get_daily_basic(**kwargs)
        if df is None:
            return {"code": 500, "message": "Tushare 返回空数据", "data": [], "total": 0}
        # 处理 nan 值，转换为 None 以符合 JSON 规范
        data = df.replace({float('nan'): None}).to_dict(orient="records")
        return {"code": 0, "data": data, "total": len(df)}
    except Exception as e:
        return {"code": 500, "message": f"获取数据失败: {str(e)}", "data": [], "total": 0}


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
    
    性能优化建议:
    1. 使用 trade_date 查询单日数据最快 (约 0.5秒)
    2. 使用 start_date + end_date 查询指定范围 (建议不超过90天)
    3. 避免不指定日期范围查询全部历史数据 (会很慢)
    """
    kwargs = {"ts_code": ts_code}
    
    # 参数验证和优化
    if trade_date:
        # 单日查询 - 最快
        kwargs["trade_date"] = trade_date
    elif start_date and end_date:
        # 日期范围查询 - 检查范围是否过大
        from datetime import datetime
        
        try:
            start = datetime.strptime(start_date, "%Y%m%d")
            end = datetime.strptime(end_date, "%Y%m%d")
            
            # 检查日期顺序
            if start > end:
                return {"code": 400, "message": "start_date 不能晚于 end_date", "data": [], "total": 0}
            
            # 检查日期范围是否过大 (最多90天)
            days_diff = (end - start).days + 1
            if days_diff > 90:
                return {"code": 400, "message": f"日期范围过大 ({days_diff}天)，最多支持90天", "data": [], "total": 0}
            
            kwargs["start_date"] = start_date
            kwargs["end_date"] = end_date
        except ValueError:
            return {"code": 400, "message": "日期格式错误，应为 YYYYMMDD", "data": [], "total": 0}
    else:
        # 未指定日期范围，提示用户
        return {
            "code": 400, 
            "message": "请指定 trade_date 或 start_date + end_date，避免查询全部历史数据", 
            "data": [], 
            "total": 0
        }
    
    try:
        df = tushare_client.get_stk_factor_pro(**kwargs)
        if df is None:
            return {"code": 500, "message": "Tushare 返回空数据", "data": [], "total": 0}
        # 处理 nan 值，转换为 None 以符合 JSON 规范
        data = df.replace({float('nan'): None}).to_dict(orient="records")
        return {"code": 0, "data": data, "total": len(df)}
    except Exception as e:
        return {"code": 500, "message": f"获取数据失败: {str(e)}", "data": [], "total": 0}
