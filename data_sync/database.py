from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings
import os

# 确保日志目录存在
os.makedirs(settings.log_dir, exist_ok=True)

# 创建异步引擎
engine = create_async_engine(settings.database_url, echo=False)

# 创建异步会话工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# 导入所有模型以确保它们被注册到 Base.metadata
from .models import (
    StockBasic,
    StockDaily,
    StockAdjFactor,
    StockDailyBasic,
    IndexDaily,
    TradeCalendar,
)


async def get_db():
    """获取数据库会话"""
    async with async_session() as session:
        yield session


async def init_db():
    """初始化数据库，创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)