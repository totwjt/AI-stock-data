# 数据同步模块

`data_sync/` 负责将 Tushare 数据同步到 PostgreSQL，并提供手动同步、状态查询、表结构浏览和定时调度能力。

如果你是在做 AI 辅助开发或文档维护，请优先把这里视为“当前实现说明”，再去参考 `docs/DATA_SYNC_PLAN.md` 这类历史规划文档。

## 模块定位

`data_sync` 与 `app` 模块分离：

- `app`: 实时 API 服务，偏接口调用和 Web 看板
- `data_sync`: 历史数据沉淀，偏批量同步、校验、状态跟踪和 PostgreSQL 查询

数据流向：

```text
Tushare Pro -> data_sync -> PostgreSQL -> 策略系统 / 分析系统 / Web 查询
```

## 目录结构

```text
data_sync/
├── config.py                # 配置管理
├── database.py              # PostgreSQL 异步引擎与会话
├── tushare_client.py        # Tushare 客户端封装
├── sync_runner.py           # CLI 同步入口
├── sync_state.json          # 年度验证状态文件
├── models/                  # PostgreSQL ORM 模型
│   ├── stock_basic.py
│   ├── stock_daily.py
│   ├── stock_adj_factor.py
│   ├── stock_daily_basic.py
│   ├── index_daily.py
│   ├── trade_calendar.py
│   └── stock_factor_pro.py
├── sync/                    # 同步任务与状态逻辑
│   ├── base.py
│   ├── sync_stock_basic.py
│   ├── sync_trade_calendar.py
│   ├── sync_daily.py
│   ├── sync_adj_factor.py
│   ├── sync_daily_basic.py
│   ├── sync_index_daily.py
│   ├── sync_stk_factor_pro.py
│   ├── sync_state.py
│   └── partition_manager.py
├── scheduler/               # APScheduler 定时任务
├── web/                     # Web 查询与同步管理界面
├── logs/                    # 日志目录
├── test_sync.py             # 测试脚本
├── test_partitioned_sync.py
├── example_usage.py
├── IMPLEMENTATION_SUMMARY.md
└── README.md
```

说明：

- `repository/` 目录当前没有实际实现文件，不应默认当作稳定的数据访问层。
- `web/` 已经完成基本功能，不是“待开发”状态。

## 配置

在项目根目录创建 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tushare_sync
DB_USER=wangjiangtao
DB_PASSWORD=

TUSHARE_TOKEN=your_token
TUSHARE_URL=http://lianghua.nanyangqiankun.top

BATCH_SIZE=1000
RETRY_TIMES=3
RETRY_DELAY=5
```

配置来源：

- `data_sync/config.py`
- 通过 `pydantic-settings` 读取 `.env`

## 核心入口

### 1. CLI 同步入口

```bash
./venv/bin/python -m data_sync.sync_runner stock_basic
./venv/bin/python -m data_sync.sync_runner trade_cal
./venv/bin/python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131
./venv/bin/python -m data_sync.sync_runner adj_factor --start_date 20250101 --end_date 20250131
./venv/bin/python -m data_sync.sync_runner daily_basic
./venv/bin/python -m data_sync.sync_runner index_daily
./venv/bin/python -m data_sync.sync_runner stk_factor_pro
./venv/bin/python -m data_sync.sync_runner all
```

`sync_runner.py` 当前支持：

| 参数 | 实际行为 |
|------|----------|
| `full` | 映射到 `stock_basic` |
| `incremental` | 映射到 `daily` |
| `stock_basic` | 股票基础信息同步 |
| `trade_cal` | 交易日历同步 |
| `daily` | 股票日线同步 |
| `adj_factor` | 复权因子同步 |
| `daily_basic` | 每日基本面同步 |
| `index_daily` | 指数行情同步 |
| `stk_factor_pro` | 技术面因子同步 |
| `all` | 顺序执行全部任务 |

### 2. Web 同步与查询入口

```bash
./venv/bin/python -m data_sync.web.run
```

访问：`http://localhost:8001`

### 3. 调度器入口

```bash
./venv/bin/python -m data_sync.scheduler.scheduler
```

