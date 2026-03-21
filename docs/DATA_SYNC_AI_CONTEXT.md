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

## 4.1 历史设计原则与当前本地目标

这部分非常重要。维护 `data_sync/` 时，不能只看“当前代码怎么写”，还要理解当初的同步设计目标：

1. 历史方案是“全量手动同步 + 自动增量同步”。
2. 当前本地目标优先级高于自动增量：先保证用于策略回测的本地历史库可用，再考虑日常自动追数。
3. 回测使用时，判断“数据完整”不能只看某个日期是否存在记录，还要优先保证该日期的全量股票覆盖数量足够。
4. 对大表，全量同步不能简单理解为一次性从最早年份拉到最新年份，而应采用“由近到远、分批回补、优先保证最近区间完整”的模式。
5. 程序运行一段时间后，再次执行全量同步时，必须考虑断点快速查询，而不是每次重新扫描全部历史。

换句话说：

- “全量”更接近“面向目标区间的完整补齐”
- “增量”是日常维护能力，不是当前本地回测数据准备的优先事项
- 对大表，股票覆盖度优先于单纯日期覆盖度

## 4.2 按体量区分同步策略

维护同步逻辑时，先判断表体量，而不是先套统一模板。

### 大表

典型包括：

- `stock_daily`
- `stock_adj_factor`
- `stock_daily_basic`
- `stock_factor_pro`

这些表的共同点：

- 行数大
- 与股票数量强相关
- 回测场景下，某个交易日如果只有少量股票有数据，等同于“不完整”

因此设计要求是：

- 手动全量同步时，按“近到远”的时间顺序补齐
- 优先保证最近区间可用于回测，当前优先是近三年
- 判断完成度时，要重点看某交易日覆盖了多少只股票
- 同步过程要支持断点续传和快速定位缺口
- 不能每次都做全历史、全股票、全年份的重扫

### 小表

典型包括：

- `trade_calendar`
- `index_daily`（当前默认指数集合较小）
- `stock_basic`

这些表有时没有刻意拆出复杂的“全量/增量”两套逻辑，不是因为不重要，而是因为：

- 数据体量相对可控
- 全量重拉成本较低
- 缺口判断也更简单

所以维护时不要机械要求所有表都实现完全对称的全量/增量接口。是否需要拆分，取决于体量和回测使用方式。

## 4.3 当前本地目标表的逐表判断

面向当前“先补本地回测库、优先近三年”的目标，建议直接按下表理解：

| 表名 | 类型判断 | 当前现状 | 本地目标 | 手动全量策略 | 断点建议 |
|------|----------|----------|----------|--------------|----------|
| `stock_daily` | 大表 | 近三年已有较大体量，年份和交易日覆盖接近可用，但仍有缺口 | 近三年交易日完整，且每个交易日尽量达到全量股票覆盖 | 按交易日由近到远补齐，先补近三年，再决定是否回补更早年份 | 至少按“表 + 年份”记录；更理想是增加“交易日 + 覆盖股票数” |
| `stock_adj_factor` | 大表 | 日期存在较多，但股票覆盖严重不足，部分年份只有少量股票 | 近三年复权因子与股票覆盖尽量匹配，保证复权回测可靠 | 不能只看缺失日期，必须按“股票 × 日期区间”补齐，仍按近到远优先 | 需要比按年份更细，建议支持“股票批次 + 日期区间”或“交易日 + 覆盖股票数” |
| `stock_daily_basic` | 大表 | 当前几乎未形成近三年数据，只有极少数交易日 | 先补足近三年交易日，并尽量达到全量股票覆盖 | 按交易日由近到远补齐近三年；如果接口按日返回全市场，则优先走按日补齐 | 可先按年份 + 最近缺失交易日，后续再细化到交易日 |
| `index_daily` | 小表 | 默认指数集合很小，当前缺口明显但总量很小 | 先补足近三年全部目标指数交易日 | 直接按指数列表与交易日补齐即可，不必过度复杂化 | 年份级或日期级断点都足够 |
| `stock_factor_pro` | 大表 | 近三年已有一定数据，但交易日覆盖明显不足，且限流敏感 | 先把近三年补到可回测，再考虑更早历史 | 严格按交易日由近到远回补，低并发，优先近三年 | 继续保留年份断点，但建议增加最近完成交易日或批次位置 |

