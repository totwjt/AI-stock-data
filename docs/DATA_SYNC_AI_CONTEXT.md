# Data Sync AI 上下文文档

本文档用于帮助 AI 或新同事快速理解 `data_sync/` 目录的当前实现状态。这里描述的是“现在的代码”，不是早期规划。

## 1. 模块定位

`data_sync/` 是项目中的历史数据同步子系统，职责是：

1. 从 Tushare 拉取基础数据和行情数据
2. 清洗并写入 PostgreSQL
3. 维护同步状态、验证状态和日志
4. 通过 Web 界面提供查询、手动触发和定时同步能力

它不负责：

- 实时 API 对外服务
- 策略回测
- 交易执行

## 2. 目录结构

```text
data_sync/
├── config.py
├── database.py
├── tushare_client.py
├── sync_runner.py
├── sync_state.json
├── models/
│   ├── stock_basic.py
│   ├── stock_daily.py
│   ├── stock_adj_factor.py
│   ├── stock_daily_basic.py
│   ├── index_daily.py
│   ├── trade_calendar.py
│   └── stock_factor_pro.py
├── sync/
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
├── scheduler/
│   └── scheduler.py
├── web/
│   ├── app.py
│   ├── run.py
│   ├── sync_api.py
│   ├── sync_manager.py
│   ├── table_descriptions.py
│   └── README.md
└── README.md
```

## 3. 核心入口

### CLI 入口

文件：`data_sync/sync_runner.py`

支持的同步类型：

- `stock_basic`
- `trade_cal`
- `daily`
- `adj_factor`
- `daily_basic`
- `index_daily`
- `stk_factor_pro`
- `all`

兼容别名：

- `full` -> `stock_basic`
- `incremental` -> `daily`

示例：

```bash
./venv/bin/python -m data_sync.sync_runner stock_basic
./venv/bin/python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131
./venv/bin/python -m data_sync.sync_runner stk_factor_pro
```

### Web 入口

文件：`data_sync/web/run.py`

启动命令：

```bash
./venv/bin/python -m data_sync.web.run
```

默认端口：`8001`

### 定时任务入口

文件：`data_sync/scheduler/scheduler.py`

启动命令：

```bash
./venv/bin/python -m data_sync.scheduler.scheduler
```

## 4. 同步任务与数据库表映射

这里最容易混淆的是“同步任务名”和“数据库表名”并不总相同。

| 同步任务名 | 主要类 | 数据表名 | 默认策略 |
|------------|--------|----------|----------|
| `stock_basic` | `StockBasicSync` | `stock_basic` | 全量 / 增量差集 |
| `trade_cal` | `TradeCalendarSync` | `trade_calendar` | 全量 |
| `daily` | `DailySync` | `stock_daily` | 年度缺口同步 + 近几日增量 |
| `adj_factor` | `AdjFactorSync` | `stock_adj_factor` | 日期区间增量 |
| `daily_basic` | `DailyBasicSync` | `stock_daily_basic` | 年度补齐或增量 |
| `index_daily` | `IndexDailySync` | `index_daily` | 年度补齐或增量 |
| `stk_factor_pro` | `StkFactorProSync` | `stock_factor_pro` | 按年份逐交易日同步 |

注意：

- Web API 里使用的是“同步任务名”
- PostgreSQL 中看到的是“数据库表名”
- `table_descriptions.py` 同时混用了两类命名，维护时需要特别留意

## 5. 代码层设计

### `BaseSync`

文件：`data_sync/sync/base.py`

提供所有同步器共用能力：

- 日志初始化
- 批量写入
- PostgreSQL `ON CONFLICT DO NOTHING`
- 自动去重
- 按字段数量拆批，避免 PostgreSQL 参数数量超限
- 重试包装 `sync_with_retry`

### 状态管理

文件：`data_sync/sync/sync_state.py`

状态文件：`data_sync/sync_state.json`

用途：

- 记录某个表某个年份是否已验证完成
- 支持从最近年份向历史年份回补
- 避免每次都从头同步

典型使用者：

- `DailySync`
- `StkFactorProSync`

### 年度验证

`DailySync` 和 `StkFactorProSync` 都依赖交易日历表来判断某一年应该有哪些交易日，再与现有数据日期做比较。

这意味着：

- `trade_calendar` 是很多行情表校验的基础依赖
- 若交易日历不完整，后续验证结果会失真

## 6. Web 子系统说明

`data_sync/web/` 已完成基础实现，不是待开发目录。

主要能力：

- 首页列出 PostgreSQL 中的表
- 查看表结构和样本数据
- 手动触发同步任务
- 查询任务状态
- 停止任务
- 维护内存中的任务状态
- 提供表说明与字段说明
- 定时触发计划同步

主要文件职责：

- `app.py`: FastAPI 应用与首页 HTML
- `sync_api.py`: 同步 API 和状态 API
- `sync_manager.py`: 任务队列、并发控制、状态存储
- `table_descriptions.py`: 表中文说明、字段描述

## 7. 当前需要特别注意的实现事实

1. `docs/DATA_SYNC_PLAN.md` 是早期规划文档，目录结构和部分策略已经过期。
2. 仓库中存在 `data_sync/repository/` 目录，但当前没有实际实现文件；不要默认认为仓库采用 repository pattern。
3. `stk_factor_pro` 已经纳入同步入口和 Web 管理能力，但很多旧文档仍未完整写入该任务。
4. `data_sync/web/app.py` 与 `data_sync/scheduler/scheduler.py` 中的调度时间描述存在历史遗留差异，修改调度文档时要以代码为准。
5. `DailySync`、`DailyBasicSync`、`IndexDailySync`、`StkFactorProSync` 并不只是简单“按日期区间拉取”，它们包含按年份补齐、校验和跳过逻辑。

## 8. 近期开发脉络

仅保留最近几天的提交，帮助快速理解当前演进方向：

- `2026-03-21`：`stk_factor_pro` 调度时间调整到 `18:00`，并发控制优化，目标是避免限流。
- `2026-03-20`：新增 `stk_factor_pro` 增量同步方法；Web 因子表查询界面同步增强。
- `2026-03-19`：引入 `sync_state.py` 和 `sync_state.json`，形成按年份验证、断点续传、缺口补齐的同步模式。
- `2026-03-19`：Web 轮询增加超时与节流处理，状态展示从单纯百分比向“已同步数量”倾斜。
- `2026-03-18`：`index_daily` 同步参数问题被修复，并支持多个指数分别查询。

这些提交说明当前 `data_sync` 的维护重点已经从“先跑起来”转向：

- 长时间同步的稳定性
- 缺失数据补齐
- 限流控制
- Web 可观察性

## 9. AI 维护建议

当 AI 需要维护 `data_sync/` 文档时，建议按下面顺序理解代码：

1. `data_sync/sync_runner.py`
2. `data_sync/sync/base.py`
3. `data_sync/sync/*.py`
4. `data_sync/web/sync_api.py`
5. `data_sync/web/table_descriptions.py`
6. `data_sync/README.md`

如果问题涉及 Tushare 官方接口文档，再回到：

- `docs/tushare_api_index.json`
- `docs/ai_prompt_documentation.md`
