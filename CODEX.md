# Codex 协作指南

本文档面向在本仓库中工作的 Codex / AI 编码助手，目标是帮助快速建立正确上下文，减少被旧文档或命名差异误导。

## 1. 先读什么

处理本项目时，建议优先阅读顺序如下：

1. `README.md`
2. `docs/DATA_SYNC_AI_CONTEXT.md`
3. `data_sync/README.md`
4. `SKILLS.md`

如果任务明确落在 `data_sync/`，继续阅读：

5. `data_sync/sync_runner.py`
6. `data_sync/sync/base.py`
7. `data_sync/sync/*.py`
8. `data_sync/web/sync_api.py`
9. `data_sync/web/table_descriptions.py`

## 2. 项目有两个子系统

### `app/`

- 面向实时 API 调用
- 使用 SQLite
- 入口：`python -m app.main`
- 默认端口：`8000`

### `data_sync/`

- 面向历史数据同步和 PostgreSQL 管理
- 使用 PostgreSQL
- CLI 入口：`python -m data_sync.sync_runner ...`
- Web 入口：`python -m data_sync.web.run`
- 默认端口：`8001`

当前仓库中，`data_sync/` 是更复杂、也更需要优先理解上下文的目录。

## 3. 最容易踩坑的约定

### 目录名

- 正确：`data_sync`
- 错误：`data-sync`

### 同步任务名和表名不同

| 同步任务名 | 数据表名 |
|------------|----------|
| `stock_basic` | `stock_basic` |
| `trade_cal` | `trade_calendar` |
| `daily` | `stock_daily` |
| `adj_factor` | `stock_adj_factor` |
| `daily_basic` | `stock_daily_basic` |
| `index_daily` | `index_daily` |
| `stk_factor_pro` | `stock_factor_pro` |

不要把下面这些混成同一个名字：

- `trade_cal` 和 `trade_calendar`
- `daily` 和 `stock_daily`
- `adj_factor` 和 `stock_adj_factor`
- `daily_basic` 和 `stock_daily_basic`
- `stk_factor_pro` 和 `stock_factor_pro`

### 文档新旧判断

- `docs/DATA_SYNC_AI_CONTEXT.md`：当前实现上下文
- `data_sync/README.md`：当前实现说明
- `docs/DATA_SYNC_PLAN.md`：历史规划文档，仅作背景参考

如果三者冲突，优先信任代码，其次是当前实现文档。

## 4. data_sync 的真实实现特点

`data_sync/` 当前不是简单的“按日期拉取后写库”，而是一个带状态和校验的同步系统，包含：

- PostgreSQL 异步写入
- 批量 UPSERT/去重
- 年度校验
- `sync_state.json` 断点状态
- Web 手动触发与状态查询
- 调度器
- `stk_factor_pro` 的限流约束

尤其是：

- `DailySync`
- `DailyBasicSync`
- `IndexDailySync`
- `StkFactorProSync`

这些任务都可能包含“按年份补齐、校验缺口、跳过已验证年份”的逻辑。

## 5. 修改代码时要联动检查什么

### 修改同步任务

至少检查：

- `data_sync/sync_runner.py`
- `data_sync/web/sync_api.py`
- `data_sync/web/table_descriptions.py`
- `data_sync/README.md`
- `docs/DATA_SYNC_AI_CONTEXT.md`

### 修改调度时间

至少检查：

- `data_sync/scheduler/scheduler.py`
- `data_sync/web/app.py`
- `data_sync/README.md`
- `docs/DATA_SYNC_AI_CONTEXT.md`

### 新增同步任务或表

至少同步更新：

- `data_sync/models/`
- `data_sync/sync/__init__.py`
- `data_sync/sync_runner.py`
- `data_sync/web/sync_api.py`
- `data_sync/web/table_descriptions.py`
- `data_sync/README.md`
- `docs/DATA_SYNC_AI_CONTEXT.md`
- `SKILLS.md`

## 6. 和 Tushare 文档相关时

如果问题是“某个 Tushare API 的官方文档在哪”，优先读取：

1. `docs/tushare_api_index.json`
2. `docs/ai_prompt_documentation.md`

不要先凭记忆硬写 URL。

## 7. 近期演进方向

最近几天的开发重点主要集中在：

- `stk_factor_pro` 增量同步
- 同步状态持久化
- 按年份补齐和验证
- Web 轮询与状态展示优化
- 限流与调度时间调整

说明当前维护重点是：

- 同步稳定性
- 缺失数据修复
- 限流控制
- Web 可观察性

## 8. 推荐工作方式

1. 先确认任务属于 `app` 还是 `data_sync`
2. 如果是 `data_sync`，先确认说的是“同步任务名”还是“数据库表名”
3. 修改文档时，区分“当前实现”与“历史规划”
4. 修改代码后，检查是否需要联动更新 AI 文档

如果不确定，优先把问题收敛到：

- 入口文件是哪一个
- 映射名是什么
- 当前行为以哪段代码为准
