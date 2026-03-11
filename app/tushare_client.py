import tushare as ts
from app.config import settings


class TushareClient:
    def __init__(self):
        self._pro = None
    
    @property
    def pro(self):
        if self._pro is None:
            token = settings.tushare_token or "你的token"
            self._pro = ts.pro_api(token)
            self._pro._DataApi__token = token
            self._pro._DataApi__http_url = settings.tushare_url
        return self._pro
    
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
