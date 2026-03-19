import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class SyncStateManager:
    
    def __init__(self, state_file: str = None):
        if state_file is None:
            base_dir = Path(__file__).resolve().parent.parent
            state_file = base_dir / "sync_state.json"
        self.state_file = Path(state_file)
        self._state: Dict = {}
        self._load()
    
    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.warning(f"加载同步状态文件失败: {e}")
                self._state = {}
        else:
            self._state = {}
    
    def _save(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同步状态文件失败: {e}")
    
    def is_year_verified(self, table_name: str, year: int) -> bool:
        table_state = self._state.get(table_name, {})
        year_state = table_state.get(str(year), {})
        return year_state.get('verified', False)
    
    def mark_year_verified(self, table_name: str, year: int, trade_dates: int = 0):
        if table_name not in self._state:
            self._state[table_name] = {}
        
        self._state[table_name][str(year)] = {
            'verified': True,
            'verified_at': datetime.now().isoformat(),
            'trade_dates': trade_dates
        }
        self._save()
        logger.info(f"标记 {table_name}.{year} 已验证 ({trade_dates} 个交易日)")
    
    def mark_year_incomplete(self, table_name: str, year: int):
        if table_name not in self._state:
            self._state[table_name] = {}
        
        self._state[table_name][str(year)] = {
            'verified': False,
            'verified_at': datetime.now().isoformat(),
            'trade_dates': 0
        }
        self._save()
    
    def get_next_sync_year(self, table_name: str, current_year: int, min_year: int = 2010) -> Optional[int]:
        for year in range(current_year, min_year - 1, -1):
            if not self.is_year_verified(table_name, year):
                return year
        return None
    
    def get_all_verified_years(self, table_name: str) -> List[int]:
        table_state = self._state.get(table_name, {})
        return [int(y) for y, s in table_state.items() if s.get('verified', False)]
    
    def get_table_state(self, table_name: str) -> Dict:
        return self._state.get(table_name, {})
    
    def reset_year(self, table_name: str, year: int):
        if table_name in self._state and str(year) in self._state[table_name]:
            del self._state[table_name][str(year)]
            self._save()
    
    def reset_table(self, table_name: str):
        if table_name in self._state:
            del self._state[table_name]
            self._save()


sync_state_manager = SyncStateManager()