这里最关键的区分是：

- `stock_daily` / `stock_daily_basic` / `stock_factor_pro` 更接近“按交易日拉全市场”的大表
- `stock_adj_factor` 不能只用“某天是否存在数据”来判断完整，因为当前现实数据已经说明同一天可能只覆盖极少股票
- `index_daily` 由于目标指数数量小，可以保留小表思路

## 4.4 当前库内观测到的近三年特征

以下是本地数据库在当前时点的观测结果，用于说明为什么要分表处理：

- `trade_calendar` 近三年开放交易日约 `919` 天。
- `stock_daily`：`2023` 年 `242` 天、`5381` 只股票；`2024` 年 `242` 天、`5433` 只股票；`2025` 年 `243` 天、`5500` 只股票；`2026` 年当前 `49` 天、`5492` 只股票。
- `stock_adj_factor`：`2023` 年 `242` 天但只有 `334` 只股票；`2024` 年 `242` 天但也只有 `334` 只股票；`2025` 年 `243` 天有 `2323` 只股票；`2026` 年当前 `43` 天、`334` 只股票。
- `stock_daily_basic`：当前只看到 `2026` 年 `4` 个交易日，明显未形成近三年可用数据。
- `index_daily`：当前只看到 `2026` 年 `18` 个交易日，总量很小，但缺口明显。
- `stock_factor_pro`：`2023` 年只有 `47` 天、`2024` 年 `68` 天、`2025` 年 `96` 天、`2026` 年当前 `49` 天，说明当前远未补满近三年。

这些观测带来的直接结论是：

1. 当前不能把“有 trade_date distinct”直接等同于“可用于回测”。
2. `stock_adj_factor` 必须额外关注股票覆盖数，否则复权结果不可靠。
3. `stock_daily_basic`、`index_daily`、`stock_factor_pro` 的本地优先事项都是“先把近三年补完整”，不是先讨论自动增量。

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

补充注意：

- 仅按 `trade_date distinct` 判断“这一年完整”只适用于非常粗粒度的检查
- 对股票大表，真正用于回测时还需要结合“每个交易日覆盖了多少只股票”来判断是否足够完整
- 后续若扩展同步状态，优先考虑“日期覆盖 + 股票覆盖”双维度，而不是只保留年份布尔值

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
6. 对回测场景，大表的核心不是“接口调用成功”，而是“最近目标区间内每个交易日都尽量达到全量股票覆盖”。
7. 讨论“全量同步”时，优先理解为“手动触发的完整补齐任务”，其实现要支持由近到远、分批执行和断点快速查询。

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
- 大表在回测场景下的真实完整性

## 9. AI 维护建议

当 AI 需要维护 `data_sync/` 文档时，建议按下面顺序理解代码：

1. `data_sync/sync_runner.py`
2. `data_sync/sync/base.py`
3. `data_sync/sync/*.py`
4. `data_sync/web/sync_api.py`
5. `data_sync/web/table_descriptions.py`
6. `data_sync/README.md`

额外判断原则：

- 如果任务目标是“给回测补齐本地库”，先按表体量分层，再判断是否需要改代码
- 如果现有逻辑已经满足“小表可控、可直接全量”的条件，不要为了形式统一而强行重构
- 如果是大表同步，默认要问自己三个问题：
  1. 最近目标区间是否优先
  2. 股票覆盖数是否优先
  3. 是否支持断点快速续跑

如果问题涉及 Tushare 官方接口文档，再回到：

- `docs/tushare_api_index.json`
- `docs/ai_prompt_documentation.md`
