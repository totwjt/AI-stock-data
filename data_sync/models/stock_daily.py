from sqlalchemy import Column, String, Float, Integer, DateTime, Date, Index
from sqlalchemy.sql import func
from data_sync.database import Base


class StockDaily(Base):
    """股票日线行情表"""
    __tablename__ = "stock_daily"
    
    ts_code = Column(String(20), primary_key=True)
    trade_date = Column(String(10), primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    pre_close = Column(Float)
    change = Column(Float)
    pct_chg = Column(Float)
    vol = Column(Float)
    amount = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_stock_daily_ts_code', 'ts_code'),
        Index('idx_stock_daily_trade_date', 'trade_date'),
        Index('idx_stock_daily_ts_trade', 'ts_code', 'trade_date'),
    )