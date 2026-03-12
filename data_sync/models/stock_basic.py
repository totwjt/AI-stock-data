from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from data_sync.database import Base


class StockBasic(Base):
    """股票基础信息表"""
    __tablename__ = "stock_basic"
    
    ts_code = Column(String(20), primary_key=True, comment="股票代码")
    symbol = Column(String(10), comment="股票代码")
    name = Column(String(50), comment="股票名称")
    area = Column(String(20), comment="地域")
    industry = Column(String(20), comment="行业")
    market = Column(String(10), comment="市场类型")
    list_status = Column(String(1), comment="上市状态 L/D/P")
    list_date = Column(String(10), comment="上市日期")
    delist_date = Column(String(10), comment="退市日期")
    is_hs = Column(String(1), comment="是否沪深港通标的")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())