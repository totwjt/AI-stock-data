import os
import tushare as ts
from .config import settings

# 禁用代理以解决VPN软件导致的网络请求失败问题
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'


class TushareClient:
    """Tushare 客户端封装"""
    
    def __init__(self):
        self._pro = None
        self._initialized = False
    
    @property
    def pro(self):
        """获取 Tushare Pro API 实例"""
        if self._pro is None and not self._initialized:
            token = settings.tushare_token or "你的token"
            try:
                ts.set_token(token)
                self._pro = ts.pro_api(token)
                self._initialized = True
            except Exception as e:
                print(f"Tushare 初始化失败: {e}")
                self._initialized = True
        return self._pro
    
    def get_stock_basic(self, **kwargs):
        """获取股票基础信息"""
        return self.pro.stock_basic(**kwargs)
    
    def get_daily(self, **kwargs):
        """获取日线行情"""
        return self.pro.daily(**kwargs)
    
    def get_trade_cal(self, **kwargs):
        """获取交易日历"""
        return self.pro.trade_cal(**kwargs)
    
    def get_daily_basic(self, **kwargs):
        """获取每日基本面指标"""
        return self.pro.daily_basic(**kwargs)
    
    def get_adj_factor(self, **kwargs):
        """获取复权因子"""
        return self.pro.adj_factor(**kwargs)
    
    def get_index_daily(self, **kwargs):
        """获取指数行情"""
        return self.pro.index_daily(**kwargs)
    
    def get_stk_factor_pro(self, **kwargs):
        """获取技术面因子（专业版）"""
        return self.pro.stk_factor_pro(**kwargs)


# 全局实例
tushare_client = TushareClient()