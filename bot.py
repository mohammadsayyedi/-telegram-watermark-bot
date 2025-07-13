
import os
import subprocess
from datetime import datetime
from PIL import Image
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# تنظیمات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LOGO_DIR = "logos"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
user_state = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🖼 عکس", callback_data="mode_photo"),
            InlineKeyboardButton("🎬 فیلم", callback_data="mode_video"),
            InlineKeyboardButton("📉 تغییر سایز ویدیو", callback_data="mode_resize")
        ]
    ]
    if update.message:
        await update.message.reply_text("چی می‌خوای واترمارک بشه؟", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.reply_text("چی می‌خوای واترمارک بشه؟", reply_markup=InlineKeyboardMarkup(keyboard))

# انتخاب مد
async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    mode = query.data.replace("mode_", "")
    user_state[user_id] = {"mode": mode}

    if mode == "photo":
        keyboard = [
            [
                InlineKeyboardButton("🔷 لوگو 1", callback_data="logo1"),
                InlineKeyboardButton("🔶 لوگو 2", callback_data="logo2"),
            ]
        ]
        await query.edit_message_text("لوگوی مورد نظر برای عکس رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif mode == "video":
        await query.edit_message_text("فیلم رو بفرست تا واترمارک متنی بهش اضافه بشه (سمت چپ پایین)")
    elif mode == "resize":
        await query.edit_message_text("لطفاً ویدیویی که می‌خوای برای تلگرام سبک‌سازی بشه رو ارسال کن.")

# انتخاب لوگو
async def logo_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in user_state:
        await query.edit_message_text("لطفاً ابتدا نوع مدیا رو انتخاب کن.")
        return

    user_state[user_id]["logo"] = f"{query.data}.png"
    await query.edit_message_text("حالا لطفاً عکس رو ارسال کن.")

# واترمارک روی عکس
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_state or user_state[user_id].get("mode") != "photo":
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = f"{OUTPUT_DIR}/photo_{user_id}_{timestamp}.jpg"
    output_path = f"{OUTPUT_DIR}/watermarked_{user_id}_{timestamp}.jpg"
    await file.download_to_drive(input_path)

    logo_path = os.path.join(LOGO_DIR, user_state[user_id]["logo"])
    base_img = Image.open(input_path).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    logo_width = int(base_img.width * 0.2)
    logo_height = int(logo.height * (logo_width / logo.width))
    logo = logo.resize((logo_width, logo_height))

    pos = (10, base_img.height - logo_height - 10)
    base_img.paste(logo, pos, logo)
    base_img.convert("RGB").save(output_path)

    await update.message.reply_photo(photo=open(output_path, "rb"))
    os.remove(input_path)
    os.remove(output_path)
    user_state.pop(user_id, None)
    await start(update, context)

# واترمارک روی ویدیو
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    video = update.message.video or update.message.document
    file = await video.get_file()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = f"{OUTPUT_DIR}/video_{user_id}_{timestamp}.mp4"
    output_path = f"{OUTPUT_DIR}/watermarked_video_{user_id}_{timestamp}.mp4"
    await file.download_to_drive(input_path)

    command = [
        "ffmpeg", "-i", input_path,
        "-vf", "drawtext=text='Made by: Avash.ir':fontcolor=white:fontsize=24:x=10:y=H-th-10",
        "-c:a", "copy", output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    await update.message.reply_video(video=open(output_path, "rb"), caption="🎬 ویدیوی واترمارک‌شده")
    os.remove(input_path)
    os.remove(output_path)
    user_state.pop(user_id, None)
    await start(update, context)

# /resize
async def resize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"mode": "resize"}
    await update.message.reply_text("لطفاً ویدیویی که می‌خوای برای تلگرام سبک‌سازی بشه رو ارسال کن.")

# انتخاب عملکرد ویدیو بر اساس حالت
async def handle_all_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = user_state.get(user_id, {}).get("mode")
    if mode == "video":
        await handle_video(update, context)
    elif mode == "resize":
        await handle_resize_video(update, context)

# ری‌سایز ویدیو
async def handle_resize_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    video = update.message.video or update.message.document
    file = await video.get_file()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = f"{OUTPUT_DIR}/resize_input_{user_id}_{timestamp}.mp4"
    output_path = f"{OUTPUT_DIR}/resize_output_{user_id}_{timestamp}.mp4"
    await file.download_to_drive(input_path)

    command = [
        "ffmpeg", "-i", input_path,
        "-vf", "scale=960:-2",
        "-c:v", "libx264", "-crf", "32", "-preset", "slow",
        "-c:a", "aac", "-b:a", "96k",
        output_path
    ]
    subprocess.run(command, check=True)

    await update.message.reply_video(video=open(output_path, "rb"), caption="🎥 نسخه سبک‌شده مخصوص تلگرام")
    os.remove(input_path)
    os.remove(output_path)
    user_state.pop(user_id, None)
    await start(update, context)

# اجرای ربات
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_mode, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(logo_choice, pattern="^logo"))
    app.add_handler(CommandHandler("resize", resize_command))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_all_videos))

    app.run_polling()

if __name__ == "__main__":
    main()
