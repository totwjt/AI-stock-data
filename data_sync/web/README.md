# Web 查询与同步界面

为 PostgreSQL 数据库提供 Web 查询界面和数据同步功能。

## 功能

### 查询功能
- 浏览所有表
- 查看表结构（列名、类型、主键等）
- 浏览表数据（前100条）

### 同步功能
- 首页表列表显示同步按钮
- 支持手动触发同步任务
- 实时显示同步状态（进行中/完成/失败）
- 支持并发同步（最多3个任务同时运行）
- 增量同步默认最近30天数据

## 启动方式

```bash
cd data_sync/web
python run.py
```

访问 http://localhost:8001

## 接口说明

### Web 界面

#### 首页
- URL: `/`
- 功能: 显示所有表列表，包含同步按钮和状态指示

#### 浏览表数据
- URL: `/table/{table_name}`
- 参数: `limit` (默认100)
- 功能: 显示表的前N条数据

#### 查看表结构
- URL: `/schema/{table_name}`
- 功能: 显示表的列定义、主键、行数等信息

### 同步 API

#### 触发同步
- URL: `POST /api/sync/{table_name}`
- 参数:
  - `start_date`: 开始日期 (YYYYMMDD)，增量同步时可选
  - `end_date`: 结束日期 (YYYYMMDD)，增量同步时可选
- 返回: `{task_id: str, message: str}`
- 示例:
  ```bash
  curl -X POST http://localhost:8001/api/sync/stock_basic
  curl -X POST http://localhost:8001/api/sync/daily -H "Content-Type: application/json" -d '{"start_date":"20250101","end_date":"20250131"}'
  ```

#### 查询任务状态
- URL: `GET /api/sync/status/{task_id}`
- 返回: 任务详细状态（状态、进度、记录数、错误信息等）
- 示例:
  ```bash
  curl http://localhost:8001/api/sync/status/{task_id}
  ```

#### 查询所有任务状态
- URL: `GET /api/sync/status`
- 返回: 所有任务的状态列表

#### 停止任务
- URL: `POST /api/sync/stop/{task_id}`
- 返回: 操作结果

#### 获取可同步表列表
- URL: `GET /api/sync/tables`
- 返回: 可同步的表名列表及同步类型

## 同步类型

| 表名 | 同步类型 | 说明 |
|------|----------|------|
| stock_basic | 全量 | 股票基础信息 |
| trade_calendar | 全量 | 交易日历 |
| daily | 增量 | 日线行情（默认30天） |
| adj_factor | 增量 | 复权因子（默认30天） |
| daily_basic | 增量 | 每日指标（默认30天） |
| index_daily | 增量 | 指数行情（默认30天） |

## 并发控制

- 最多同时运行 3 个同步任务
- 超出限制的任务会进入等待队列
- 使用 asyncio.Semaphore 实现并发控制

## 状态管理

同步任务状态包括：
- **pending**: 等待中
- **running**: 运行中
- **completed**: 完成
- **failed**: 失败
- **stopped**: 已停止

任务信息存储在内存中，可通过 API 查询实时状态。

## 技术实现

### 同步管理器 (sync_manager.py)
- 使用 asyncio 实现异步任务管理
- 信号量控制并发数量
- 任务状态跟踪和存储

### 同步 API (sync_api.py)
- 基于 FastAPI 的 RESTful API
- 集成现有的同步任务逻辑
- 支持全量和增量同步

### Web 界面 (app.py)
- 前端 JavaScript 实现状态轮询
- 实时更新同步状态
- 用户友好的按钮和状态指示

## 注意事项

1. **数据库连接**: 需要配置正确的 PostgreSQL 连接信息（环境变量）
2. **Tushare Token**: 需要有效的 Tushare Pro Token
3. **并发限制**: 最多3个任务同时运行，避免数据库压力过大
4. **内存存储**: 任务状态存储在内存中，重启服务后丢失
5. **增量同步**: 默认最近30天，可通过 API 参数调整