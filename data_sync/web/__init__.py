# data_sync/web 模块初始化
# 提供 PostgreSQL 数据库的 Web 查询界面

from .app import create_app

__all__ = ["create_app"]