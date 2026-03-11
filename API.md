# Ai-TuShare API Reference

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **响应格式**: JSON

## 通用响应格式

```json
{
  "code": 0,
  "data": [],
  "total": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 0成功, 非0失败 |
| data | array | 数据数组 |
| total | int | 总数 |

---

## Stock API (股票基础信息)

### 获取股票列表

**GET** `/api/v1/stock/list`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| exchange | string | N | 交易所: SSE/SZSE/BSE |
| list_status | string | N | L上市/D退市/P暂停，默认L |
| fields | string | N | 返回字段，逗号分隔 |

**示例:**
```bash
curl "http://localhost:8000/api/v1/stock/list?list_status=L&fields=ts_code,name,area,industry"
```

---

### 获取日线行情

**GET** `/api/v1/stock/daily`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ts_code | string | Y | 股票代码，如 000001.SZ |
| start_date | string | N | 开始日期 YYYYMMDD |
| end_date | string | N | 结束日期 YYYYMMDD |
| fields | string | N | 返回字段 |

**示例:**
```bash
curl "http://localhost:8000/api/v1/stock/daily?ts_code=000001.SZ&start_date=20250101&end_date=20250110"
```

---

### 获取交易日历

**GET** `/api/v1/stock/trade_cal`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| exchange | string | N | 交易所，默认SSE |
| start_date | string | N | 开始日期 YYYYMMDD |
| end_date | string | N | 结束日期 YYYYMMDD |

**示例:**
```bash
curl "http://localhost:8000/api/v1/stock/trade_cal?exchange=SSE&start_date=20250101&end_date=20250131"
```

---

## Indicators API (技术指标)

### 获取每日基本面指标

**GET** `/api/v1/indicators/daily_basic`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ts_code | string | N | 股票代码 |
| trade_date | string | N | 交易日期 YYYYMMDD |
| start_date | string | N | 开始日期 YYYYMMDD |
| end_date | string | N | 结束日期 YYYYMMDD |
| fields | string | N | 返回字段 |

**返回字段:**
- ts_code, trade_date, close
- turnover_rate, turnover_rate_f, volume_ratio
- pe, pe_ttm, pb, ps, ps_ttm
- dv_ratio, dv_ttm
- total_share, float_share, free_share
- total_mv, circ_mv

**示例:**
```bash
curl "http://localhost:8000/api/v1/indicators/daily_basic?ts_code=000001.SZ&start_date=20250101"
```

---

### 获取技术面因子

**GET** `/api/v1/indicators/factors`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ts_code | string | Y | 股票代码 |
| trade_date | string | N | 交易日期 |
| start_date | string | N | 开始日期 |
| end_date | string | N | 结束日期 |

**返回字段 (部分):**
- MACD: macd, macd_dif, macd_dea
- KDJ: kdj, kdj_k, kdj_d
- BOLL: boll_upper, boll_mid, boll_lower
- RSI: rsi_6, rsi_12, rsi_24
- CCI, ATR, DMI, BBI, OBV, etc.

**示例:**
```bash
curl "http://localhost:8000/api/v1/indicators/factors?ts_code=000001.SZ&start_date=20250101&end_date=20250110"
```

---

## Logs API (请求日志)

### 获取日志列表

**GET** `/api/v1/logs/list`

**参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | N | 页码，默认1 |
| page_size | int | N | 每页数量，默认20 |
| api_name | string | N | API名称筛选 |
| method | string | N | 请求方法筛选 |

---

### 获取统计信息

**GET** `/api/v1/logs/stats`

**返回:**
```json
{
  "code": 0,
  "data": {
    "total_requests": 100,
    "success_requests": 95,
    "failed_requests": 5,
    "success_rate": 95.0,
    "avg_response_time": 150.5,
    "top_apis": [...]
  }
}
```
