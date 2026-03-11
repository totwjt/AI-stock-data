from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
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


def read_static_html(filename: str) -> str:
    html_path = os.path.join(os.path.dirname(__file__), "../static", filename)
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<html><body><h1>404 - {filename} not found</h1></body></html>"


@app.get("/", response_class=HTMLResponse)
async def root():
    return read_static_html("index.html")


@app.get("/api-tester", response_class=HTMLResponse)
async def api_tester():
    return read_static_html("api-tester.html")


@app.get("/api-stats", response_class=HTMLResponse)
async def api_stats():
    return read_static_html("api-stats.html")


@app.get("/ai-docs", response_class=HTMLResponse)
async def ai_docs():
    return read_static_html("ai-docs.json")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
