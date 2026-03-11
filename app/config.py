from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Ai-TuShare 股票数据API服务"
    app_version: str = "1.0.0"
    
    # Tushare配置
    tushare_token: str = "1d7aabe519e1f1bf7cbe4e5c4f49fbad70bb3778e0c1a8abf260e183b2c7"
    tushare_url: str = "http://lianghua.nanyangqiankun.top"
    
    # 数据库配置
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/app.db"
    
    # API配置
    api_prefix: str = "/api/v1"
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
