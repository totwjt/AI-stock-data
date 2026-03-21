# Ai-TuShare 项目配置

## Skills

### data-sync-context
`data_sync/` 是当前仓库里最复杂、也最容易被旧文档误导的模块。分析或修改它时，请优先遵循下面的顺序：

1. 先看 `docs/DATA_SYNC_AI_CONTEXT.md`
2. 再看 `data_sync/README.md`
3. 然后看 `data_sync/sync_runner.py` 和 `data_sync/sync/`

关键约定：

- 目录名是 `data_sync`，不是 `data-sync`
- 同步任务名和数据库表名不总相同
- `docs/DATA_SYNC_PLAN.md` 是历史规划，不代表当前实现
- `data_sync/web/` 已可用，不是待开发目录
- `stk_factor_pro` 已经接入 CLI 和 Web，同步时要考虑限流

任务名与表名映射：

| 同步任务名 | 数据表名 |
|------------|----------|
| `stock_basic` | `stock_basic` |
| `trade_cal` | `trade_calendar` |
| `daily` | `stock_daily` |
| `adj_factor` | `stock_adj_factor` |
| `daily_basic` | `stock_daily_basic` |
| `index_daily` | `index_daily` |
| `stk_factor_pro` | `stock_factor_pro` |

### tushare-reference
项目基于Tushare Pro数据接口，官方文档地址：https://tushare.pro/document/2

**文档 URL 检索规则**：
1. **优先查看本地索引**：检索 API 文档 URL 时，首先查看 `docs/tushare_api_index.json` 文件
2. **索引文件位置**：`/Users/wangjiangtao/Documents/AI/Ai-TuShare/docs/tushare_api_index.json`
3. **索引格式**：JSON 数组，每个元素包含 `api`、`name`、`doc` 三个字段
4. **未找到处理**：如果在本地索引中未找到该接口，请先补充到 `tushare_api_index.json` 文件中
5. **补充方法**：添加新条目 `{ "api": "接口名", "name": "接口中文名", "doc": "官方文档URL" }`
6. **详细说明**：参见 `docs/ai_prompt_documentation.md`

**常用接口文档**：
- 股票列表: https://tushare.pro/document/2?doc_id=25
- 日线行情: https://tushare.pro/document/2?doc_id=27
- 每日指标: https://tushare.pro/document/2?doc_id=32
- 技术面因子(专业版): https://tushare.pro/document/2?doc_id=328
- 指数技术面因子: https://tushare.pro/document/2?doc_id=358
- 基金技术面因子: https://tushare.pro/document/2?doc_id=359
- 可转债技术面因子: https://tushare.pro/document/2?doc_id=392

**积分说明**：
- 基础接口：免费，无需积分
- 技术面因子：5000积分/分钟30次，8000积分以上/分钟500次
- 积分获取：https://tushare.pro/document/1?doc_id=13

### api-endpoints

项目API端点：

```
股票基础信息:
- GET  /api/v1/stock/list        股票列表
- GET  /api/v1/stock/daily       日线行情
- GET  /api/v1/stock/trade_cal   交易日历

技术指标:
- GET  /api/v1/indicators/daily_basic  每日基本面
- GET  /api/v1/indicators/factors      技术面因子(需5000积分)

系统管理:
- GET  /api/v1/logs/list         请求日志
- GET  /api/v1/logs/stats        请求统计
```

### quick-start

快速启动指南：

```bash
./start.sh app
./start.sh web

# 或分别启动
./venv/bin/python -m app.main
./venv/bin/python -m data_sync.web.run

# CLI 同步入口
./venv/bin/python -m data_sync.sync_runner stock_basic
./venv/bin/python -m data_sync.sync_runner daily --start_date 20250101 --end_date 20250131
```

### tech-stack

技术栈：
- 后端: FastAPI + SQLAlchemy + aiosqlite
- 前端: 原生HTML/CSS/JavaScript
- 数据源: Tushare Pro
- 数据库: SQLite (`app`) + PostgreSQL (`data_sync`)

### config-reference

配置项：

```python
# app/config.py
TUSHARE_TOKEN = "你的token"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"

# data_sync/config.py
db_host = "localhost"
db_port = 5432
db_name = "tushare_sync"
db_user = "wangjiangtao"
db_password = ""
```

可在.env文件中覆盖默认配置。
