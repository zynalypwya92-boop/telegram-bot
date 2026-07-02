"""
bot.py — دستیار شخصی تلگرام (اکثر قابلیت‌ها فقط برای مالک، چندتاشون برای همه)

قابلیت‌های مالک (owner-only):
  پنل                       - مدیریت تریگرهای عمومی/ریپلای
  /translate + خط بعد متن   - ترجمه
  /addtrigger + کلمه + پاسخ - افزودن تریگر عمومی (۳ خط)
  /addreplytrigger + ...    - افزودن تریگر ریپلای (۳ خط)
  دلار/طلا/سکه/...          - قیمت به تومان
  قیمت <رمزارز>              - قیمت با نمودار ۷ روزه
  پرمیوم / استارز            - قیمت تلگرام پرمیوم و استارز
  جوک / فال                 - با هوش مصنوعی
  اطلاعات (ریپلای یا آیدی عددی) - پروفایل کاربر
  لقب <متن> (روی ریپلای)     - تنظیم لقب یه کاربر
  تگ                        - پنل تگ‌کردن کاربران
  ویدیو + «گیف»              - تبدیل به گیف

قابلیت‌های عمومی (برای همه‌ی اعضای گروه):
  تریگرهای عمومی و ریپلای، سلام/شب‌بخیر/... با هوش مصنوعی + لقب
"""

import logging
import os
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import database
import tools

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- تنظیمات ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
BRS_API_KEY = os.environ.get("BRS_API_KEY", "PUT_YOUR_BRSAPI_KEY_HERE")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "PUT_YOUR_GROQ_KEY_HERE")
OWNER_ID = int(os.environ.get("OWNER_ID", "6386018481"))

PRICE_KEYWORDS_FA = ["دلار", "یورو", "پوند", "درهم", "طلا", "سکه", "تتر"]
GREETING_WORDS = ["سلام", "صبح بخیر", "شب بخیر", "خداحافظ", "چطوری", "خسته نباشید", "روز بخیر"]


def is_owner(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id == OWNER_ID


def is_greeting(text: str) -> bool:
    return any(text.startswith(g) for g in GREETING_WORDS)


# ---------- دستور پایه ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    text = (
        "سلام پویا! من دستیار شخصی توئم 🤖\n\n"
        "«پنل» → مدیریت تریگرها\n"
        "/translate + خط بعد متن → ترجمه\n"
        "دلار/طلا/سکه/... → قیمت\n"
        "«قیمت بیت کوین» → قیمت با نمودار\n"
        "«پرمیوم» / «استارز» → قیمت تلگرام\n"
        "«جوک» / «فال»\n"
        "رو کسی ریپلای کن و بگو «اطلاعات»\n"
        "رو کسی ریپلای کن و بگو «لقب چیزی»\n"
        "«تگ» → پنل تگ کردن\n"
        "ویدیو بفرست و بگو «گیف»"
    )
    await update.message.reply_text(text)


# ---------- پنل مدیریت تریگرها ----------

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ افزودن تریگر عمومی", callback_data="add_trigger")],
        [InlineKeyboardButton("📃 لیست تریگرهای عمومی", callback_data="list_triggers")],
        [InlineKeyboardButton("🗑 حذف تریگر عمومی", callback_data="del_menu_trigger")],
        [InlineKeyboardButton("➕ افزودن تریگر ریپلای", callback_data="add_reply_trigger")],
        [InlineKeyboardButton("📃 لیست تریگرهای ریپلای", callback_data="list_reply_triggers")],
        [InlineKeyboardButton("🗑 حذف تریگر ریپلای", callback_data="del_menu_reply_trigger")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="close_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def del_submenu_keyboard(kind: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔸 حذف تکی", callback_data=f"del_single_{kind}")],
        [InlineKeyboardButton("🔺 حذف همگانی", callback_data=f"del_all_confirm_{kind}")],
        [InlineKeyboardButton("« بازگشت", callback_data="back")],
    ])


