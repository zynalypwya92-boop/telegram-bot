"""
bot.py — فایل اصلی ربات تلگرام

قابلیت‌ها:
  /start               - راهنما
  /addtrigger کلمه | پاسخ   - اضافه کردن تریگر خودکار (وقتی کسی "کلمه" رو نوشت، "پاسخ" ارسال میشه)
  /deltrigger کلمه      - حذف یه تریگر
  /triggers              - لیست تریگرهای این چت
  /translate متن          - ترجمه‌ی متن (فارسی <-> انگلیسی، خودکار تشخیص میده)
  /price بیت‌کوین          - قیمت لحظه‌ای ارز دیجیتال (مثلا /price bitcoin)
  /joke                  - یه جوک تصادفی
  /fal                   - یه فال تصادفی
  ارسال ویدیو             - خودکار به گیف تبدیل و برگردونده میشه

نکته: توکن ربات رو باید از طریق متغیر محیطی BOT_TOKEN ست کنی، یا مستقیم در پایین جایگزین کنی.
"""

import logging
import os
import tempfile

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import database
import content
import tools

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# توکن ربات: یا از متغیر محیطی می‌خونه یا اینجا مستقیم بنویس
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")


# ---------- دستورات پایه ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام! من دستیار شخصی توی تلگرامم 🤖\n\n"
        "دستورات من:\n"
        "/addtrigger کلمه | پاسخ  — تریگر خودکار بساز\n"
        "/deltrigger کلمه — حذف تریگر\n"
        "/triggers — لیست تریگرها\n"
        "/translate متن — ترجمه\n"
        "/price bitcoin — قیمت ارز دیجیتال\n"
        "/joke — یه جوک\n"
        "/fal — فال بگیر\n"
        "یه ویدیو بفرست تا خودکار گیف بشه 🎞"
    )
    await update.message.reply_text(text)


# ---------- مدیریت تریگرها ----------

async def add_trigger_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    استفاده: /addtrigger کلمه | پاسخ
    مثال: /addtrigger پویا | الان کار دارم بعدا بهت پیام میدم
    """
    raw = update.message.text.partition(" ")[2]
    if "|" not in raw:
        await update.message.reply_text(
            "فرمت درست:\n/addtrigger کلمه | پاسخ\n\nمثال:\n/addtrigger پویا | الان کار دارم بعدا بهت پیام میدم"
        )
        return

    keyword, response = raw.split("|", 1)
    keyword = keyword.strip()
    response = response.strip()

    if not keyword or not response:
        await update.message.reply_text("هم کلمه و هم پاسخ باید پر باشن.")
        return

    database.add_trigger(update.effective_chat.id, keyword, response)
    await update.message.reply_text(f"✅ تریگر ثبت شد:\nوقتی کسی «{keyword}» رو بنویسه، این پیام ارسال میشه:\n«{response}»")


async def del_trigger_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.partition(" ")[2].strip()
    if not keyword:
        await update.message.reply_text("بنویس: /deltrigger کلمه")
        return
    ok = database.remove_trigger(update.effective_chat.id, keyword)
    if ok:
        await update.message.reply_text(f"❌ تریگر «{keyword}» حذف شد.")
    else:
        await update.message.reply_text("همچین تریگری پیدا نشد.")


async def list_triggers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = database.list_triggers(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("هنوز هیچ تریگری ثبت نکردی.")
        return
    text = "لیست تریگرهای این چت:\n\n"
    for r in rows:
        text += f"• «{r['keyword']}» → «{r['response']}»\n"
    await update.message.reply_text(text)


# ---------- ابزارها ----------

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("بنویس: /translate متنی که میخوای ترجمه بشه")
        return
    result = tools.translate_text(text)
    await update.message.reply_text(result)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = update.message.text.partition(" ")[2].strip().lower() or "bitcoin"
    result = tools.get_crypto_price(coin)
    await update.message.reply_text(result)


async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(content.random_joke())


async def fal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(content.random_fortune())


# ---------- ویدیو به گیف ----------

async def video_to_gif_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        return

    await update.message.reply_text("در حال تبدیل ویدیو به گیف... ⏳")

    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, "input.mp4")
        output_path = os.path.join(tmp, "output.gif")

        file = await context.bot.get_file(video.file_id)
        await file.download_to_drive(input_path)

        ok = tools.convert_video_to_gif(input_path, output_path)
        if ok and os.path.exists(output_path):
            with open(output_path, "rb") as f:
                await update.message.reply_animation(f)
        else:
            await update.message.reply_text(
                "تبدیل ناموفق بود. مطمئن شو ffmpeg روی سرور نصبه."
            )


# ---------- تشخیص خودکار تریگر روی پیام‌های معمولی ----------

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    response = database.find_matching_trigger(update.effective_chat.id, update.message.text)
    if response:
        await update.message.reply_text(response)


def main():
    if BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit(
            "توکن ربات ست نشده. متغیر محیطی BOT_TOKEN رو ست کن یا مستقیم توی bot.py بنویس."
        )

    database.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addtrigger", add_trigger_cmd))
    app.add_handler(CommandHandler("deltrigger", del_trigger_cmd))
    app.add_handler(CommandHandler("triggers", list_triggers_cmd))
    app.add_handler(CommandHandler("translate", translate_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("fal", fal_cmd))

    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video_to_gif_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
