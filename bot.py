# bot.py
import telebot
from telebot import types
import signal
import sys
import time
import os
import html
import logging
from datetime import datetime

from database import UserDatabase
from ai_handler import AIHandler
from rate_limiter import RateLimiter
from config import TELEGRAM_TOKEN, ADMIN_IDS, MAX_MESSAGE_LENGTH, LOGS_PATH

# ایجاد پوشه لاگ‌ها در صورت عدم وجود (رفع باگ کرش در ابتدای کار)
os.makedirs(LOGS_PATH, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(LOGS_PATH, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
db = UserDatabase()
ai = AIHandler()
rate_limiter = RateLimiter()

bot_stats = {
    'start_time': datetime.now(),
    'messages_processed': 0,
    'errors': 0
}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def signal_handler(sig, frame):
    logger.info("🛑 در حال خاموش شدن ایمن...")
    bot.stop_polling()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ========== دستورات ادمین ==========
@bot.message_handler(commands=['adduser'])
def add_user_command(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "❌ <b>فرمت نادرست</b>\n\nاستفاده: <code>/adduser USER_ID [NAME]</code>", parse_mode='HTML')
            return
        
        user_id = int(parts[1])
        display_name = parts[2] if len(parts) > 2 else ""
        
        if db.add_user(user_id, display_name):
            bot.reply_to(message, f"✅ کاربر اضافه شد\n\n🆔 آی‌دی: <code>{user_id}</code>", parse_mode='HTML')
        else:
            bot.reply_to(message, "⚠️ این کاربر قبلاً وجود دارد یا ظرفیت پر است", parse_mode='HTML')
    except ValueError:
        bot.reply_to(message, "❌ آی‌دی باید یک عدد صحیح باشد", parse_mode='HTML')

@bot.message_handler(commands=['removeuser'])
def remove_user_command(message):
    if not is_admin(message.from_user.id): return
    try:
        parts = message.text.split()
        if len(parts) != 2: return bot.reply_to(message, "❌ فرمت: <code>/removeuser USER_ID</code>", parse_mode='HTML')
        
        user_id = int(parts[1])
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_remove_{user_id}"),
            types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_remove")
        )
        bot.reply_to(message, f"⚠️ آیا از حذف <code>{user_id}</code> مطمئنید؟", reply_markup=markup, parse_mode='HTML')
    except ValueError:
        bot.reply_to(message, "❌ آی‌دی باید عدد باشد", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_remove_'))
def confirm_remove_callback(call):
    if not is_admin(call.from_user.id): return
    user_id = int(call.data.split('_')[2])
    if db.remove_user(user_id):
        bot.edit_message_text(f"✅ کاربر <code>{user_id}</code> حذف شد.", call.message.chat.id, call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_remove')
def cancel_remove_callback(call):
    if not is_admin(call.from_user.id): return
    bot.edit_message_text("❌ عملیات لغو شد", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['listusers'])
def list_users_command(message):
    if not is_admin(message.from_user.id): return
    users = db.get_all_users()
    if users:
        user_info = [f"🆔 <code>{uid}</code>\n   📊 {db.get_user_stats(uid)['message_count']} پیام" for uid in users]
        bot.reply_to(message, f"👥 <b>کاربران مجاز</b> ({len(users)} نفر):\n\n" + "\n\n".join(user_info), parse_mode='HTML')
    else:
        bot.reply_to(message, "📭 هیچ کاربری ثبت نشده است", parse_mode='HTML')

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if not is_admin(message.from_user.id): return
    uptime = datetime.now() - bot_stats['start_time']
    hours, minutes = int(uptime.total_seconds() // 3600), int((uptime.total_seconds() % 3600) // 60)
    stats_text = (
        f"📊 <b>آمار بات</b>\n\n⏱ زمان فعالیت: {hours}h {minutes}m\n"
        f"👥 کاربران: {len(db.get_all_users())}\n"
        f"💬 پیام‌ها: {bot_stats['messages_processed']}\n"
        f"❌ خطاها: {bot_stats['errors']}\n"
        f"🤖 مدل: <code>{ai._get_model()}</code>\n"
        f"🔗 وضعیت: {'✅ فعال' if ai.health_check() else '❌ غیرفعال'}"
    )
    bot.reply_to(message, stats_text, parse_mode='HTML')

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if not is_admin(message.from_user.id): return
    text = message.text.replace('/broadcast', '').strip()
    if not text: return bot.reply_to(message, "❌ لطفاً متن پیام را وارد کنید", parse_mode='HTML')
    
    users = db.get_all_users()
    success, failed = 0, 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 <b>پیام مدیریت:</b>\n\n{html.escape(text)}", parse_mode='HTML')
            success += 1
            time.sleep(0.05) # جلوگیری از محدودیت تلگرام
        except: failed += 1
    bot.reply_to(message, f"✅ ارسال تمام شد\n\nموفق: {success}\nناموفق: {failed}", parse_mode='HTML')

# ========== دستورات عمومی ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    if not db.user_exists(message.from_user.id):
        return bot.reply_to(message, "⛔ دسترسی ندارید.\nلطفاً برای دریافت مجوز به ادمین پیام دهید.", parse_mode='HTML')
    bot.reply_to(message, "سلام! 👋\n\nخوشحالم که باهات آشنا شدم. من اینجام تا کمکت کنم و با هم گپ بزنیم.", parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    if not db.user_exists(message.from_user.id): return
    bot.reply_to(message, "🌟 <b>راهنما</b>\n\n✨ فقط کافیه پیامت رو بفرستی!\n\n/start - شروع\n/help - راهنما\n/mystats - آمار شخصی", parse_mode='HTML')

@bot.message_handler(commands=['mystats'])
def my_stats_command(message):
    if not db.user_exists(message.from_user.id): return
    stats = db.get_user_stats(message.from_user.id)
    bot.reply_to(message, f"📊 <b>آمار شما</b>\n\n💬 پیام‌ها: {stats.get('message_count', 0)}\n🗓 مکالمات: {stats.get('conversation_count', 0)}\n📅 عضویت: {stats.get('created_at', 'N/A')[:10]}", parse_mode='HTML')

# ========== پردازش پیام اصلی ==========
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_message(message):
    user_id = message.from_user.id
    
    # رفع باگ سکوت مرگبار
    if not db.user_exists(user_id):
        return bot.reply_to(message, "⛔ شما دسترسی به بات ندارید.", parse_mode='HTML')
    
    if not rate_limiter.is_allowed(user_id):
        wait_time = rate_limiter.get_wait_time(user_id)
        return bot.reply_to(message, f"⏳ لطفاً <code>{wait_time}</code> ثانیه دیگه پیام بده. 🙏", parse_mode='HTML')
    
    if len(message.text) > MAX_MESSAGE_LENGTH:
        return bot.reply_to(message, f"❌ پیام طولانی است!\nحداکثر: {MAX_MESSAGE_LENGTH} کاراکتر", parse_mode='HTML')
    
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # دریافت اطلاعات (فقط متنی و بدون آی‌دی)
        user_memories = db.get_user_profile(user_id)
        conversation_history = db.get_conversation_history(user_id, limit=5)
        
        # پردازش با AI
        reply, memory_updates = ai.process_message(
            message.text,
            user_memories,
            conversation_history
        )
        
        # ذخیره/ویرایش حافظه در صورت وجود
        if memory_updates:
            db.update_user_profile(user_id, memory_updates)
        
        # ذخیره مکالمه
        db.add_conversation(user_id, message.text, reply)
        
        # رفع باگ Markdown Injection: استفاده از HTML و Escape کردن خروجی AI
        safe_reply = html.escape(reply)
        bot.reply_to(message, safe_reply, parse_mode='HTML')
        
        bot_stats['messages_processed'] += 1
        
    except Exception as e:
        bot_stats['errors'] += 1
        logger.error(f"Error processing message from {user_id}: {e}", exc_info=True)
        try:
            bot.reply_to(message, "متأسفم، یه مشکلی پیش اومد. 😔 یه بار دیگه امتحان کن?", parse_mode='HTML')
        except: pass

@bot.message_handler(content_types=['photo', 'video', 'document', 'audio', 'voice', 'sticker'])
def handle_media(message):
    if not db.user_exists(message.from_user.id): return
    bot.reply_to(message, "متأسفم، فعلاً فقط به متن جواب میدم. 📝", parse_mode='HTML')

# ========== اجرا ==========
if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🤖 بات هوش مصنوعی (ایزوله شده، بهینه برای سرور ضعیف)")
    logger.info("="*60)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("🛑 بات متوقف شد")
    except Exception as e:
        logger.critical(f"❌ خطای بحرانی: {e}", exc_info=True)