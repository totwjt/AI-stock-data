from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime, timezone


def get_beijing_time():
    return datetime.now(timezone.utc).astimezone()


class ApiLog(Base):
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String(100), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    params = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_beijing_time, index=True)
