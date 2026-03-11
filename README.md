# Ai-TuShare 股票数据API服务

基于Tushare Pro的股票数据API服务，提供股票基础信息和技术指标接口，带有Web看板监控。

## 技术栈

- **Web框架**: FastAPI
- **数据库**: SQLite (aiosqlite)
- **数据源**: Tushare Pro
- **前端**: 原生HTML/CSS/JavaScript

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
TUSHARE_TOKEN = "你的token"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"
```

## 注意事项

- 技术因子接口 `stk_factor_pro` 需要Tushare专业版积分
- 默认端口8000，如需更改修改 `app/main.py`
