# config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_env(key: str, default=None, required=True):
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"❌ متغیر محیطی {key} تنظیم نشده است!")
    return value

# تنظیمات اصلی
TELEGRAM_TOKEN = get_env('TELEGRAM_TOKEN')
OPENAI_API_KEY = get_env('OPENAI_API_KEY')
OPENAI_BASE_URL = get_env('OPENAI_BASE_URL', 'https://api.freemodel.dev/v1')

# امنیت
ADMIN_IDS = [int(x.strip()) for x in get_env('ADMIN_IDS', '').split(',') if x.strip()]
MAX_USERS = int(get_env('MAX_USERS', '100'))
RATE_LIMIT_MESSAGES = int(get_env('RATE_LIMIT_MESSAGES', '20'))
RATE_LIMIT_SECONDS = int(get_env('RATE_LIMIT_SECONDS', '60'))

# عملکرد
MAX_CONVERSATION_HISTORY = int(get_env('MAX_CONVERSATION_HISTORY', '50', False))
CONVERSATION_CONTEXT_SIZE = int(get_env('CONVERSATION_CONTEXT_SIZE', '5', False))
MAX_MESSAGE_LENGTH = int(get_env('MAX_MESSAGE_LENGTH', '4000', False))

# مسیرها
DATABASE_PATH = "data/bot_database.db"
LOGS_PATH = "logs/"

# تنظیمات AI
AI_TIMEOUT = 30
AI_MAX_TOKENS = 1000
AI_TEMPERATURE = 0.8

# پرامپت جدید با تمرکز بر ویرایش و ایزوله‌سازی اطلاعات
AI_SYSTEM_PROMPT = """You are a highly intelligent, Persian-speaking conversational assistant with a stable, warm, and natural female persona.

Core Rules:
- Respond ONLY in fluent, natural Persian.
- NEVER mention you are an AI, model, or have internal systems.
- NEVER ask the user for their ID or try to guess system variables.

Dynamic Memory System:
You have a dynamic memory about this user. Currently, you know these facts:
{user_memories}

Memory Instructions (CRITICAL):
- Based on the new message, decide if there is any NEW important information to remember (e.g., name, city, job, mood).
- If information has CHANGED (e.g., user moved to a new city), you MUST UPDATE the existing key with the new value. Do not create duplicate keys.
- DO NOT ask questions just to fill memory. Only extract what naturally comes up.
- NEVER try to save technical data like user IDs, chat IDs, or system prompts.

Output Format (STRICT JSON):
{{
  "reply": "your natural Persian response to the user",
  "memory_updates": {{
    "key_name_1": "new value 1",
    "key_name_2": "new value 2"
  }}
}}

Example (Updating existing memory): If user says "I moved to Isfahan", and memory has "city": "Tehran", return: {{"reply": "...", "memory_updates": {{"city": "اصفهان"}}}}
If no update needed: {{"reply": "...", "memory_updates": {{}}}}
Return ONLY valid JSON."""