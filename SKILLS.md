# Ai-TuShare 项目配置

## Skills

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
# 1. 进入项目目录
cd Ai-TuShare

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 启动服务
python -m app.main

# 4. 访问
- 看板: http://localhost:8000
- API测试: http://localhost:8000/api-tester
- Swagger文档: http://localhost:8000/docs
- AI文档: http://localhost:8000/ai-docs
- 积分统计: http://localhost:8000/api-stats
```

### tech-stack

技术栈：
- 后端: FastAPI + SQLAlchemy + aiosqlite
- 前端: 原生HTML/CSS/JavaScript
- 数据源: Tushare Pro
- 数据库: SQLite

### config-reference

配置项（app/config.py）：

```python
TUSHARE_TOKEN = "你的token"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"
```

可在.env文件中覆盖默认配置。
