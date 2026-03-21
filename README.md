# Ai-TuShare 股票数据服务

Ai-TuShare 由两个相互独立、但共享同一仓库的子系统组成：

- `app/`: 面向实时查询的 FastAPI 服务，使用 SQLite 记录日志和缓存。
- `data_sync/`: 面向历史数据沉淀的同步子系统，将 Tushare 数据写入 PostgreSQL，并提供查询与同步管理界面。

项目当前最值得优先维护的目录是 `data_sync/`。如果是 AI 辅助开发、补文档或排查同步问题，建议先阅读：

1. `docs/DATA_SYNC_AI_CONTEXT.md`
2. `data_sync/README.md`
3. `SKILLS.md`
4. `CODEX.md`

## 项目结构

```text
Ai-TuShare/
├── app/                      # 实时股票 API 服务
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── tushare_client.py
│   ├── middleware/
│   ├── models/
│   └── routers/
├── data_sync/                # 历史数据同步子系统（重点）
│   ├── config.py             # PostgreSQL/Tushare/同步参数
│   ├── database.py           # SQLAlchemy 异步引擎与会话
│   ├── tushare_client.py     # Tushare 封装
│   ├── models/               # PostgreSQL 表模型
│   ├── sync/                 # 各类同步任务与状态管理
│   ├── scheduler/            # APScheduler 定时任务
│   ├── web/                  # Web 查询与同步管理界面
│   ├── logs/                 # data_sync 日志目录
│   ├── sync_runner.py        # CLI 同步入口
│   ├── sync_state.json       # 年度验证状态
│   └── README.md
├── docs/
│   ├── DATA_SYNC_AI_CONTEXT.md
│   ├── DATA_SYNC_PLAN.md
│   ├── ai_prompt_documentation.md
│   └── tushare_api_index.json
├── static/                   # app 模块看板与 AI 文档静态资源
├── start.sh                  # 一键启动 app/web
├── START_SCRIPT.md
├── SKILLS.md
└── requirements.txt
```

## 模块关系

```text
Tushare Pro
├─ 实时调用 -> app -> SQLite -> Web 看板 / API
└─ 批量同步 -> data_sync -> PostgreSQL -> 策略分析 / 数据查询
```

## data_sync 当前能力

`data_sync/` 已经不是规划中的空目录，而是可运行模块，当前包括：

- 7 个同步任务：`stock_basic`、`trade_cal`、`daily`、`adj_factor`、`daily_basic`、`index_daily`、`stk_factor_pro`
- PostgreSQL 异步写入与 UPSERT 去重
- 基于 `sync_state.json` 的年度验证/断点状态
- Web 查询与手动触发同步界面
- APScheduler 定时任务

详细说明见 `data_sync/README.md`。

## 快速启动

### 使用启动脚本

```bash
./start.sh app
./start.sh web
./start.sh all
./start.sh --help
```

### 手动启动 app

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m app.main
```

访问：

- `http://localhost:8000/`
- `http://localhost:8000/docs`
- `http://localhost:8000/ai-docs`

### 手动启动 data_sync Web

```bash
./venv/bin/python -m data_sync.web.run
```

访问：

- `http://localhost:8001/`

### 运行 data_sync CLI 同步

```bash
./venv/bin/python -m data_sync.sync_runner stock_basic
./venv/bin/python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131
./venv/bin/python -m data_sync.sync_runner stk_factor_pro
./venv/bin/python -m data_sync.sync_runner all
```

## 配置

项目主要依赖 `.env`：

```env
TUSHARE_TOKEN=your_token
TUSHARE_URL=http://lianghua.nanyangqiankun.top

DB_HOST=localhost
DB_PORT=5432
DB_NAME=tushare_sync
DB_USER=wangjiangtao
DB_PASSWORD=
```

`app/` 和 `data_sync/` 使用不同数据库：

- `app`: SQLite
- `data_sync`: PostgreSQL

## AI 协作建议

- 查询 Tushare 文档 URL 时，优先读取 `docs/tushare_api_index.json`
- 分析同步逻辑时，优先查看 `data_sync/sync_runner.py` 与 `data_sync/sync/`
- 理解表结构和任务映射时，优先查看 `data_sync/models/`、`data_sync/web/table_descriptions.py`
- 区分“历史计划”和“当前实现”：`docs/DATA_SYNC_PLAN.md` 是历史计划文档，不应替代当前 README
- 如果是 Codex/AI 进入仓库协作，优先阅读 `CODEX.md`
