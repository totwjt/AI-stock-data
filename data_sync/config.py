from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class SyncSettings(BaseSettings):
    # PostgreSQL 数据库配置
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tushare_sync"
    db_user: str = "wangjiangtao"  # 与 .env 文件保持一致
    db_password: str = ""
    
    # 数据库 URL
    @property
    def database_url(self) -> str:
        host = self.db_host
        if host == "localhost":
            host = "127.0.0.1"
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{host}:{self.db_port}/{self.db_name}"
    
    # Tushare 配置
    tushare_token: str = "你的TushareToken"
    tushare_url: str = "http://lianghua.nanyangqiankun.top"
    
    # 同步配置
    batch_size: int = 1000  # 批量写入大小
    retry_times: int = 3    # 重试次数
    retry_delay: int = 5    # 重试延迟（秒）
    
    # 日志配置
    log_dir: str = str(BASE_DIR / "data_sync" / "logs")
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = SyncSettings()
