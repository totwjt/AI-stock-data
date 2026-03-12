# Ai-TuShare 股票数据API服务

## 项目概述

基于Tushare Pro的股票数据API服务，提供股票基础信息和技术指标接口，带有Web看板监控。本项目专为AI开发优化，提供完整的项目上下文和开发指南。

### 项目定位
- **数据服务层**: 提供标准化的股票数据API接口
- **AI开发友好**: 完整的项目文档、API说明和开发规范
- **监控看板**: 实时监控API调用情况和系统状态

## 技术栈

- **Web框架**: FastAPI
- **数据库**: SQLite (aiosqlite) - 用于API日志和缓存
- **数据源**: Tushare Pro - 股票数据源
- **前端**: 原生HTML/CSS/JavaScript - Web看板
- **数据同步**: PostgreSQL - 用于大规模数据存储（可选模块）

## 项目架构

```
Ai-TuShare/
├── app/                    # FastAPI应用（股票API服务）
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   ├── tushare_client.py  # Tushare客户端封装
│   ├── middleware/        # 中间件
│   ├── models/            # 数据模型
│   └── routers/           # API路由
├── static/                # 静态资源（Web看板）
├── data/                  # SQLite数据库文件（API日志）
├── data_sync/             # 数据同步模块（PostgreSQL）
│   ├── models/            # PostgreSQL数据模型
│   ├── sync/              # 同步任务
│   ├── scheduler/         # 定时任务
│   ├── repository/        # 数据访问层
│   ├── web/               # Web查询界面（待开发）
│   └── sync_runner.py     # 同步入口脚本
├── docs/                  # 文档
├── start.sh               # 启动脚本
└── requirements.txt       # 依赖包
```

## 模块说明

### 1. app 模块（股票API服务）
- **功能**: 提供股票数据API接口和Web看板
- **数据库**: SQLite（用于API日志和缓存）
- **数据源**: Tushare Pro（实时API调用）
- **端口**: 8000
- **访问地址**: http://localhost:8000

### 2. data_sync 模块（数据同步）
- **功能**: 将Tushare数据同步到PostgreSQL数据库
- **数据库**: PostgreSQL（大规模数据存储）
- **数据源**: Tushare Pro（定时同步）
- **用途**: 为策略系统提供数据基础设施

### 模块关系
```
Tushare Pro (实时API) → app模块 → SQLite (API日志)
Tushare Pro (定时同步) → data_sync模块 → PostgreSQL (历史数据)
```

## 开发规范

### 代码风格
- 使用Python类型提示
- 遵循PEP 8规范
- 函数命名使用snake_case
- 类命名使用CamelCase

### AI开发提示
- 所有数据访问通过API接口进行
- 禁止直接调用Tushare API（数据同步模块除外）
- 使用PostgreSQL数据库进行大规模数据存储
- API响应格式统一为JSON

### 项目配置
配置文件位于 `app/config.py`，支持环境变量覆盖：

```python
TUSHARE_TOKEN = "你的token"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"
```

## 项目结构

```
Ai-TuShare/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── tushare_client.py    # Tushare客户端封装
│   ├── middleware/
│   │   └── logging.py        # 请求日志中间件
│   ├── models/
│   │   └── log.py           # API日志数据模型
│   └── routers/
│       ├── stock_basic.py   # 股票基础信息API
│       ├── indicators.py    # 技术指标API
│       └── logs.py          # 请求日志API
├── static/
│   └── index.html           # Web看板页面
├── data/                    # 数据库存储目录
├── requirements.txt         # Python依赖
├── .gitignore
└── nothing.md              # Tushare配置参考
```

## 快速启动

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 安装依赖
./venv/bin/pip install -r requirements.txt

# 3. 配置Token (可选)
# 创建 .env 文件:
# TUSHARE_TOKEN=你的token

# 4. 启动服务
./venv/bin/python -m app.main

# 5. 访问
# http://localhost:8000
```

## API接口

### 股票基础信息

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/stock/list` | GET | 股票列表 |
| `/api/v1/stock/daily` | GET | 日线行情 |
| `/api/v1/stock/trade_cal` | GET | 交易日历 |

### 技术指标

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/indicators/daily_basic` | GET | 每日基本面指标 |
| `/api/v1/indicators/factors` | GET | 技术面因子 |

### 请求日志

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/logs/list` | GET | 请求日志列表 |
| `/api/v1/logs/stats` | GET | 请求统计信息 |

## API详细说明

### 股票列表
```
GET /api/v1/stock/list?list_status=L&fields=ts_code,name

参数:
- exchange: 交易所 (SSE/SZSE/BSE)
- list_status: 上市状态 (L/D/P)
- fields: 返回字段
```

### 日线行情
```
GET /api/v1/stock/daily?ts_code=000001.SZ&start_date=20250101&end_date=20250110

参数:
- ts_code: 股票代码 (必需)
- start_date: 开始日期 (YYYYMMDD)
- end_date: 结束日期 (YYYYMMDD)
- fields: 返回字段
```

### 每日基本面指标
```
GET /api/v1/indicators/daily_basic?ts_code=000001.SZ&start_date=20250101

返回字段: 收盘价、换手率、量比、市盈率、市净率、市销率、股息率、总股本、流通股本、总市值、流通市值
```

### 技术面因子
```
GET /api/v1/indicators/factors?ts_code=000001.SZ&start_date=20250101

返回字段: MACD、KDJ、RSI、布林带、ATR、DMI、CCI、BBI、OBV等大量技术指标
```

## Web看板

访问 `http://localhost:8000` 查看:
- 总请求数/成功/失败统计
- 请求日志列表
- Top API调用排行

## 配置

在 `app/config.py` 或 `.env` 文件中配置:

```python
TUSHARE_TOKEN = "1d7aabe519e1f1bf7cbe4e5c4f49fbad70bb3778e0c1a8abf260e183b2c7"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"
```

## 数据同步模块

项目包含数据同步模块，可将 Tushare 数据同步到 PostgreSQL 数据库。

### 同步模块结构

```
data_sync/
├── config.py              配置管理
├── database.py            PostgreSQL连接
├── models/                数据库模型
├── sync/                  同步任务
├── scheduler/             定时任务
├── sync_runner.py         同步入口脚本
└── test_sync.py           测试脚本
```

### 使用方法

```bash
# 同步股票基础信息
python -m data_sync.sync_runner stock_basic

# 同步日线行情（增量）
python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131

# 启动定时任务
python -m data_sync.scheduler.scheduler
```

详细说明见 `data_sync/README.md`

## 注意事项

- 技术因子接口 `stk_factor_pro` 需要Tushare专业版积分
- 默认端口8000，如需更改修改 `app/main.py`
- 数据同步模块需要 PostgreSQL 数据库
