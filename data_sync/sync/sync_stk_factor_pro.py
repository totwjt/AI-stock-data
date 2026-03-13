import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from data_sync.sync.base import BaseSync
from data_sync.models.stock_factor_pro import StockFactorPro
from data_sync.models.stock_basic import StockBasic
from data_sync.tushare_client import tushare_client


class StkFactorProSync(BaseSync):
    """股票技术面因子（专业版）同步 - 支持按年份分段和每日增量"""
    
    def get_table_model(self):
        return StockFactorPro
    
    def fetch_data(self, **kwargs):
        return tushare_client.get_stk_factor_pro(**kwargs)
    
    def transform_data(self, df: pd.DataFrame) -> list:
        if df is None or df.empty:
            return []
        
        df = df.replace({pd.NA: None, float('nan'): None})
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        return df.to_dict(orient='records')
    
    async def get_stock_codes_from_factor_pro(self):
        """从 stock_factor_pro 表中获取所有股票代码"""
        result = await self.db.execute(
            select(StockFactorPro.ts_code).distinct()
        )
        return [row[0] for row in result.fetchall()]
    
    async def get_stock_codes_to_sync(self):
        """获取需要同步的股票列表（从 stock_basic 表读取，但不维护该表）"""
        # 从 stock_basic 表中获取所有股票（作为数据源，但不维护）
        result = await self.db.execute(select(StockBasic.ts_code))
        all_stocks = [row[0] for row in result.fetchall()]
        
        return all_stocks
    
    async def get_latest_trade_date(self, ts_code: str):
        result = await self.db.execute(
            select(func.max(StockFactorPro.trade_date))
            .where(StockFactorPro.ts_code == ts_code)
        )
        return result.scalar()
    
    async def sync_stock(self, ts_code: str, start_date: str = None, end_date: str = None):
        """同步单只股票的技术面因子"""
        start_time = datetime.now()
        self.logger.info(f"开始同步股票 {ts_code}")
        
        try:
            latest_date = await self.get_latest_trade_date(ts_code)
            
            if latest_date:
                sync_start_date = (datetime.strptime(latest_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
                self.logger.info(f"股票 {ts_code} 数据库最新日期: {latest_date}，从 {sync_start_date} 开始同步")
            else:
                sync_start_date = "20200101"
                self.logger.info(f"股票 {ts_code} 数据库为空，从 {sync_start_date} 开始同步")
            
            if not start_date:
                start_date = sync_start_date
            
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            # Ensure end_date does not exceed today (to avoid requesting future dates)
            today_str = datetime.now().strftime("%Y%m%d")
            if end_date > today_str:
                end_date = today_str
                self.logger.debug(f"调整结束日期为今天: {end_date}")
            
            if start_date > end_date:
                self.logger.info(f"股票 {ts_code} 已同步到最新日期，跳过")
                return 0
            
            df = self.fetch_data(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                self.logger.info(f"股票 {ts_code} 无新数据")
                return 0
            
            data_list = self.transform_data(df)
            
            if not data_list:
                self.logger.info(f"股票 {ts_code} 数据转换结果为空")
                return 0
            
            count = await self.upsert_data(data_list)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"股票 {ts_code} 同步完成，写入 {count} 条数据，耗时 {duration:.2f} 秒")
            
            return count
            
        except Exception as e:
            self.logger.error(f"股票 {ts_code} 同步失败: {str(e)}")
            raise
    
    async def sync_stock_by_year(self, ts_code: str, year: int):
        start_time = datetime.now()
        self.logger.info(f"开始同步股票 {ts_code} 的 {year} 年数据")
        
        try:
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            
            df = self.fetch_data(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                self.logger.info(f"股票 {ts_code} 在 {year} 年无数据")
                return 0
            
            data_list = self.transform_data(df)
            
            if not data_list:
                self.logger.info(f"股票 {ts_code} 在 {year} 年数据转换结果为空")
                return 0
            
            count = await self.upsert_data(data_list)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"股票 {ts_code} 在 {year} 年同步完成，写入 {count} 条数据，耗时 {duration:.2f} 秒")
            
            return count
            
        except Exception as e:
            self.logger.error(f"股票 {ts_code} 在 {year} 年同步失败: {str(e)}")
            raise
    
    async def sync_history_by_year(self, start_year: int = 2020, end_year: int = None):
        if end_year is None:
            end_year = datetime.now().year
        
        start_time = datetime.now()
        self.logger.info(f"开始按年份分段同步历史数据，年份范围: {start_year} - {end_year} （优先同步最近年份）")
        
        try:
            stock_codes = await self.get_listed_stock_codes()
            self.logger.info(f"获取到 {len(stock_codes)} 只股票")
            
            total_count = 0
            
            # 倒序处理：从最近年份到早年份，优先确保所有股票有最新数据
            for year in range(end_year, start_year - 1, -1):
                self.logger.info(f"开始同步 {year} 年数据...")
                
                for i, ts_code in enumerate(stock_codes):
                    try:
                        count = await self.sync_stock_by_year(ts_code, year)
                        total_count += count
                        
                        if (i + 1) % 10 == 0:
                            self.logger.info(f"已处理 {i + 1}/{len(stock_codes)} 只股票，当前年份 {year}")
                    
                    except Exception as e:
                        self.logger.warning(f"股票 {ts_code} 在 {year} 年同步失败: {str(e)}")
                        continue
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"按年份分段同步完成（优先最近年份），共写入 {total_count} 条数据，耗时 {duration:.2f} 秒")
            
            return total_count
            
        except Exception as e:
            self.logger.error(f"按年份分段同步失败: {str(e)}")
            raise
    
    async def sync_daily_incremental(self, trade_date: str = None):
        if trade_date is None:
            trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        
        start_time = datetime.now()
        self.logger.info(f"开始每日增量同步，交易日期: {trade_date}")
        
        try:
            stock_codes = await self.get_stock_codes_to_sync()
            self.logger.info(f"获取到 {len(stock_codes)} 只股票")
            
            df = self.fetch_data(start_date=trade_date, end_date=trade_date)
            
            if df is None or df.empty:
                self.logger.info(f"交易日期 {trade_date} 无数据")
                return 0
            
            data_list = self.transform_data(df)
            
            if not data_list:
                self.logger.info(f"交易日期 {trade_date} 数据转换结果为空")
                return 0
            
            count = await self.upsert_data(data_list)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"每日增量同步完成，交易日期 {trade_date}，写入 {count} 条数据，耗时 {duration:.2f} 秒")
            
            return count
            
        except Exception as e:
            self.logger.error(f"每日增量同步失败: {str(e)}")
            raise