from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from sqlalchemy.sql import func
from data_sync.database import Base


class StockAdjFactor(Base):
    """股票复权因子表"""
    __tablename__ = "stock_adj_factor"
    
    ts_code = Column(String(20), primary_key=True)
    trade_date = Column(String(10), primary_key=True)
    adj_factor = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_adj_factor_ts_code', 'ts_code'),
        Index('idx_adj_factor_trade_date', 'trade_date'),
    )