def confirm_all_keyboard(kind: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، همه رو پاک کن", callback_data=f"del_all_yes_{kind}")],
        [InlineKeyboardButton("↩️ انصراف", callback_data="back")],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« بازگشت", callback_data="back")]])


def tag_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛡 کاربران مقام‌دار", callback_data="tag_admins")],
        [InlineKeyboardButton("🟢 کاربران فعال (۲۴ساعت)", callback_data="tag_active")],
        [InlineKeyboardButton("👥 همه‌ی کاربران دیده‌شده", callback_data="tag_all")],
        [InlineKeyboardButton("👑 مالک گروه", callback_data="tag_owner")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text("🎛 پنل مدیریت:", reply_markup=main_menu_keyboard())


async def show_tag_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text("چه کسایی رو تگ کنم؟", reply_markup=tag_menu_keyboard())


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != OWNER_ID:
        await query.answer("این پنل فقط برای مالک ربات فعاله.", show_alert=True)
        return
    await query.answer()

    data = query.data
    chat_id = query.message.chat.id

    if data == "back":
        await query.edit_message_text("🎛 پنل مدیریت:", reply_markup=main_menu_keyboard())

    elif data == "add_trigger":
        context.user_data["awaiting"] = "add_trigger"
        await query.edit_message_text(
            "✍️ پیام بعدی رو این‌طوری بفرست:\n\nکلمه\nپاسخ",
            reply_markup=back_keyboard(),
        )

    elif data == "add_reply_trigger":
        context.user_data["awaiting"] = "add_reply_trigger"
        await query.edit_message_text(
            "✍️ پیام بعدی رو این‌طوری بفرست:\n\nکلمه\nپاسخ\n\n"
            "(فقط وقتی فعال میشه که یکی رو پیام تو ریپلای بزنه و این کلمه رو بگه)",
            reply_markup=back_keyboard(),
        )

    elif data == "list_triggers":
        rows = database.list_triggers(chat_id)
        text = "هنوز هیچ تریگر عمومی‌ای ثبت نشده." if not rows else (
            "📃 تریگرهای عمومی:\n\n" + "\n".join(f"• «{r['keyword']}» → «{r['response']}»" for r in rows)
        )
        await query.edit_message_text(text, reply_markup=back_keyboard())

    elif data == "list_reply_triggers":
        rows = database.list_reply_triggers(chat_id)
        text = "هنوز هیچ تریگر ریپلای‌ای ثبت نشده." if not rows else (
            "📃 تریگرهای ریپلای:\n\n" + "\n".join(f"• «{r['keyword']}» → «{r['response']}»" for r in rows)
        )
        await query.edit_message_text(text, reply_markup=back_keyboard())

    elif data == "help":
        text = (
            "ℹ️ راهنما:\n\n"
            "🔹 تریگر عمومی: هر کسی بگه، جواب میده.\n"
            "🔹 تریگر ریپلای: فقط وقتی رو پیام تو ریپلای بشه."
        )
        await query.edit_message_text(text, reply_markup=back_keyboard())

    elif data in ("tag_admins", "tag_active", "tag_all", "tag_owner"):
        await handle_tag(query, context, chat_id, data)

    elif data in ("del_menu_trigger", "del_menu_reply_trigger"):
        kind = "trigger" if data == "del_menu_trigger" else "reply_trigger"
        label = "عمومی" if kind == "trigger" else "ریپلای"
        await query.edit_message_text(f"🗑 حذف تریگر {label} - کدوم روش؟", reply_markup=del_submenu_keyboard(kind))

    elif data.startswith("del_single_"):
        kind = data.replace("del_single_", "")
        context.user_data["awaiting"] = f"del_single_{kind}"
        await query.edit_message_text("کلمه‌ی تریگری که میخوای حذف بشه رو بنویس.", reply_markup=back_keyboard())

    elif data.startswith("del_all_confirm_"):
        kind = data.replace("del_all_confirm_", "")
        label = "عمومی" if kind == "trigger" else "ریپلای"
        await query.edit_message_text(
            f"⚠️ مطمئنی می‌خوای همه‌ی تریگرهای {label} پاک بشن؟ این کار برگشت‌پذیر نیست.",
            reply_markup=confirm_all_keyboard(kind),
        )

    elif data.startswith("del_all_yes_"):
        kind = data.replace("del_all_yes_", "")
        if kind == "trigger":
            database.delete_all_triggers(chat_id)
        else:
            database.delete_all_reply_triggers(chat_id)
        await query.edit_message_text("✅ همه پاک شدن.", reply_markup=back_keyboard())

    elif data == "close_panel":
        await query.message.delete()


async def handle_wizard_input(update: Update, context: ContextTypes.DEFAULT_TYPE, awaiting: str, text: str):
    chat_id = update.effective_chat.id

    if awaiting in ("add_trigger", "add_reply_trigger"):
        parts = text.split("\n", 1)
        if len(parts) < 2 or not parts[1].strip():
            await update.message.reply_text("فرمت درست نبود. خط اول کلمه، خط دوم پاسخ. دوباره از «پنل» امتحان کن.")
            return
        keyword, response = parts[0].strip(), parts[1].strip()
        if awaiting == "add_trigger":
            database.add_trigger(chat_id, keyword, response)
            await update.message.reply_text(f"✅ تریگر عمومی «{keyword}» اضافه شد.")
        else:
            database.add_reply_trigger(chat_id, keyword, response)
            await update.message.reply_text(f"✅ تریگر ریپلای «{keyword}» اضافه شد.")

    elif awaiting == "del_single_trigger":
        ok = database.remove_trigger(chat_id, text.strip())
        await update.message.reply_text("✅ تریگر حذف شد." if ok else "همچین تریگری پیدا نشد.")

    elif awaiting == "del_single_reply_trigger":
        ok = database.remove_reply_trigger(chat_id, text.strip())
        await update.message.reply_text("✅ تریگر حذف شد." if ok else "همچین تریگری پیدا نشد.")


# ---------- دستورات اسلش با فرمت چندخطی ----------

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    parts = update.message.text.split("\n", 1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("بعد از /translate یه خط پایین‌تر متن رو بنویس.")
        return
    await update.message.reply_text(tools.translate_text(parts[1].strip()))


async def addtrigger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    lines = update.message.text.split("\n")
    if len(lines) < 3 or not lines[1].strip() or not "".join(lines[2:]).strip():
        await update.message.reply_text("فرمت: خط اول /addtrigger، خط دوم کلمه، خط سوم پاسخ.")
        return
    keyword = lines[1].strip()
    response = "\n".join(lines[2:]).strip()
    database.add_trigger(update.effective_chat.id, keyword, response)
    await update.message.reply_text(f"✅ تریگر عمومی «{keyword}» اضافه شد.")


async def addreplytrigger_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    lines = update.message.text.split("\n")
    if len(lines) < 3 or not lines[1].strip() or not "".join(lines[2:]).strip():
        await update.message.reply_text("فرمت: خط اول /addreplytrigger، خط دوم کلمه، خط سوم پاسخ.")
        return
    keyword = lines[1].strip()
    response = "\n".join(lines[2:]).strip()
    database.add_reply_trigger(update.effective_chat.id, keyword, response)
    await update.message.reply_text(f"✅ تریگر ریپلای «{keyword}» اضافه شد.")


# ---------- اطلاعات کاربر ----------

async def send_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        chat = await context.bot.get_chat(user_id)
    except Exception:
        await update.message.reply_text(
            "اطلاعاتی از این آیدی پیدا نکردم. باید طرف قبلاً تو یه گروه مشترک یا با خود ربات تعامل داشته باشه."
        )
        return

    name = chat.first_name or ""
    if getattr(chat, "last_name", None):
        name += " " + chat.last_name
    username = f"@{chat.username}" if chat.username else "نداره"
    bio = getattr(chat, "bio", None) or "چیزی ننوشته"

    caption = (
        f"🪪 نام: {name or 'نامشخص'}\n"
        f"🔗 یوزرنیم: {username}\n"
        f"🆔 آیدی عددی: {user_id}\n"
        f"📝 بیوگرافی: {bio}\n"
        f"⏰ آخرین بازدید: در دسترس نیست (تلگرام این اطلاعات رو به ربات‌ها نمیده)"
    )

    photos = None
    try:
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
    except Exception:
        pass

    if photos and photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id
        await update.message.reply_photo(file_id, caption=caption)
    else:
        await update.message.reply_text(caption + "\n\n(عکس پروفایلی پیدا نشد)")


# ---------- تگ‌کردن ----------

async def handle_tag(query, context: ContextTypes.DEFAULT_TYPE, chat_id: int, kind: str):
    mentions = []
    try:
        if kind == "tag_admins":
            admins = await context.bot.get_chat_administrators(chat_id)
            mentions = [f'<a href="tg://user?id={a.user.id}">{a.user.first_name}</a>' for a in admins if not a.user.is_bot]
        elif kind == "tag_owner":
            admins = await context.bot.get_chat_administrators(chat_id)
            mentions = [f'<a href="tg://user?id={a.user.id}">{a.user.first_name}</a>' for a in admins if a.status == "creator"]
        elif kind == "tag_active":
            users = database.get_active_users(chat_id, hours=24)
            mentions = [f'<a href="tg://user?id={u["user_id"]}">{u["first_name"] or "کاربر"}</a>' for u in users]
        elif kind == "tag_all":
            users = database.get_all_seen_users(chat_id)
            mentions = [f'<a href="tg://user?id={u["user_id"]}">{u["first_name"] or "کاربر"}</a>' for u in users]
    except Exception as e:
        await context.bot.send_message(chat_id, f"خطا: {e}")
        return

    if not mentions:
        await context.bot.send_message(chat_id, "کسی پیدا نشد.")
        return

    chunk = ""
    for m in mentions:
        if len(chunk) + len(m) > 3500:
            await context.bot.send_message(chat_id, chunk, parse_mode="HTML")
            chunk = ""
        chunk += m + " "
    if chunk:
        await context.bot.send_message(chat_id, chunk, parse_mode="HTML")


# ---------- ویدیو به گیف ----------

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    video = update.message.video or update.message.document
    if not video:
        return
    caption = (update.message.caption or "").strip()
    if "گیف" in caption:
        await do_convert_to_gif(update, context, video.file_id)
    else:
        context.user_data["last_video_file_id"] = video.file_id
        await update.message.reply_text("ویدیو ذخیره شد. هر وقت خواستی گیف بشه، بنویس «گیف».")


async def do_convert_to_gif(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    await update.message.reply_text("در حال تبدیل به گیف... ⏳")
    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, "input.mp4")
        output_path = os.path.join(tmp, "output.gif")
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(input_path)
        ok = tools.convert_video_to_gif(input_path, output_path)
        if ok and os.path.exists(output_path):
            with open(output_path, "rb") as f:
                await update.message.reply_animation(f)
        else:
            await update.message.reply_text("تبدیل ناموفق بود.")


# ---------- قیمت رمزارز با نمودار ----------

async def send_crypto_price_with_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, query_name: str):
    coin_id, name, symbol = tools.search_coin_id(query_name)
    if not coin_id:
        await update.message.reply_text(f"❓ رمزارز «{query_name}» پیدا نشد.")
        return

    usd_rate = tools.get_usd_to_toman_rate(BRS_API_KEY)
    caption = tools.get_crypto_price_full(query_name, usd_rate)

    with tempfile.TemporaryDirectory() as tmp:
        chart_path = os.path.join(tmp, "chart.png")
        ok = tools.generate_crypto_chart(coin_id, chart_path)
        if ok:
            with open(chart_path, "rb") as f:
                await update.message.reply_photo(f, caption=caption)
        else:
            await update.message.reply_text(caption)


# ---------- پیام‌های متنی ----------

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    owner_msg = is_owner(update)
    user = update.effective_user

    # ثبت کاربر و پیام برای قابلیت تگ + خلاصه‌ی هوش مصنوعی (فقط توی گروه‌ها)
    if update.effective_chat.type in ("group", "supergroup"):
        database.upsert_seen_user(chat_id, user.id, user.username, user.first_name)
        database.save_recent_message(chat_id, user.username or user.first_name or "کاربر", text)
        if user.id != OWNER_ID:
            try:
                await update.message.forward(OWNER_ID)
            except Exception:
                pass

    # ۰. ویزارد پنل (فقط مالک)
    if owner_msg and context.user_data.get("awaiting"):
        awaiting = context.user_data.pop("awaiting")
        await handle_wizard_input(update, context, awaiting, text)
        return

    # ۱. تریگرهای عمومی - برای همه
    resp = database.find_matching_trigger(chat_id, text)
    if resp:
        await update.message.reply_text(resp)
        return

    # ۲. تریگرهای ریپلای - برای همه، فقط وقتی رو پیام مالک ریپلای بشه
    reply_to = update.message.reply_to_message
    if reply_to and reply_to.from_user and reply_to.from_user.id == OWNER_ID:
        resp2 = database.find_matching_reply_trigger(chat_id, text)
        if resp2:
            await update.message.reply_text(resp2)
            return

    # ۳. لقب‌گذاری (مالک روی کسی ریپلای می‌زنه)
    if owner_msg and reply_to and text.startswith("لقب"):
        nickname = text[len("لقب"):].strip()
        if nickname and reply_to.from_user:
            database.set_nickname(chat_id, reply_to.from_user.id, nickname)
            await update.message.reply_text(f"✅ لقب «{nickname}» برای {reply_to.from_user.first_name} ثبت شد.")
        else:
            await update.message.reply_text("بعد از «لقب» یه اسم بنویس و رو پیام طرف ریپلای کن.")
        return

    # ۴.۵ هوش مصنوعی با فراخوانی صریح - برای همه‌ی اعضا
    if text.startswith("هوش مصنوعی"):
        rest = text.split("\n", 1)
        if len(rest) > 1 and rest[1].strip():
            question = rest[1].strip()
            system_prompt = "خودمونی، کوتاه و دوستانه فارسی جواب بده، مثل یه رفیق باهوش."
            answer = tools.ai_generate_text(question, GROQ_API_KEY, system=system_prompt)
            await update.message.reply_text(answer)
        else:
            await update.message.reply_text("بعد از «هوش مصنوعی» یه خط پایین‌تر سوال یا حرفتو بنویس.")
        return

    # ۵. سلام/شب‌بخیر و... - برای همه، با هوش مصنوعی + لقب
    if is_greeting(text):
        nickname = database.get_nickname(chat_id, user.id)
        prompt = f"یکی بهت گفته: «{text}». یه جواب طبیعی، خودمونی و کوتاه (یک خط) فارسی بده، بدون توضیح اضافه."
        ai_reply = tools.ai_generate_text(prompt, GROQ_API_KEY)
        if nickname:
            ai_reply = f"{ai_reply} {nickname}"
        await update.message.reply_text(ai_reply)
        return

    # از اینجا به بعد فقط مالک
    if not owner_msg:
        return

    # ۵. اطلاعات کاربر (ریپلای یا آیدی عددی مستقیم)
    if text in ("اطلاعات", "info"):
        if reply_to and reply_to.from_user:
            await send_user_info(update, context, reply_to.from_user.id)
        else:
            await update.message.reply_text("رو پیام یه نفر ریپلای کن و بنویس «اطلاعات»، یا آیدی عددیش رو تنها بفرست.")
        return

    if text.isdigit() and len(text) >= 5:
        await send_user_info(update, context, int(text))
        return

    # ۶. گیف با درخواست
    if text == "گیف" and context.user_data.get("last_video_file_id"):
        file_id = context.user_data.pop("last_video_file_id")
        await do_convert_to_gif(update, context, file_id)
        return

    # ۷. ترجمه با کلمه‌ی «ترجمه» (علاوه بر /translate)
    if text.startswith("ترجمه"):
        rest = text.split("\n", 1)
        if len(rest) > 1 and rest[1].strip():
            await update.message.reply_text(tools.translate_text(rest[1].strip()))
        else:
            await update.message.reply_text("بعد از «ترجمه» یه خط پایین‌تر متن رو بنویس.")
        return

    # ۸. پنل و تگ
    if text == "پنل":
        await show_panel(update, context)
        return
    if text == "تگ":
        await show_tag_panel(update, context)
        return

    # ۹. قیمت‌ها
    if text in PRICE_KEYWORDS_FA:
        await update.message.reply_text(tools.get_persian_market_price(text, BRS_API_KEY))
        return

    if text.startswith("قیمت"):
        coin_query = text.replace("قیمت", "", 1).strip()
        if coin_query:
            await send_crypto_price_with_chart(update, context, coin_query)
            return

    if text == "پرمیوم":
        usd_rate = tools.get_usd_to_toman_rate(BRS_API_KEY)
        await update.message.reply_text(tools.get_telegram_premium_price(usd_rate))
        return

    if text == "استارز":
        usd_rate = tools.get_usd_to_toman_rate(BRS_API_KEY)
        await update.message.reply_text(tools.get_telegram_stars_price(100, usd_rate))
        return

    # ۱۰. جوک و فال
    if text == "جوک":
        recent = database.get_recent_jokes(chat_id)
        avoid = "\n".join(recent) if recent else "هیچی"
        prompt = (
            "یه جوک کوتاه، باحال و کاملاً عامیانه‌ی فارسی (لحن محاوره‌ای تهرونی) بگو. "
            f"این جوک‌ها قبلاً گفته شدن، عیناً تکرارشون نکن:\n{avoid}"
        )
        joke = tools.ai_generate_text(prompt, GROQ_API_KEY)
        database.save_joke(chat_id, joke)
        await update.message.reply_text(joke)
        return

    if text == "فال":
        prompt = "یه فال کوتاه (۲-۳ خط)، جالب، مثبت و به زبان محاوره‌ای فارسی بگو."
        await update.message.reply_text(tools.ai_generate_text(prompt, GROQ_API_KEY))
        return


# ---------- خلاصه‌ی دوره‌ای گروه برای مالک ----------

async def summary_job(context: ContextTypes.DEFAULT_TYPE):
    for chat_id in database.get_all_chats_with_recent_messages():
        messages = database.get_and_clear_recent_messages(chat_id)
        if not messages:
            continue
        convo = "\n".join(f"{m['username']}: {m['text']}" for m in messages[-100:])
        prompt = (
            "این گفتگوی یه گروه تلگرامیه. خلاصه‌ی کوتاهی از نکات مهمش بده: دعوا یا بحث مهم، "
            "چیزی که کسی درباره‌ی علایقش گفته، خبر یا تصمیم مهم. اگه چیز خاصی نبود همینو بگو. "
            "فارسی، خودمونی و کوتاه بنویس.\n\n" + convo
        )
        summary = tools.ai_generate_text(prompt, GROQ_API_KEY)
        try:
            await context.bot.send_message(OWNER_ID, f"📋 خلاصه‌ی گروه:\n\n{summary}")
        except Exception:
            pass


def main():
    if BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit("توکن ربات ست نشده. متغیر محیطی BOT_TOKEN رو ست کن.")

    database.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("addtrigger", addtrigger_command))
    app.add_handler(CommandHandler("addreplytrigger", addreplytrigger_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    if app.job_queue is not None:
        app.job_queue.run_repeating(summary_job, interval=1800, first=1800)
    else:
        logger.warning("job-queue نصب نیست؛ خلاصه‌ی خودکار گروه غیرفعاله. برای فعال‌سازی: pip install \"python-telegram-bot[job-queue]\"")

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
