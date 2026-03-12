# 数据同步模块

将 Tushare 数据同步到 PostgreSQL 数据库。

## 目录结构

```
data_sync/
├── __init__.py              模块初始化
├── config.py                配置管理
├── database.py              数据库连接
├── tushare_client.py        Tushare 客户端封装
├── models/                  数据库模型
│   ├── stock_basic.py       股票基础信息
│   ├── stock_daily.py       日线行情
│   ├── stock_adj_factor.py  复权因子
│   ├── stock_daily_basic.py 每日指标
│   ├── index_daily.py       指数行情
│   └── trade_calendar.py    交易日历
├── sync/                    同步任务
│   ├── base.py              基础同步类
│   ├── sync_stock_basic.py
│   ├── sync_trade_calendar.py
│   ├── sync_daily.py
│   ├── sync_adj_factor.py
│   ├── sync_daily_basic.py
│   └── sync_index_daily.py
├── scheduler/               定时任务
│   └── scheduler.py
├── logs/                    日志目录
├── sync_runner.py           同步入口脚本
├── test_sync.py             测试脚本
└── README.md                说明文档
```

## 配置

在项目根目录创建 `.env` 文件：

```env
# PostgreSQL 配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tushare_sync
DB_USER=postgres
DB_PASSWORD=your_password

# Tushare 配置
TUSHARE_TOKEN=your_token
TUSHARE_URL=http://lianghua.nanyangqiankun.top

# 同步配置
BATCH_SIZE=1000
RETRY_TIMES=3
RETRY_DELAY=5
```

## 使用方法

### 1. 运行同步任务

```bash
# 全量同步股票基础信息
python -m data_sync.sync_runner stock_basic

# 增量同步日线行情（默认最近30天）
python -m data_sync.sync_runner daily

# 指定日期范围同步
python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131

# 同步所有数据
python -m data_sync.sync_runner all
```

### 2. 启动定时任务

```bash
python -m data_sync.scheduler.scheduler
```

定时任务会在每日 16:30 自动执行增量同步。

### 3. 运行测试

```bash
python -m data_sync.test_sync
```

## 同步类型

| 类型 | 说明 | 同步方式 |
|------|------|----------|
| stock_basic | 股票基础信息 | 全量同步 |
| trade_cal | 交易日历 | 全量同步 |
| daily | 日线行情 | 增量同步 |
| adj_factor | 复权因子 | 增量同步 |
| daily_basic | 每日指标 | 增量同步 |
| index_daily | 指数行情 | 增量同步 |
| all | 所有数据 | 混合同步 |

## 数据表结构

### stock_basic (股票基础信息)

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | VARCHAR(20) | 股票代码 (主键) |
| symbol | VARCHAR(10) | 股票代码 |
| name | VARCHAR(50) | 股票名称 |
| area | VARCHAR(20) | 地域 |
| industry | VARCHAR(20) | 行业 |
| market | VARCHAR(10) | 市场类型 |
| list_status | VARCHAR(1) | 上市状态 |
| list_date | VARCHAR(10) | 上市日期 |
| delist_date | VARCHAR(10) | 退市日期 |
| is_hs | VARCHAR(1) | 是否沪深港通 |

### stock_daily (日线行情)

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | VARCHAR(20) | 股票代码 (主键) |
| trade_date | VARCHAR(10) | 交易日期 (主键) |
| open | FLOAT | 开盘价 |
| high | FLOAT | 最高价 |
| low | FLOAT | 最低价 |
| close | FLOAT | 收盘价 |
| pre_close | FLOAT | 前收盘价 |
| change | FLOAT | 涨跌额 |
| pct_chg | FLOAT | 涨跌幅 |
| vol | FLOAT | 成交量 |
| amount | FLOAT | 成交额 |

## 注意事项

1. **数据库连接**: 确保 PostgreSQL 服务正常运行
2. **Tushare Token**: 需要有效的 Tushare Pro Token
3. **网络环境**: 确保能访问 Tushare API 服务器
4. **数据量**: 日线数据量较大，建议分批同步
5. **增量同步**: 默认同步最近30天数据，可根据需要调整

## 错误处理

- 自动重试机制：失败时会自动重试 3 次
- 详细日志：所有同步操作都会记录到 `logs/data_sync.log`
- 事务回滚：失败时自动回滚，保证数据一致性