from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.sql import func
from data_sync.database import Base


class TradeCalendar(Base):
    """交易日历表"""
    __tablename__ = "trade_calendar"
    
    exchange = Column(String(10), primary_key=True)
    cal_date = Column(String(10), primary_key=True)
    is_open = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_trade_calendar_exchange', 'exchange'),
        Index('idx_trade_calendar_cal_date', 'cal_date'),
    )