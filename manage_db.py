# manage_db.py
import sqlite3
import os
import sys
from datetime import datetime

# مسیر دقیق دیتابیس
DATABASE_PATH = "data/bot_database.db"

# کلیدهای ممنوعه (همانند دیتابیس اصلی)
BLOCKED_MEMORY_KEYS = {'id', 'telegram_id', 'user_id', 'admin', 'system', 'role', 'prompt', 'created_at'}

def get_conn():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_if_not_exists():
    """ساخت جداول اولیه در صورت عدم وجود"""
    conn = get_conn()
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_uid ON user_memory(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_uid ON conversations(user_id)")
    conn.commit()
    conn.close()

def user_exists(telegram_id):
    """بررسی وجود کاربر"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (int(telegram_id),))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def add_user(telegram_id, display_name=""):
    conn = get_conn()
    try:
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, display_name, created_at, last_activity) VALUES (?, ?, ?, ?)",
            (int(telegram_id), display_name, now, now)
        )
        conn.commit()
        if cursor.rowcount > 0:
            print(f"✅ کاربر با آیدی {telegram_id} با موفقیت اضافه شد.")
        else:
            print(f"⚠️ کاربر با آیدی {telegram_id} از قبل وجود دارد.")
    except ValueError:
        print("❌ خطا: آیدی تلگرام باید فقط شامل اعداد باشد.")
    except Exception as e:
        print(f"❌ خطا در ثبت کاربر: {e}")
    finally:
        conn.close()

def remove_user(telegram_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE telegram_id = ?", (int(telegram_id),))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"✅ کاربر با آیدی {telegram_id} حذف شد.")
        else:
            print(f"⚠️ کاربری با آیدی {telegram_id} یافت نشد.")
    except Exception as e:
        print(f"❌ خطا در حذف کاربر: {e}")
    finally:
        conn.close()

def list_users():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, display_name, message_count, created_at FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("📭 دیتابیس خالی است. هیچ کاربری ثبت نشده.")
    else:
        print(f"\n👥 لیست کاربران ثبت شده ({len(rows)} نفر):\n" + "="*40)
        for row in rows:
            name = row['display_name'] or "بدون نام"
            print(f"🆔 آیدی: {row['telegram_id']} | 👤 نام: {name} | 📊 پیام‌ها: {row['message_count']}")
        print("="*40 + "\n")

def get_user_memory(telegram_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_memory WHERE user_id = ?", (int(telegram_id),))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"🧠 حافظه کاربر {telegram_id} خالی است.")
    else:
        print(f"\n🧠 حافظه پویای کاربر {telegram_id}:\n" + "="*40)
        for row in rows:
            print(f"🔑 کلید: {row['key']}  ➡️  مقدار: {row['value']}")
        print("="*40 + "\n")

def set_user_memory(telegram_id, key, value):
    """ثبت یا ویرایش دستی حافظه کاربر"""
    # 1. بررسی وجود کاربر
    if not user_exists(telegram_id):
        print(f"❌ خطا: کاربر با آیدی {telegram_id} در دیتابیس وجود ندارد. ابتدا او را با دستور add اضافه کنید.")
        return

    # 2. اعتبارسنجی کلید
    if key.lower() in BLOCKED_MEMORY_KEYS:
        print(f"❌ خطا: کلید '{key}' جزو کلیدهای سیستمی ممنوعه است و قابل ثبت نیست.")
        return
    if len(key) > 50:
        print(f"❌ خطا: طول کلید نمی‌تواند بیش از ۵۰ کاراکتر باشد.")
        return

    # 3. ثبت در دیتابیس (Upsert)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO user_memory (user_id, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET 
                value = excluded.value, 
                updated_at = excluded.updated_at
        ''', (int(telegram_id), str(key), str(value), now))
        conn.commit()
        print(f"✅ حافظه کاربر {telegram_id} با موفقیت ثبت/ویرایش شد:\n   [{key}] = {value}")
    except Exception as e:
        print(f"❌ خطا در ثبت حافظه: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db_if_not_exists()
    
    if len(sys.argv) < 2:
        print("\n🛠️ راهنمای مدیریت دیتابیس بات:")
        print("="*50)
        print("1. افزودن کاربر جدید:")
        print("   python manage_db.py add [آیدی_عددی] [نام_اختیاری]")
        print("   مثال: python manage_db.py add 123456789 Ali")
        print("\n2. حذف کاربر:")
        print("   python manage_db.py remove [آیدی_عددی]")
        print("   مثال: python manage_db.py remove 123456789")
        print("\n3. مشاهده لیست کاربران:")
        print("   python manage_db.py list")
        print("\n4. مشاهده حافظه یک کاربر:")
        print("   python manage_db.py memory [آیدی_عددی]")
        print("\n5. ⭐ ثبت/ویرایش دستی اطلاعات حافظه کاربر:")
        print("   python manage_db.py setmemory [آیدی_عددی] [کلید] [مقدار]")
        print("   مثال: python manage_db.py setmemory 123456789 city تهران")
        print("   مثال: python manage_db.py setmemory 123456789 job برنامه نویس پایتون")
        print("="*50)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print("❌ لطفاً آیدی عددی تلگرام را وارد کنید.")
        else:
            t_id = sys.argv[2]
            t_name = sys.argv[3] if len(sys.argv) > 3 else ""
            add_user(t_id, t_name)
            
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ لطفاً آیدی عددی تلگرام را وارد کنید.")
        else:
            remove_user(sys.argv[2])
            
    elif command == "list":
        list_users()
        
    elif command == "memory":
        if len(sys.argv) < 3:
            print("❌ لطفاً آیدی عددی کاربر را وارد کنید.")
        else:
            get_user_memory(sys.argv[2])
            
    elif command == "setmemory":
        if len(sys.argv) < 5:
            print("❌ فرمت نادرست است.")
            print("   راهنما: python manage_db.py setmemory [آیدی] [کلید] [مقدار]")
            print("   مثال: python manage_db.py setmemory 123456789 name رضا")
        else:
            t_id = sys.argv[2]
            t_key = sys.argv[3]
            # پیوستن تمام کلمات بعد از کلید به عنوان "مقدار" (برای مقادیر دارای فاصله)
            t_value = " ".join(sys.argv[4:]) 
            set_user_memory(t_id, t_key, t_value)
            
    else:
        print(f"❌ دستور '{command}' نامعتبر است. از add, remove, list, memory یا setmemory استفاده کنید.")