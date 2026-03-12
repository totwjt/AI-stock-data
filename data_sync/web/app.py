from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "tushare_sync")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


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
    from .sync_api import router as sync_router
    app.include_router(sync_router)

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
            }
            syncable_tables = list(sync_task_to_table.keys())
            table_to_sync_task = {v: k for k, v in sync_task_to_table.items()}
            
            # 获取表描述信息
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8001/api/sync/descriptions")
                    descriptions = response.json()
                    # 转换为字典以便查找（使用同步任务名称）
                    desc_dict = {d["name"]: d for d in descriptions}
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
                    .status-pending { color: #ff9800; }
                    .status-running { color: #2196F3; }
                    .status-completed { color: #4CAF50; }
                    .status-failed { color: #f44336; }
                    .desc { color: #666; font-size: 12px; }
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
                        const btn = document.getElementById('sync-' + tableName);
                        const status = document.getElementById('status-' + tableName);
                        
                        const interval = setInterval(async () => {
                            try {
                                const response = await fetch('/api/sync/status/' + taskId);
                                const data = await response.json();
                                
                                if (data.status === 'completed') {
                                    status.textContent = '完成 (' + data.records_count + ' 条)';
                                    status.className = 'status-completed';
                                    btn.disabled = false;
                                    btn.textContent = '同步';
                                    clearInterval(interval);
                                } else if (data.status === 'failed') {
                                    status.textContent = '失败: ' + data.error_message;
                                    status.className = 'status-failed';
                                    btn.disabled = false;
                                    btn.textContent = '同步';
                                    clearInterval(interval);
                                } else if (data.status === 'running') {
                                    status.textContent = '同步中... ' + data.progress + '%';
                                }
                            } catch (error) {
                                clearInterval(interval);
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
                    
                    function showTableDesc(tableName) {
                        const descDiv = document.getElementById('desc-' + tableName);
                        if (descDiv.style.display === 'none') {
                            descDiv.style.display = 'block';
                        } else {
                            descDiv.style.display = 'none';
                        }
                    }
                </script>
            </head>
            <body>
                <h1>PostgreSQL 数据库查询</h1>
                <p>可用的数据表：</p>
                <table>
                    <tr>
                        <th>表名</th>
                        <th>描述</th>
                        <th>操作</th>
                        <th>同步</th>
                        <th>状态</th>
                    </tr>
            """

            for row in tables:
                table_name = row["table_name"]
                
                # 获取对应的同步任务名称
                sync_task_name = table_to_sync_task.get(table_name)
                is_syncable = sync_task_name is not None
                
                # 同步按钮使用同步任务名称
                if is_syncable:
                    sync_btn = f'<button id="sync-{sync_task_name}" class="sync-btn" onclick="startSync(\'{sync_task_name}\')">同步</button>'
                    status_id = f"status-{sync_task_name}"
                else:
                    sync_btn = 'N/A'
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
                
                # 对于基础表，添加重新同步按钮
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
                        <td>{sync_btn}{resync_btn}</td>
                        <td id="{status_id}">-</td>
                    </tr>
                """

            html += """
                </table>
                <p>说明：绿色按钮表示可同步的表，增量同步默认最近30天数据。</p>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

        except Exception as e:
            return HTMLResponse(content=f"<h1>错误</h1><p>无法连接数据库: {str(e)}</p>", status_code=500)

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