from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.config import settings
from app.database import init_db
from app.middleware.logging import LoggingMiddleware
from app.routers import stock_basic, indicators, logs
import os
from datetime import datetime, timezone

datetime.now(timezone.utc)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于Tushare的股票数据API服务，提供股票基础信息和技术指标接口"
)

app.add_middleware(LoggingMiddleware)

app.include_router(stock_basic.router, prefix="/api/v1")
app.include_router(indicators.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")

static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join(os.path.dirname(__file__), "../static/index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <html>
        <head><title>Ai-TuShare</title></head>
        <body>
            <h1>Ai-TuShare 股票数据API服务</h1>
            <p>服务运行中...</p>
            <ul>
                <li><a href="/docs">API文档</a></li>
                <li><a href="/static/index.html">看板</a></li>
            </ul>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
