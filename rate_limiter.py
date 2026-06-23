# rate_limiter.py
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict
from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_SECONDS
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.user_requests: Dict[int, list] = defaultdict(list)
        self.last_cleanup = datetime.now()
    
    def is_allowed(self, user_id: int) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(seconds=RATE_LIMIT_SECONDS)
        
        # پاکسازی درخواست‌های قدیمی این کاربر خاص
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if req_time > cutoff
        ]
        
        if len(self.user_requests[user_id]) >= RATE_LIMIT_MESSAGES:
            return False
        
        self.user_requests[user_id].append(now)
        
        # پاکسازی دوره‌ای کل رم (هر ۵ دقیقه یکبار بدون توجه به تعداد کاربران)
        if (now - self.last_cleanup).total_seconds() > 300:
            self._cleanup_idle_users(now)
            self.last_cleanup = now
            
        return True
    
    def get_wait_time(self, user_id: int) -> int:
        if not self.user_requests[user_id]:
            return 0
        oldest = min(self.user_requests[user_id])
        wait_seconds = (oldest + timedelta(seconds=RATE_LIMIT_SECONDS) - datetime.now()).total_seconds()
        return max(0, int(wait_seconds))

    def _cleanup_idle_users(self, now: datetime):
        cutoff = now - timedelta(minutes=10)
        idle_users = [
            uid for uid, times in self.user_requests.items() 
            if not times or times[-1] < cutoff
        ]
        for uid in idle_users:
            del self.user_requests[uid]
        if idle_users:
            logger.info(f"🧹 پاکسازی رم: {len(idle_users)} کاربر غیرفعال.")