## 同步任务与表映射

同步任务名不总等于数据库表名：

| 同步任务名 | 同步类 | 数据表名 | 特点 |
|------------|--------|----------|------|
| `stock_basic` | `StockBasicSync` | `stock_basic` | 可全量，也支持增量差集过滤 |
| `trade_cal` | `TradeCalendarSync` | `trade_calendar` | 全量同步 |
| `daily` | `DailySync` | `stock_daily` | 按年份检查缺失交易日并补齐 |
| `adj_factor` | `AdjFactorSync` | `stock_adj_factor` | 日期区间增量 |
| `daily_basic` | `DailyBasicSync` | `stock_daily_basic` | 支持年度补齐和增量 |
| `index_daily` | `IndexDailySync` | `index_daily` | 支持年度补齐和增量 |
| `stk_factor_pro` | `StkFactorProSync` | `stock_factor_pro` | 按年份逐交易日同步，限流更严格 |

## 历史方案与当前本地优先级

历史设计原则不是“所有表都按同一种方式同步”，而是：

- 手动执行全量同步
- 自动执行增量同步
- 大表优先考虑可恢复、可分批、可断点
- 小表在体量可控时可以不刻意拆成复杂的全量/增量两套逻辑

当前本地目标要优先理解为：

- 先为交易平台策略回测准备本地可用数据
- 优先保证近三年数据可用
- 对股票大表，优先保证每个交易日尽量达到全量股票覆盖
- 暂时不以自动增量同步为主要改造目标

这意味着“全量同步”在这里更接近：

- 手动触发
- 由近到远分批补齐
- 最近区间优先
- 长任务支持断点续跑和快速查询缺口

## 同步策略说明

### 基础表

- `stock_basic`
- `trade_cal`

以全量为主，适合初始化或定期重建。

### 行情类表

- `daily`
- `daily_basic`
- `index_daily`
- `stk_factor_pro`

并不是简单拉一个日期区间后直接落库。当前实现普遍包含：

- 按交易日历推算应有交易日
- 检查数据库内已有日期
- 只补缺失日期
- 完成后按年份做验证
- 将结果写入 `sync_state.json`

但在维护时还要额外区分“大表”和“小表”。

### 大表的维护原则

对以下表，维护时默认按大表思路处理：

- `stock_daily`
- `stock_adj_factor`
- `stock_daily_basic`
- `stock_factor_pro`

要求是：

- 手动全量同步时按“近到远”回补，而不是无差别扫全历史
- 优先保证近三年完整，以满足回测使用
- 判断完整度时，不能只看某交易日是否存在记录，还要看该交易日覆盖了多少只股票
- 程序长期运行后，要支持断点快速续跑，避免每次从头扫描全部历史

### 小表的维护原则

以下表通常可以按小表思路处理：

- `trade_calendar`
- `stock_basic`
- `index_daily`（当前默认指数数量较少时）

特点是：

- 体量相对可控
- 全量成本较低
- 不一定需要复杂的全量/增量双轨设计

所以如果某张表当前逻辑已经足够支撑本地目标，不必为了形式统一强行改造成复杂流程。

## 当前本地目标的逐表策略

针对当前要服务交易平台回测的 5 张目标表，可先按下面的口径设计，不必先修改自动增量：

| 表名 | 归类 | 本地优先目标 | 建议的手动全量策略 |
|------|------|--------------|--------------------|
| `stock_daily` | 大表 | 近三年交易日完整，且每个交易日尽量达到全量股票覆盖 | 按交易日由近到远补齐，先完成近三年 |
| `stock_adj_factor` | 大表 | 近三年复权因子覆盖尽量匹配股票池 | 不能只按日期判断，要按股票与日期区间补齐 |
| `stock_daily_basic` | 大表 | 近三年每日基本面完整 | 如果接口支持按日拉全市场，则按交易日由近到远补齐 |
| `index_daily` | 小表 | 近三年目标指数完整 | 直接按指数列表补齐近三年即可 |
| `stock_factor_pro` | 大表 | 近三年技术面因子先达到可回测 | 严格低并发，按交易日由近到远补齐 |

