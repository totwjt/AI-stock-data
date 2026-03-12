# Web 查询界面

为 PostgreSQL 数据库提供 Web 查询界面。

## 功能

- 浏览所有表
- 查看表结构（列名、类型、主键等）
- 浏览表数据（前100条）

## 启动方式

```bash
cd data_sync/web
python run.py
```

访问 http://localhost:8001

## 接口说明

### 首页
- URL: `/`
- 功能: 显示所有表列表

### 浏览表数据
- URL: `/table/{table_name}`
- 参数: `limit` (默认100)
- 功能: 显示表的前N条数据

### 查看表结构
- URL: `/schema/{table_name}`
- 功能: 显示表的列定义、主键、行数等信息