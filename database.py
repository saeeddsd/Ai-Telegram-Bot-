# database.py
import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional, Dict, List

from config import DATABASE_PATH, MAX_USERS, MAX_CONVERSATION_HISTORY

logger = logging.getLogger(__name__)

# کلیدهای ممنوعه برای جلوگیری از تغییر توسط هوش مصنوعی
BLOCKED_MEMORY_KEYS = {'id', 'telegram_id', 'user_id', 'admin', 'system', 'role', 'prompt', 'created_at'}

class UserDatabase:
    def __init__(self):
        self.db_path = DATABASE_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        """ایجاد اتصال بهینه برای سرورهای تک هسته‌ای (WAL Mode)"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        # فعال‌سازی WAL برای جلوگیری از قفل شدن دیتابیس روی CPU ضعیف
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        # بهینه‌سازی حافظه
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            display_name TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            message_count INTEGER DEFAULT 0
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
            UNIQUE(user_id, key)
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            bot_reply TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        )''')

        # ایجاد ایندکس برای جلوگیری از فشار به CPU در جستجوها (مخصوص سرور ضعیف)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_uid ON user_memory(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_uid ON conversations(user_id)")
        
        conn.commit()
        conn.close()
        logger.info("✅ دیتابیس SQLite (WAL Mode) با ایندکس‌ها آماده شد.")

    def user_exists(self, user_id: int) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def add_user(self, user_id: int, display_name: str = "") -> bool:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] >= MAX_USERS:
                conn.close()
                return False
            
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT OR IGNORE INTO users (telegram_id, display_name, created_at, last_activity) VALUES (?, ?, ?, ?)",
                (user_id, display_name[:100], now, now)
            )
            conn.commit()
            added = cursor.rowcount > 0
            conn.close()
            return added
        except Exception as e:
            logger.error(f"❌ خطا در افزودن کاربر: {e}")
            return False

    def remove_user(self, user_id: int) -> bool:
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        except Exception as e:
            logger.error(f"❌ خطا در حذف کاربر: {e}")
            return False

    def get_all_users(self) -> List[int]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users

    def get_user_profile(self, user_id: int) -> Dict:
        """دریافت حافظه پویا (بدون هیچ آی‌دی سیستم‌ای)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_memory WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return {row['key']: row['value'] for row in rows}

    def update_user_profile(self, user_id: int, updates: Dict) -> bool:
        """آپدیت حافظه با فیلتر کردن کلیدهای خطرناک"""
        if not updates:
            return False
            
        # فیلتر کردن کلیدهای سیستمی برای جلوگیری از حملات Prompt Injection
        safe_updates = {
            k: str(v) for k, v in updates.items() 
            if k.lower() not in BLOCKED_MEMORY_KEYS and len(k) <= 50
        }
        
        if not safe_updates:
            logger.warning(f"⚠️ تلاش برای ذخیره کلید ممنوعه توسط کاربر {user_id} رد شد.")
            return False
            
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            for key, value in safe_updates.items():
                cursor.execute('''
                    INSERT INTO user_memory (user_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, key) DO UPDATE SET 
                        value = excluded.value, 
                        updated_at = excluded.updated_at
                ''', (user_id, key, value, now))
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ خطا در آپدیت حافظه: {e}")
            return False

    def add_conversation(self, user_id: int, user_msg: str, bot_reply: str):
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO conversations (user_id, user_message, bot_reply, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, user_msg[:2000], bot_reply[:4000], now)
            )
            
            cursor.execute('''UPDATE users SET 
                message_count = message_count + 1, 
                last_activity = ? 
                WHERE telegram_id = ?''', (now, user_id))
            
            # کوئری بهینه برای پاکسازی (جلوگیری از فشار CPU)
            cursor.execute('''
                DELETE FROM conversations WHERE user_id = ? AND id < (
                    SELECT id FROM conversations WHERE user_id = ? 
                    ORDER BY id DESC LIMIT 1 OFFSET ?
                )
            ''', (user_id, user_id, MAX_CONVERSATION_HISTORY))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره مکالمه: {e}")

    def get_conversation_history(self, user_id: int, limit: int = 5) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        # استفاده از Subquery برای گرفتن آخرین پیام‌ها به صورت صعودی (بدون Reverse در پایتون)
        cursor.execute('''
            SELECT user_message as user, bot_reply as bot FROM (
                SELECT user_message, bot_reply FROM conversations 
                WHERE user_id = ? ORDER BY id DESC LIMIT ?
            ) ORDER BY rowid ASC
        ''', (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_stats(self, user_id: int) -> Dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) as cnt FROM conversations WHERE user_id = ?", (user_id,))
        conv_count = cursor.fetchone()['cnt']
        conn.close()
        
        if user:
            return {
                'message_count': user['message_count'],
                'created_at': user['created_at'],
                'last_activity': user['last_activity'],
                'conversation_count': conv_count
            }
        return {}

    # ── Web Panel Methods ──

    def panel_get_all_users(self, search: str = None) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        if search:
            like = f"%{search}%"
            cursor.execute(
                "SELECT * FROM users WHERE display_name LIKE ? OR CAST(telegram_id AS TEXT) LIKE ? ORDER BY last_activity DESC",
                (like, like)
            )
        else:
            cursor.execute("SELECT * FROM users ORDER BY last_activity DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def panel_get_user(self, telegram_id: int) -> Optional[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def panel_get_memory(self, user_id: int) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key, value, updated_at FROM user_memory WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def panel_get_history(self, user_id: int) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_message, bot_reply, timestamp FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user_id,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        rows.reverse()
        return rows

    def panel_get_stats(self) -> Dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM users")
        total_users = cursor.fetchone()['c']
        cursor.execute("SELECT COALESCE(SUM(message_count), 0) as c FROM users")
        total_messages = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM conversations")
        total_conversations = cursor.fetchone()['c']
        conn.close()
        return {
            'total_users': total_users,
            'total_messages': total_messages,
            'total_conversations': total_conversations,
        }