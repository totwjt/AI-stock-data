import os
import tushare as ts
from app.config import settings

# 禁用代理以解决VPN软件导致的网络请求失败问题
# 这会覆盖系统代理设置，让Tushare直接连接服务器
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'


class TushareClient:
    def __init__(self):
        self._pro = None
        self._initialized = False
    
    @property
    def pro(self):
        if self._pro is None and not self._initialized:
            token = settings.tushare_token or "你的token"
            try:
                ts.set_token(token)
                self._pro = ts.pro_api(token)
                if hasattr(self._pro, '_DataApi'):
                    self._pro._DataApi__http_url = settings.tushare_url
                self._initialized = True
            except Exception as e:
                print(f"Tushare 初始化失败: {e}")
                self._initialized = True
        return self._pro
    
    def is_valid_token(self):
        """检查 Token 是否有效"""
        if self._pro is None:
            return False
        try:
            # 尝试获取用户信息来验证 Token
            user_info = self._pro.user_info()
            return user_info is not None and len(user_info) > 0
        except:
            return False
    
    def get_stock_basic(self, **kwargs):
        return self.pro.stock_basic(**kwargs)
    
    def get_daily(self, **kwargs):
        return self.pro.daily(**kwargs)
    
    def get_trade_cal(self, **kwargs):
        return self.pro.trade_cal(**kwargs)
    
    def get_daily_basic(self, **kwargs):
        return self.pro.daily_basic(**kwargs)
    
    def get_stk_factor_pro(self, **kwargs):
        return self.pro.stk_factor_pro(**kwargs)


tushare_client = TushareClient()