当前本地库观测到的问题也支持这个分法：

- `stock_daily` 近三年体量已较大，但仍未覆盖全部近三年交易日
- `stock_adj_factor` 某些年份日期很多，但股票覆盖严重不足
- `stock_daily_basic` 当前只有极少交易日
- `index_daily` 当前只有少量交易日，但总量很小
- `stock_factor_pro` 当前只补到了部分交易日，且受限流影响更明显

所以现在的优先顺序应是：

1. 先定手动全量补齐策略
2. 先补近三年
3. 先保证大表的股票覆盖和交易日覆盖
4. 最后再回头考虑自动增量如何衔接

### 复权因子

- `adj_factor`

仍以日期区间增量为主。

## 同步状态与断点

状态文件：`data_sync/sync_state.json`

用途：

- 标记某个表某个年份是否已验证完成
- 支持从近到远逐年补齐
- 减少重复同步

当前重点使用该状态文件的任务：

- `daily`
- `stk_factor_pro`

后续若扩展到更多大表，优先考虑支持：

- 最近目标区间的快速缺口定位
- 断点续跑
- 按年份或按日期批次快速判断是否已完成
- 必要时增加“交易日覆盖股票数”维度，而不是只记录年份布尔状态

## Web 功能

`data_sync/web/` 已实现以下能力：

- 浏览所有表
- 查看表结构
- 查看表数据
- 展示表中文描述和字段说明
- 手动触发同步任务
- 查询任务状态
- 停止任务
- 限制并发同步任务数量

主要页面与接口：

- `/`：首页
- `/table/{table_name}`：浏览表数据
- `/schema/{table_name}`：查看表结构
- `POST /api/sync/{table_name}`：提交同步任务
- `GET /api/sync/status/{task_id}`：查询单任务状态
- `GET /api/sync/status`：查询全部任务状态
- `POST /api/sync/stop/{task_id}`：停止任务
- `GET /api/sync/descriptions`：获取表描述

更多说明见 `data_sync/web/README.md`。

## 调度

当前代码中有两套与调度相关的入口：

1. `data_sync/scheduler/scheduler.py`
   - 面向独立调度进程
   - 包含每日行情类任务和每周基础表任务

2. `data_sync/web/app.py`
   - Web 进程启动后也会注册每日同步任务

维护文档时请以代码为准，不要只引用旧文档中的时间描述。

## 近期开发重点

以下内容基于近期 git 提交整理，仅保留 2026-03-18 到 2026-03-21 的开发演进：

- `2026-03-21`：`stk_factor_pro` 定时任务调整到 `18:00`，并发控制进一步收紧，降低触发 Tushare 限流的风险。
- `2026-03-20`：补入 `stk_factor_pro` 的增量同步方法，并同步更新了 Web 端因子表查询/展示能力。
- `2026-03-19`：同步逻辑从“简单拉取”继续演进到“按年份校验、断点续传、缺失补齐”的模式，`sync_state.py` 和 `sync_state.json` 也在这次演进中加入。
- `2026-03-19`：Web 端任务状态展示从纯百分比改为更关注已同步数量，同时轮询频率和超时处理被优化，避免请求堆积。
- `2026-03-18`：`index_daily` 同步参数兼容性得到修复，并支持多个指数分别查询。

## 错误处理与日志

- 自动重试：`BaseSync.sync_with_retry`
- 批量 UPSERT：`BaseSync.upsert_data`
- 失败回滚：数据库异常时执行回滚
- 日志文件：`data_sync/logs/data_sync.log`

## AI 维护建议

分析 `data_sync` 时，建议优先阅读：

1. `data_sync/sync_runner.py`
2. `data_sync/sync/base.py`
3. `data_sync/sync/*.py`
4. `data_sync/web/sync_api.py`
5. `data_sync/web/table_descriptions.py`
6. `docs/DATA_SYNC_AI_CONTEXT.md`

如果任务是“为回测补齐本地库”，在动代码前先确认：

1. 这是大表还是小表
2. 当前目标区间是否是近三年
3. 是否要优先保证股票覆盖数量
4. 是否需要断点快速续跑
