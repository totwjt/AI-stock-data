from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncpg
import asyncio
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

load_dotenv()

scheduler = AsyncIOScheduler()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "tushare_sync")
DB_USER = os.getenv("DB_USER", "wangjiangtao")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")


async def get_db_connection():
    """获取数据库连接"""
    return await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def create_app():
    """创建 Web 查询应用"""
    app = FastAPI(title="PostgreSQL Web Query", description="查询 PostgreSQL 数据库的 Web 界面")

    # 导入并包含同步API路由
    from .sync_api import router as sync_router, run_schedule_sync
    app.include_router(sync_router)

    # 添加定时任务：每天 16:30 执行
    async def schedule_job():
        await run_schedule_sync()

    scheduler.add_job(
        schedule_job,
        CronTrigger(hour=16, minute=30),
        id='daily_sync',
        replace_existing=True
    )

    @app.on_event("startup")
    async def startup_event():
        scheduler.start()

    @app.on_event("shutdown")
    async def shutdown_event():
        if scheduler.running:
            scheduler.shutdown(wait=False)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """首页 - 显示可用的表"""
        try:
            conn = await get_db_connection()
            # 查询所有表
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            await conn.close()

            # 获取可同步的表列表
            # 注意：同步任务名称与数据库表名的映射
            sync_task_to_table = {
                "stock_basic": "stock_basic",
                "trade_calendar": "trade_calendar",
                "daily": "stock_daily",
                "adj_factor": "stock_adj_factor",
                "daily_basic": "stock_daily_basic",
                "index_daily": "index_daily",
                "stk_factor_pro": "stock_factor_pro",
            }
            syncable_tables = list(sync_task_to_table.keys())
            table_to_sync_task = {v: k for k, v in sync_task_to_table.items()}

            # 核心表：固定排序在前
            priority_tables = ["stock_basic", "stock_daily", "stock_factor_pro"]

            # 其他表
            other_tables = [row for row in tables if row["table_name"] not in priority_tables]

            # 核心表详细数据
            priority_table_data = [
                {
                    "table_name": "stock_basic",
                    "sync_task_name": "stock_basic",
                    "description": "获取股票基础信息，包含股票代码、名称、行业等基本信息",
                    "record_count": "-",
                },
                {
                    "table_name": "stock_daily",
                    "sync_task_name": "daily",
                    "description": "获取股票每日行情数据，包含开盘价、收盘价、成交量等",
                    "record_count": "-",
                },
                {
                    "table_name": "stock_factor_pro",
                    "sync_task_name": "stk_factor_pro",
                    "description": "获取股票每日技术面因子数据，用于跟踪股票当前走势情况，包含MACD、KDJ、RSI等数十种技术指标",
                    "record_count": "-",
                },
            ]

            try:
                from .table_descriptions import get_all_table_descriptions
                descriptions = get_all_table_descriptions()
                desc_dict = {}
                for desc in descriptions:
                    desc_dict[desc.name] = {
                        "name": desc.name,
                        "description": desc.description,
                        "fields": [
                            {
                                "name": f.name,
                                "type": f.type,
                                "description": f.description,
                                "is_primary_key": f.is_primary_key
                            }
                            for f in desc.fields
                        ]
                    }
            except:
                desc_dict = {}

            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>PostgreSQL Web Query</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    table { border-collapse: collapse; width: 100%; max-width: 1400px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    tr:hover { background-color: #f5f5f5; }
                    a { color: #0066cc; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    .sync-btn {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        cursor: pointer;
                        border-radius: 3px;
                        font-size: 12px;
                    }
                    .sync-btn:hover { background-color: #45a049; }
                    .sync-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
                    .resync-btn {
                        background-color: #2196F3;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        cursor: pointer;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 5px;
                    }
                    .resync-btn:hover { background-color: #1976D2; }
                    .batch-sync-btn {
                        background-color: #9C27B0;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        cursor: pointer;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 5px;
                    }
                    .batch-sync-btn:hover { background-color: #7B1FA2; }
                    .batch-sync-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
                    .stop-btn {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        cursor: pointer;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 5px;
                    }
                    .stop-btn:hover { background-color: #d32f2f; }
                    .stop-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
                    .verify-btn {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        cursor: pointer;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-left: 5px;
                    }
                    .verify-btn:hover { background-color: #F57C00; }
                    .verify-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
                    .verified-badge {
                        background-color: #4CAF50;
                        color: white;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-size: 11px;
                        margin-left: 5px;
                    }
                    .incomplete-badge {
                        background-color: #f44336;
                        color: white;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-size: 11px;
                        margin-left: 5px;
                    }
                    .status-pending { color: #ff9800; }
                    .status-running { color: #2196F3; }
                    .status-completed { color: #4CAF50; }
                    .status-failed { color: #f44336; }
                    .desc { color: #666; font-size: 12px; }
                    .schedule-section {
                        background-color: #f5f5f5;
                        padding: 10px 15px;
                        border-radius: 5px;
                        margin-bottom: 15px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }
                    .schedule-title { font-weight: bold; color: #333; }
                    .schedule-status { color: #666; margin-left: 10px; }
                    .switch {
                        position: relative;
                        display: inline-block;
                        width: 40px;
                        height: 22px;
                    }
                    .switch input { opacity: 0; width: 0; height: 0; }
                    .slider {
                        position: absolute;
                        cursor: pointer;
                        top: 0; left: 0; right: 0; bottom: 0;
                        background-color: #ccc;
                        transition: .3s;
                        border-radius: 22px;
                    }
                    .slider:before {
                        position: absolute;
                        content: "";
                        height: 16px;
                        width: 16px;
                        left: 3px;
                        bottom: 3px;
                        background-color: white;
                        transition: .3s;
                        border-radius: 50%;
                    }
                    input:checked + .slider { background-color: #4CAF50; }
                    input:checked + .slider:before { transform: translateX(18px); }
                    .run-now-btn {
                        background-color: #673AB7;
                        color: white;
                        border: none;
                        padding: 6px 16px;
                        cursor: pointer;
                        border-radius: 4px;
                        font-size: 13px;
                        margin-left: 10px;
                    }
                    .run-now-btn:hover { background-color: #5E35B1; }
                    .run-now-btn:disabled { background-color: #cccccc; cursor: not-allowed; }
                    .group-header { background-color: #e3f2fd; font-weight: bold; }
                    .priority-table { background-color: #fffde7; }
                </style>
                <script>
                    async function startSync(tableName) {
                        const btn = document.getElementById('sync-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        btn.disabled = true;
                        btn.textContent = '同步中...';
                        status.textContent = '同步中';
                        status.className = 'status-running';

                        try {
                            const response = await fetch('/api/sync/' + tableName, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'}
                            });

                            const data = await response.json();

                            if (response.ok) {
                                // 轮询查询状态
                                pollStatus(tableName, data.task_id);
                            } else {
                                status.textContent = '失败: ' + data.detail;
                                status.className = 'status-failed';
                                btn.disabled = false;
                                btn.textContent = '同步';
                            }
                        } catch (error) {
                            status.textContent = '请求失败: ' + error;
                            status.className = 'status-failed';
                            btn.disabled = false;
                            btn.textContent = '同步';
                        }
                    }

                    async function pollStatus(tableName, taskId) {
                        const syncBtn = document.getElementById('sync-' + tableName);
                        const stopBtn = document.getElementById('stop-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        // 存储任务ID到停止按钮
                        if (stopBtn) {
                            stopBtn.setAttribute('data-task-id', taskId);
                            stopBtn.disabled = false;
                        }

                        const interval = setInterval(async () => {
                            try {
                                const controller = new AbortController();
                                const timeoutId = setTimeout(() => controller.abort(), 5000);
                                const response = await fetch('/api/sync/status/' + taskId, {signal: controller.signal});
                                clearTimeout(timeoutId);
                                const data = await response.json();

                                if (data.status === 'completed') {
                                    status.textContent = '完成 (' + data.records_count + ' 条)';
                                    status.className = 'status-completed';
                                    syncBtn.disabled = false;
                                    syncBtn.textContent = '同步';
                                    if (stopBtn) {
                                        stopBtn.disabled = true;
                                        stopBtn.setAttribute('data-task-id', '');
                                    }
                                    clearInterval(interval);
                                } else if (data.status === 'failed') {
                                    status.textContent = '失败: ' + data.error_message;
                                    status.className = 'status-failed';
                                    syncBtn.disabled = false;
                                    syncBtn.textContent = '同步';
                                    if (stopBtn) {
                                        stopBtn.disabled = true;
                                        stopBtn.setAttribute('data-task-id', '');
                                    }
                                    clearInterval(interval);
                                } else if (data.status === 'running') {
                                    status.textContent = '同步中... ' + data.records_count + ' 条';
                                } else if (data.status === 'pending') {
                                    status.textContent = '等待中...';
                                } else if (data.status === 'stopped') {
                                    status.textContent = '已停止';
                                    status.className = 'status-failed';
                                    syncBtn.disabled = false;
                                    syncBtn.textContent = '同步';
                                    if (stopBtn) {
                                        stopBtn.disabled = true;
                                        stopBtn.setAttribute('data-task-id', '');
                                    }
                                    clearInterval(interval);
                                }
                            } catch (error) {
                                if (error.name !== 'AbortError') {
                                    console.log('轮询错误:', error);
                                }
                            }
                        }, 2000);
                    }

                    async function resyncTable(tableName) {
                        const btn = document.getElementById('resync-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        btn.disabled = true;
                        btn.textContent = '重新同步中...';
                        status.textContent = '重新同步中';
                        status.className = 'status-running';

                        try {
                            const response = await fetch('/api/sync/' + tableName, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({sync_type: 'incremental'})
                            });

                            const data = await response.json();

                            if (response.ok) {
                                pollStatus(tableName, data.task_id);
                            } else {
                                status.textContent = '失败: ' + data.detail;
                                status.className = 'status-failed';
                                btn.disabled = false;
                                btn.textContent = '重新同步';
                            }
                        } catch (error) {
                            status.textContent = '请求失败: ' + error;
                            status.className = 'status-failed';
                            btn.disabled = false;
                            btn.textContent = '重新同步';
                        }
                    }

                    async function batchSync(tableName) {
                        const btn = document.getElementById('batch-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        btn.disabled = true;
                        btn.textContent = '批量同步中...';
                        status.textContent = '批量同步中';
                        status.className = 'status-running';

                        try {
                            const response = await fetch('/api/sync/' + tableName, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({sync_type: 'history_by_year'})
                            });

                            const data = await response.json();

                            if (response.ok) {
                                pollStatus(tableName, data.task_id);
                            } else {
                                status.textContent = '失败: ' + data.detail;
                                status.className = 'status-failed';
                                btn.disabled = false;
                                btn.textContent = '批量同步';
                            }
                        } catch (error) {
                            status.textContent = '请求失败: ' + error;
                            status.className = 'status-failed';
                            btn.disabled = false;
                            btn.textContent = '批量同步';
                        }
                    }

                    async function forceSync(tableName) {
                        const btn = document.getElementById('force-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        if (!confirm('强制重新同步会覆盖已有数据，确定要继续吗？')) {
                            return;
                        }

                        btn.disabled = true;
                        btn.textContent = '强制同步中...';
                        status.textContent = '强制同步中';
                        status.className = 'status-running';

                        try {
                            const response = await fetch('/api/sync/' + tableName, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({sync_type: 'force'})
                            });

                            const data = await response.json();

                            if (response.ok) {
                                pollStatus(tableName, data.task_id);
                            } else {
                                status.textContent = '失败: ' + data.detail;
                                status.className = 'status-failed';
                                btn.disabled = false;
                                btn.textContent = '强制重同步';
                            }
                        } catch (error) {
                            status.textContent = '请求失败: ' + error;
                            status.className = 'status-failed';
                            btn.disabled = false;
                            btn.textContent = '强制重同步';
                        }
                    }

                    async function stopSync(tableName) {
                        const stopBtn = document.getElementById('stop-' + tableName);
                        const status = document.getElementById('status-' + tableName);
                        const syncBtn = document.getElementById('sync-' + tableName);

                        stopBtn.disabled = true;
                        stopBtn.textContent = '停止中...';
                        status.textContent = '停止中';

                        try {
                            // 获取当前任务ID（从状态元素的data-task-id属性）
                            const taskId = stopBtn.getAttribute('data-task-id');
                            if (!taskId) {
                                status.textContent = '无运行中的任务';
                                stopBtn.disabled = false;
                                stopBtn.textContent = '停止';
                                return;
                            }

                            const response = await fetch('/api/sync/stop/' + taskId, {
                                method: 'POST'
                            });

                            const data = await response.json();

                            if (response.ok) {
                                status.textContent = '已停止';
                                status.className = 'status-failed';
                                syncBtn.disabled = false;
                                syncBtn.textContent = '同步';
                            } else {
                                status.textContent = '停止失败: ' + data.detail;
                                syncBtn.disabled = false;
                                syncBtn.textContent = '同步';
                            }
                        } catch (error) {
                            status.textContent = '停止请求失败: ' + error;
                            syncBtn.disabled = false;
                            syncBtn.textContent = '同步';
                        } finally {
                            stopBtn.disabled = false;
                            stopBtn.textContent = '停止';
                        }
                    }

                    function showTableDesc(tableName) {
                        const descDiv = document.getElementById('desc-' + tableName);
                        if (descDiv.style.display === 'none') {
                            descDiv.style.display = 'block';
                        } else {
                            descDiv.style.display = 'none';
                        }
                    }

                    function toggleSchedule() {
                        const enabled = document.getElementById('schedule-enable').checked;
                        const status = document.getElementById('schedule-status');

                        fetch('/api/sync/schedule/toggle', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ enabled: enabled })
                        })
                        .then(r => r.json())
                        .then(data => {
                            status.textContent = enabled ? '✓ 定时同步已启用' : '✗ 定时同步已禁用';
                        })
                        .catch(err => {
                            status.textContent = '✗ 操作失败';
                        });
                    }

                    async function startVerify(tableName) {
                        const btn = document.getElementById('verify-' + tableName);
                        const status = document.getElementById('status-' + tableName);

                        btn.disabled = true;
                        btn.textContent = '验证中...';
                        status.textContent = '验证中...';
                        status.className = 'status-running';

                        try {
                            const response = await fetch('/api/sync/verify/' + tableName, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'}
                            });

                            const data = await response.json();

                            if (response.ok) {
                                pollStatus(tableName, data.task_id);
                                // 验证完成后刷新页面显示验证状态
                                setTimeout(() => location.reload(), 3000);
                            } else {
                                status.textContent = '验证失败: ' + data.detail;
                                status.className = 'status-failed';
                                btn.disabled = false;
                                btn.textContent = '验证';
                            }
                        } catch (error) {
                            status.textContent = '验证请求失败: ' + error;
                            status.className = 'status-failed';
                            btn.disabled = false;
                            btn.textContent = '验证';
                        }
                    }

                    async function loadVerifyStatus(tableName) {
                        try {
                            const response = await fetch('/api/sync/verify/status/' + tableName);
                            if (response.ok) {
                                const data = await response.json();
                                if (data.verified_years.length > 0) {
                                    return '已验证: ' + data.verified_years.join(', ');
                                }
                            }
                            return null;
                        } catch (error) {
                            return null;
                        }
                    }
                </script>
            </head>
            <body>
                <h1>PostgreSQL 数据库查询</h1>
                <div class="schedule-section">
                    <label class="switch">
                        <input type="checkbox" id="schedule-enable" checked onchange="toggleSchedule()">
                        <span class="slider"></span>
                    </label>
                    <span class="schedule-title">16:30 定时同步 (stock_basic, stock_daily, stk_factor_pro)</span>
                    <span id="schedule-status" class="schedule-status"></span>
                </div>

                <h3 style="margin-top: 20px;">核心数据表</h3>
                <table>
                    <tr>
                        <th>表名</th>
                        <th>描述</th>
                        <th>操作</th>
                        <th>同步</th>
                        <th>状态</th>
                    </tr>
            """

            # 渲染核心表（带字段详情）
            for item in priority_table_data:
                sync_task_name = item["sync_task_name"]

                # 获取字段详情
                desc_text = item["description"]
                desc_detail = ""
                if sync_task_name in desc_dict:
                    desc = desc_dict[sync_task_name]
                    fields_html = "<br>".join([
                        f"{f['name']} ({f['type']}): {f['description']}"
                        for f in desc.get("fields", [])[:5]
                    ])
                    if len(desc.get("fields", [])) > 5:
                        fields_html += f"<br>... 还有 {len(desc.get('fields', [])) - 5} 个字段"
                    desc_detail = f'<div id="desc-{sync_task_name}" class="desc" style="display:none;">{fields_html}</div>'

                sync_btn = f'<button id="sync-{sync_task_name}" class="sync-btn" onclick="startSync(\'{sync_task_name}\')">同步</button>'
                stop_btn = f'<button id="stop-{sync_task_name}" class="stop-btn" onclick="stopSync(\'{sync_task_name}\')" disabled>停止</button>'
                verify_btn = f'<button id="verify-{sync_task_name}" class="verify-btn" onclick="startVerify(\'{sync_task_name}\')">验证</button>'
                status_id = f"status-{sync_task_name}"

                html += f"""
                    <tr class="priority-row">
                        <td>{item["table_name"]}</td>
                        <td>
                            {desc_text}
                            {desc_detail}
                            {f'<br><a href="javascript:void(0)" onclick="showTableDesc(\'{sync_task_name}\')">查看详情</a>' if desc_detail else ''}
                        </td>
                        <td>
                            <a href="/table/{item["table_name"]}">浏览数据</a> |
                            <a href="/schema/{item["table_name"]}">查看结构</a>
                        </td>
                        <td>{sync_btn}{verify_btn}{stop_btn}</td>
                        <td id="{status_id}">-</td>
                    </tr>
                """

            # 其他表
            html += """
                </table>

                <h3 style="margin-top: 30px;">其他数据表</h3>
                <table>
                    <tr>
                        <th>表名</th>
                        <th>描述</th>
                        <th>操作</th>
                        <th>同步</th>
                        <th>状态</th>
                    </tr>
            """

            for row in other_tables:
                table_name = row["table_name"]

                # 获取对应的同步任务名称
                sync_task_name = table_to_sync_task.get(table_name)
                is_syncable = sync_task_name is not None

                # 同步按钮使用同步任务名称
                if is_syncable:
                    sync_btn = f'<button id="sync-{sync_task_name}" class="sync-btn" onclick="startSync(\'{sync_task_name}\')">同步</button>'
                    stop_btn = f'<button id="stop-{sync_task_name}" class="stop-btn" onclick="stopSync(\'{sync_task_name}\')" disabled>停止</button>'
                    status_id = f"status-{sync_task_name}"
                    if sync_task_name == "daily":
                        verify_btn = f'<button id="verify-{sync_task_name}" class="verify-btn" onclick="startVerify(\'{sync_task_name}\')">验证</button>'
                    else:
                        verify_btn = ""
                else:
                    sync_btn = 'N/A'
                    stop_btn = ''
                    verify_btn = ''
                    status_id = f"status-{table_name}"

                # 获取表描述（使用同步任务名称）
                desc_text = "-"
                desc_detail = ""
                if sync_task_name and sync_task_name in desc_dict:
                    desc = desc_dict[sync_task_name]
                    desc_text = desc.get("description", "-")
                    # 构建字段列表
                    fields_html = "<br>".join([
                        f"{f['name']} ({f['type']}): {f['description']}"
                        for f in desc.get("fields", [])[:5]  # 只显示前5个字段
                    ])
                    if len(desc.get("fields", [])) > 5:
                        fields_html += f"<br>... 还有 {len(desc.get('fields', [])) - 5} 个字段"
                    desc_detail = f'<div id="desc-{sync_task_name}" class="desc" style="display:none;">{fields_html}</div>'

                resync_btn = ""
                if sync_task_name in ["stock_basic", "trade_calendar"]:
                    resync_btn = f'<button id="resync-{sync_task_name}" class="resync-btn" onclick="resyncTable(\'{sync_task_name}\')">重新同步</button>'

                html += f"""
                    <tr>
                        <td>{table_name}</td>
                        <td>
                            {desc_text}
                            {desc_detail}
                            {f'<a href="javascript:void(0)" onclick="showTableDesc(\'{sync_task_name}\')">查看详情</a>' if sync_task_name else ''}
                        </td>
                        <td>
                            <a href="/table/{table_name}">浏览数据</a> |
                            <a href="/schema/{table_name}">查看结构</a>
                        </td>
                        <td>{sync_btn}{verify_btn}{resync_btn}{stop_btn}</td>
                        <td id="{status_id}">-</td>
                    </tr>
                """

            html += """
                </table>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

        except Exception as e:
            return HTMLResponse(content=f"<h1>错误</h1><p>无法连接数据库: {str(e)}</p>", status_code=500)

    @app.get("/api/query/stock_factor_pro")
    async def query_stock_factor_pro(
        ts_code: Optional[str] = Query(None, description="股票代码，支持模糊匹配"),
        trade_date: Optional[str] = Query(None, description="交易日期 (YYYYMMDD)"),
        start_date: Optional[str] = Query(None, description="开始日期 (YYYYMMDD)"),
        end_date: Optional[str] = Query(None, description="结束日期 (YYYYMMDD)"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页条数")
    ):
        try:
            conn = await get_db_connection()

            conditions = []
            params = []
            param_idx = 1

            if ts_code:
                conditions.append(f"ts_code ILIKE ${param_idx}")
                params.append(f"%{ts_code}%")
                param_idx += 1

            if trade_date:
                conditions.append(f"trade_date = ${param_idx}")
                params.append(trade_date)
                param_idx += 1

            if start_date:
                conditions.append(f"trade_date >= ${param_idx}")
                params.append(start_date)
                param_idx += 1

            if end_date:
                conditions.append(f"trade_date <= ${param_idx}")
                params.append(end_date)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            count_query = f"""
                SELECT COUNT(*) FROM stock_factor_pro WHERE {where_clause}
            """
            total_count = await conn.fetchval(count_query, *params)

            offset = (page - 1) * page_size
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

            data_query = f"""
                SELECT
                    ts_code,
                    trade_date,
                    close,
                    pct_chg,
                    turnover_rate,
                    pe_ttm,
                    pb,
                    macd_dif_bfq,
                    macd_dea_bfq,
                    macd_bfq,
                    kdj_k_bfq,
                    kdj_d_bfq,
                    kdj_bfq,
                    rsi_bfq_6,
                    rsi_bfq_12,
                    rsi_bfq_24,
                    boll_upper_bfq,
                    boll_mid_bfq,
                    boll_lower_bfq,
                    cci_bfq,
                    atr_bfq,
                    volume_ratio
                FROM stock_factor_pro
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code ASC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            params.extend([page_size, offset])

            data = await conn.fetch(data_query, *params)

            stock_codes_query = """
                SELECT DISTINCT ts_code FROM stock_factor_pro ORDER BY ts_code LIMIT 100
            """
            stock_codes = await conn.fetch(stock_codes_query)

            await conn.close()

            return JSONResponse({
                "code": 0,
                "message": "success",
                "data": {
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "records": [dict(row) for row in data],
                    "stock_codes": [row["ts_code"] for row in stock_codes]
                }
            })

        except Exception as e:
            return JSONResponse({
                "code": 1,
                "message": str(e),
                "data": None
            }, status_code=500)

    @app.get("/table/stock_factor_pro")
    async def browse_stock_factor_pro_page():
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>股票技术因子查询</title>
            <meta charset="utf-8">
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    background-color: #f5f7fa;
                    padding: 20px;
                    min-height: 100vh;
                }
                .container { max-width: 100vw; margin: 0 auto; }
                .nav {
                    background: white;
                    padding: 15px 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                }
                .nav a { color: #0066cc; text-decoration: none; margin-right: 20px; }
                .nav a:hover { text-decoration: underline; }
                .search-panel {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                }
                .search-title { font-size: 16px; font-weight: 600; color: #333; margin-bottom: 15px; }
                .search-form {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    align-items: end;
                }
                .form-group { display: flex; flex-direction: column; }
                .form-group label { font-size: 13px; color: #666; margin-bottom: 6px; }
                .form-group input {
                    padding: 10px 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                    transition: border-color 0.2s;
                }
                .form-group input:focus { outline: none; border-color: #0066cc; }
                .btn-group { display: flex; gap: 10px; }
                .btn {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .btn-primary { background: #0066cc; color: white; }
                .btn-primary:hover { background: #0052a3; }
                .btn-secondary { background: #f0f0f0; color: #666; }
                .btn-secondary:hover { background: #e0e0e0; }
                .data-panel {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                    overflow: hidden;
                }
                .data-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 20px;
                    border-bottom: 1px solid #eee;
                }
                .data-title { font-size: 16px; font-weight: 600; color: #333; }
                .data-summary { font-size: 13px; color: #666; }
                .table-container { overflow-x: auto; }
                table { width: 100%; border-collapse: collapse; font-size: 13px; }
                th {
                    background: #f8f9fa;
                    padding: 12px 10px;
                    text-align: left;
                    font-weight: 600;
                    color: #333;
                    border-bottom: 2px solid #eee;
                    white-space: nowrap;
                    position: sticky;
                    top: 0;
                }
                td { padding: 10px; border-bottom: 1px solid #eee; color: #333; }
                tr:hover { background-color: #f8f9fa; }
                .stock-code { color: #0066cc; font-weight: 500; }
                .trade-date { color: #666; }
                .positive { color: #f44336; }
                .negative { color: #4caf50; }
                .pagination {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 20px;
                    border-top: 1px solid #eee;
                }
                .pagination-info { font-size: 13px; color: #666; }
                .pagination-controls { display: flex; gap: 5px; align-items: center; }
                .page-btn {
                    padding: 8px 12px;
                    border: 1px solid #ddd;
                    background: white;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                    color: #333;
                    transition: all 0.2s;
                }
                .page-btn:hover:not(:disabled) { border-color: #0066cc; color: #0066cc; }
                .page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
                .page-btn.active { background: #0066cc; color: white; border-color: #0066cc; }
                .page-input { width: 60px; padding: 8px; border: 1px solid #ddd; border-radius: 4px; text-align: center; }
                .loading { text-align: center; padding: 40px; color: #666; }
                .no-data { text-align: center; padding: 60px 20px; color: #999; }
                .toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 12px 20px;
                    background: #333;
                    color: white;
                    border-radius: 6px;
                    font-size: 14px;
                    z-index: 1000;
                    display: none;
                }
                .toast.error { background: #f44336; }
                .toast.success { background: #4caf50; }
                .num { font-family: "SF Mono", Monaco, monospace; text-align: right; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav">
                    <a href="/">← 返回首页</a>
                    <a href="/schema/stock_factor_pro">查看表结构</a>
                </div>

                <div class="search-panel">
                    <div class="search-title">条件筛选</div>
                    <div class="search-form">
                        <div class="form-group">
                            <label>股票代码</label>
                            <input type="text" id="ts_code" placeholder="如: 000001" list="stock-codes">
                            <datalist id="stock-codes"></datalist>
                        </div>
                        <div class="form-group">
                            <label>交易日期</label>
                            <input type="text" id="trade_date" placeholder="YYYYMMDD 如: 20250320">
                        </div>
                        <div class="form-group">
                            <label>开始日期</label>
                            <input type="text" id="start_date" placeholder="YYYYMMDD 如: 20250101">
                        </div>
                        <div class="form-group">
                            <label>结束日期</label>
                            <input type="text" id="end_date" placeholder="YYYYMMDD 如: 20250320">
                        </div>
                        <div class="btn-group">
                            <button class="btn btn-primary" onclick="search(1)">查询</button>
                            <button class="btn btn-secondary" onclick="reset()">重置</button>
                        </div>
                    </div>
                </div>

                <div class="data-panel">
                    <div class="data-header">
                        <span class="data-title">查询结果</span>
                        <span class="data-summary" id="data-summary">共 0 条记录</span>
                    </div>
                    <div id="data-container">
                        <div class="no-data">请输入查询条件并点击"查询"按钮</div>
                    </div>
                    <div class="pagination" id="pagination" style="display: none;">
                        <div class="pagination-info" id="pagination-info"></div>
                        <div class="pagination-controls">
                            <button class="page-btn" id="prev-btn" onclick="prevPage()">上一页</button>
                            <span id="page-numbers"></span>
                            <button class="page-btn" id="next-btn" onclick="nextPage()">下一页</button>
                            <span style="margin-left: 10px;">跳至</span>
                            <input type="number" class="page-input" id="page-input" min="1" onchange="goToPage(this.value)">
                            <span>页</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="toast" id="toast"></div>

            <script>
                let currentPage = 1, totalPages = 1, totalCount = 0;

                async function init() {
                    try {
                        const response = await fetch('/api/query/stock_factor_pro?page=1&page_size=1');
                        const result = await response.json();
                        if (result.code === 0 && result.data.stock_codes) {
                            const datalist = document.getElementById('stock-codes');
                            result.data.stock_codes.forEach(code => {
                                const option = document.createElement('option');
                                option.value = code;
                                datalist.appendChild(option);
                            });
                        }
                    } catch (e) { console.error('初始化失败:', e); }
                }

                function showToast(message, type = 'info') {
                    const toast = document.getElementById('toast');
                    toast.textContent = message;
                    toast.className = 'toast ' + type;
                    toast.style.display = 'block';
                    setTimeout(() => toast.style.display = 'none', 3000);
                }

                function formatNum(val, decimals = 2) {
                    if (val === null || val === undefined) return '-';
                    const num = parseFloat(val);
                    if (isNaN(num)) return '-';
                    return num.toFixed(decimals);
                }

                function formatPct(val) {
                    if (val === null || val === undefined) return '-';
                    const num = parseFloat(val);
                    if (isNaN(num)) return '-';
                    const cls = num > 0 ? 'positive' : (num < 0 ? 'negative' : '');
                    return '<span class="' + cls + '">' + formatNum(num) + '%</span>';
                }

                async function search(page = 1) {
                    const ts_code = document.getElementById('ts_code').value.trim();
                    const trade_date = document.getElementById('trade_date').value.trim();
                    const start_date = document.getElementById('start_date').value.trim();
                    const end_date = document.getElementById('end_date').value.trim();

                    currentPage = page;
                    const params = new URLSearchParams({ page: page, page_size: 10 });
                    if (ts_code) params.append('ts_code', ts_code);
                    if (trade_date) params.append('trade_date', trade_date);
                    if (start_date) params.append('start_date', start_date);
                    if (end_date) params.append('end_date', end_date);

                    const container = document.getElementById('data-container');
                    container.innerHTML = '<div class="loading">加载中...</div>';

                    try {
                        const response = await fetch('/api/query/stock_factor_pro?' + params.toString());
                        const result = await response.json();

                        if (result.code === 0) {
                            const data = result.data;
                            totalCount = data.total;
                            totalPages = data.total_pages;
                            currentPage = data.page;
                            renderTable(data.records);
                            renderPagination();
                            document.getElementById('data-summary').textContent = '共 ' + totalCount.toLocaleString() + ' 条记录';
                        } else {
                            container.innerHTML = '<div class="no-data">查询失败: ' + result.message + '</div>';
                            showToast(result.message, 'error');
                        }
                    } catch (e) {
                        container.innerHTML = '<div class="no-data">请求失败: ' + e.message + '</div>';
                        showToast('网络请求失败', 'error');
                    }
                }

                function renderTable(records) {
                    const container = document.getElementById('data-container');
                    if (!records || records.length === 0) {
                        container.innerHTML = '<div class="no-data">未找到符合条件的数据</div>';
                        document.getElementById('pagination').style.display = 'none';
                        return;
                    }

                    const fields = [
                        {key: 'ts_code', label: '股票代码', format: 'code'},
                        {key: 'trade_date', label: '交易日期', format: 'date'},
                        {key: 'close', label: '收盘价', format: 'num'},
                        {key: 'pct_chg', label: '涨跌幅', format: 'pct'},
                        {key: 'turnover_rate', label: '换手率%', format: 'num'},
                        {key: 'volume_ratio', label: '量比', format: 'num'},
                        {key: 'pe_ttm', label: 'PE(TTM)', format: 'num'},
                        {key: 'pb', label: 'PB', format: 'num'},
                        {key: 'macd_dif_bfq', label: 'MACD-DIF', format: 'num'},
                        {key: 'macd_dea_bfq', label: 'MACD-DEA', format: 'num'},
                        {key: 'macd_bfq', label: 'MACD', format: 'num'},
                        {key: 'kdj_k_bfq', label: 'KDJ-K', format: 'num'},
                        {key: 'kdj_d_bfq', label: 'KDJ-D', format: 'num'},
                        {key: 'kdj_bfq', label: 'KDJ-J', format: 'num'},
                        {key: 'rsi_bfq_6', label: 'RSI-6', format: 'num'},
                        {key: 'rsi_bfq_12', label: 'RSI-12', format: 'num'},
                        {key: 'rsi_bfq_24', label: 'RSI-24', format: 'num'},
                        {key: 'boll_upper_bfq', label: '布林上轨', format: 'num'},
                        {key: 'boll_mid_bfq', label: '布林中轨', format: 'num'},
                        {key: 'boll_lower_bfq', label: '布林下轨', format: 'num'},
                        {key: 'cci_bfq', label: 'CCI', format: 'num'},
                        {key: 'atr_bfq', label: 'ATR', format: 'num'},
                    ];

                    let html = '<div class="table-container"><table><thead><tr>';
                    fields.forEach(f => { html += '<th>' + f.label + '</th>'; });
                    html += '</tr></thead><tbody>';

                    records.forEach(row => {
                        html += '<tr>';
                        fields.forEach(f => {
                            let val = row[f.key];
                            let content = val;
                            if (f.format === 'code') content = '<span class="stock-code">' + val + '</span>';
                            else if (f.format === 'date') {
                                if (val) {
                                    val = val.toString();
                                    content = '<span class="trade-date">' + val.slice(0,4) + '-' + val.slice(4,6) + '-' + val.slice(6,8) + '</span>';
                                }
                            } else if (f.format === 'pct') content = formatPct(val);
                            else if (f.format === 'num') content = '<span class="num">' + formatNum(val) + '</span>';
                            html += '<td>' + content + '</td>';
                        });
                        html += '</tr>';
                    });

                    html += '</tbody></table></div>';
                    container.innerHTML = html;
                }

                function renderPagination() {
                    const pagination = document.getElementById('pagination');
                    pagination.style.display = 'flex';
                    document.getElementById('pagination-info').textContent = '第 ' + currentPage + ' / ' + totalPages + ' 页';
                    document.getElementById('prev-btn').disabled = currentPage <= 1;
                    document.getElementById('next-btn').disabled = currentPage >= totalPages;
                    document.getElementById('page-input').value = currentPage;
                    document.getElementById('page-input').max = totalPages;

                    let pagesHtml = '';
                    const maxButtons = 5;
                    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
                    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
                    if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);
                    for (let i = startPage; i <= endPage; i++) {
                        pagesHtml += '<button class="page-btn ' + (i === currentPage ? 'active' : '') + '" onclick="search(' + i + ')">' + i + '</button>';
                    }
                    document.getElementById('page-numbers').innerHTML = pagesHtml;
                }

                function prevPage() { if (currentPage > 1) search(currentPage - 1); }
                function nextPage() { if (currentPage < totalPages) search(currentPage + 1); }
                function goToPage(page) {
                    const pageNum = parseInt(page);
                    if (pageNum >= 1 && pageNum <= totalPages) search(pageNum);
                }

                function reset() {
                    document.getElementById('ts_code').value = '';
                    document.getElementById('trade_date').value = '';
                    document.getElementById('start_date').value = '';
                    document.getElementById('end_date').value = '';
                    document.getElementById('data-container').innerHTML = '<div class="no-data">请输入查询条件并点击"查询"按钮</div>';
                    document.getElementById('pagination').style.display = 'none';
                    document.getElementById('data-summary').textContent = '共 0 条记录';
                }

                init();
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

    @app.get("/table/{table_name}")
    async def browse_table(table_name: str, limit: int = 100):
        """浏览表数据"""
        try:
            conn = await get_db_connection()

            # 检查表是否存在
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """, table_name)

            if not table_exists:
                await conn.close()
                raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在")

            # 获取列信息
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1
                ORDER BY ordinal_position
            """, table_name)

            # 获取数据
            data = await conn.fetch(f"SELECT * FROM {table_name} LIMIT $1", limit)

            # stock_daily 表添加数据统计
            stats_html = ""
            if table_name == "stock_daily":
                # 按年份统计所有数据
                stats = await conn.fetch("""
                    SELECT
                        LEFT(trade_date, 4) as year,
                        COUNT(DISTINCT trade_date) as dates,
                        COUNT(DISTINCT ts_code) as stocks,
                        COUNT(*) as records
                    FROM stock_daily
                    GROUP BY LEFT(trade_date, 4)
                    ORDER BY year DESC
                """)
                if stats:
                    stats_html = """
                    <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px;">
                        <h3 style="margin-top: 0;">数据统计（从近到远）</h3>
                        <table style="width: auto; border-collapse: collapse;">
                            <tr style="background-color: #e0e0e0;">
                                <th style="padding: 8px; border: 1px solid #ddd;">年份</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">交易日数</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">股票数</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">总记录数</th>
                            </tr>
                    """
                    for s in stats:
                        stats_html += f"""
                            <tr>
                                <td style="padding: 8px; border: 1px solid #ddd;">{s['year']}</td>
                                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{s['dates']}</td>
                                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{s['stocks']}</td>
                                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{s['records']:,}</td>
                            </tr>
                        """
                    stats_html += "</table></div>"

            await conn.close()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>表 {table_name} 数据</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    .nav {{ margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="nav">
                    <a href="/">← 返回首页</a> |
                    <a href="/schema/{table_name}">查看结构</a>
                </div>
                <h1>表 {table_name} 数据 (最多 {limit} 条)</h1>
                {stats_html}
                <table>
                    <tr>
            """

            # 表头
            for col in columns:
                html += f"<th>{col['column_name']}<br><small>{col['data_type']}</small></th>"
            html += "</tr>"

            # 数据行
            for row in data:
                html += "<tr>"
                for col in columns:
                    value = row.get(col['column_name'], '')
                    html += f"<td>{value}</td>"
                html += "</tr>"

            html += """
                </table>
                <p>显示最多 100 条数据</p>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

        except Exception as e:
            return HTMLResponse(content=f"<h1>错误</h1><p>查询失败: {str(e)}</p>", status_code=500)

    @app.get("/schema/{table_name}")
    async def show_schema(table_name: str):
        """显示表结构"""
        try:
            conn = await get_db_connection()

            # 检查表是否存在
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """, table_name)

            if not table_exists:
                await conn.close()
                raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在")

            # 获取列信息
            columns = await conn.fetch("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1
                ORDER BY ordinal_position
            """, table_name)

            # 获取主键信息
            primary_keys = await conn.fetch("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                    AND tc.table_name = $1
                    AND tc.constraint_type = 'PRIMARY KEY'
            """, table_name)

            pk_columns = [row["column_name"] for row in primary_keys]

            # 获取行数
            row_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

            await conn.close()

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>表 {table_name} 结构</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; max-width: 800px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    .nav {{ margin-bottom: 20px; }}
                    .info {{ background-color: #f0f8ff; padding: 10px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="nav">
                    <a href="/">← 返回首页</a> |
                    <a href="/table/{table_name}">浏览数据</a>
                </div>
                <h1>表 {table_name} 结构</h1>
                <div class="info">
                    <p><strong>行数:</strong> {row_count:,}</p>
                    <p><strong>主键:</strong> {', '.join(pk_columns) if pk_columns else '无'}</p>
                </div>
                <table>
                    <tr>
                        <th>列名</th>
                        <th>数据类型</th>
                        <th>可为空</th>
                        <th>默认值</th>
                        <th>是否主键</th>
                    </tr>
            """

            for col in columns:
                is_pk = "✓" if col["column_name"] in pk_columns else ""
                html += f"""
                    <tr>
                        <td>{col["column_name"]}</td>
                        <td>{col["data_type"]}</td>
                        <td>{col["is_nullable"]}</td>
                        <td>{col["column_default"] or ''}</td>
                        <td>{is_pk}</td>
                    </tr>
                """

            html += """
                </table>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

        except Exception as e:
            return HTMLResponse(content=f"<h1>错误</h1><p>查询失败: {str(e)}</p>", status_code=500)

    return app