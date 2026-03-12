"""
数据同步模块 - 将 Tushare 数据同步到 PostgreSQL

功能：
- 同步股票基础信息
- 同步交易日历
- 同步日线行情
- 同步复权因子
- 同步每日指标
- 同步指数行情

使用方法：
    python -m data_sync.sync_runner
"""

__version__ = "1.0.0"
__author__ = "Ai-TuShare"