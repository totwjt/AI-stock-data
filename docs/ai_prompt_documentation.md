# AI 提示词文档：Tushare API 文档 URL 检索

## 概述

本文档说明了 AI 助手在检索 Tushare API 文档 URL 时的优先级和处理流程。

## 检索流程

当用户询问某个 Tushare API 接口的文档时，AI 助手应按以下优先级检索：

### 1. 优先查看本地索引文件

**文件路径**：`docs/tushare_api_index.json`

**检索步骤**：
1. 读取 `tushare_api_index.json` 文件
2. 在 JSON 数组中查找匹配的 `api` 字段
3. 如果找到，返回对应的 `doc` URL

**索引文件格式**：
```json
[
  {
    "api": "stk_factor_pro",
    "name": "股票技术面因子",
    "doc": "https://tushare.pro/document/2?doc_id=296"
  }
]
```

### 2. 未找到处理

如果在本地索引中未找到该接口：

1. **记录缺失**：记录接口名称到待补充列表
2. **查询官方文档**：访问 Tushare 官方文档 https://tushare.pro/document/2
3. **补充索引**：将新接口信息添加到 `tushare_api_index.json`
4. **更新文档**：在 `SKILLS.md` 中更新常用接口文档列表

### 3. 索引补充格式

添加新接口时，使用以下格式：

```json
{
  "api": "接口名",
  "name": "接口中文名",
  "doc": "官方文档URL"
}
```

**示例**：
```json
{"api":"stk_factor_pro","name":"股票技术面因子","doc":"https://tushare.pro/document/2?doc_id=296"}
```

## 常用接口索引

当前 `tushare_api_index.json` 中包含的接口：

| API 名称 | 中文名称 | 文档 URL |
|---------|---------|---------|
| daily | 日线行情 | https://tushare.pro/document/2?doc_id=27 |
| weekly | 周线行情 | https://tushare.pro/document/2?doc_id=144 |
| monthly | 月线行情 | https://tushare.pro/document/2?doc_id=145 |
| stk_factor_pro | 股票技术面因子 | https://tushare.pro/document/2?doc_id=296 |
| daily_basic | 每日指标 | https://tushare.pro/document/2?doc_id=32 |
| stock_basic | 股票列表 | https://tushare.pro/document/2?doc_id=25 |
| trade_cal | 交易日历 | https://tushare.pro/document/2?doc_id=26 |
| adj_factor | 复权因子 | https://tushare.pro/document/2?doc_id=28 |

## AI 助手行为规范

### 当用户询问 API 文档时

1. **优先检索本地索引**：检查 `docs/tushare_api_index.json`
2. **返回文档 URL**：如果找到，直接返回官方文档链接
3. **提示补充索引**：如果未找到，提示用户该接口未在本地索引中，建议补充

### 当需要补充新接口时

1. **查询官方文档**：访问 https://tushare.pro/document/2
2. **获取文档 ID**：找到对应接口的 `doc_id`
3. **补充索引文件**：添加到 `tushare_api_index.json`
4. **更新技能文档**：在 `SKILLS.md` 中更新常用接口列表

## 示例对话

**用户**：stk_factor_pro 接口的文档在哪里？

**AI 助手**：
1. 首先检查 `docs/tushare_api_index.json`
2. 找到匹配项：`{"api":"stk_factor_pro","name":"股票技术面因子","doc":"https://tushare.pro/document/2?doc_id=296"}`
3. 返回：stk_factor_pro 接口的官方文档地址是 https://tushare.pro/document/2?doc_id=296

**用户**：new_api 接口的文档在哪里？

**AI 助手**：
1. 检查 `docs/tushare_api_index.json`
2. 未找到匹配项
3. 返回：new_api 接口未在本地索引中找到，请先补充到 `docs/tushare_api_index.json` 文件中，然后访问 https://tushare.pro/document/2 查询官方文档。

## 维护指南

### 定期更新索引

建议定期检查并更新 `tushare_api_index.json`：

1. 访问 Tushare 官方文档：https://tushare.pro/document/2
2. 查看新增接口
3. 补充到本地索引文件

### 索引文件位置

- **开发环境**：`/Users/wangjiangtao/Documents/AI/Ai-TuShare/docs/tushare_api_index.json`
- **相对路径**：`docs/tushare_api_index.json`

## 相关文件

- `docs/tushare_api_index.json`：Tushare API 接口索引
- `SKILLS.md`：项目技能配置，包含常用接口文档
- `static/ai-docs.json`：AI 可读的 OpenAPI 文档
- `docs/ai_prompt_documentation.md`：本文档
