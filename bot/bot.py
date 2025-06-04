from dotenv import load_dotenv
load_dotenv()

import os
from uuid import uuid4
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Load from .env
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_NAME = os.getenv("SESSION_NAME", "checker_session")

# Ensure output directory exists
os.makedirs("data", exist_ok=True)

# Extract numbers from message text
def extract_numbers_from_text(text):
    lines = text.splitlines()
    numbers = []
    for line in lines:
        num = line.strip().replace(" ", "").replace("+", "")
        if num.isdigit() and 12 <= len(num) <= 15:
            numbers.append(num)
    return list(set(numbers))

# Check Telegram users
async def check_telegram_numbers(numbers):
    found = []
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        batch_size = 5000
        for i in range(0, len(numbers), batch_size):
            chunk = numbers[i:i + batch_size]
            contacts = [
                InputPhoneContact(
                    client_id=uuid4().int & 0x7FFFFFFFFFFFFFFF,
                    phone=phone,
                    first_name="User",
                    last_name=""
                ) for phone in chunk
            ]
            result = await client(ImportContactsRequest(contacts))
            for user in result.users:
                found.append(user.phone)
            await client(DeleteContactsRequest(id=[user.id for user in result.users]))
    return found

# Save to .txt
def save_to_txt(found, path="data/telegram_users.txt"):
    with open(path, "w") as f:
        for num in found:
            f.write(f"{num}\n")
    return path

# Send in chunks
async def send_chunks(update, numbers, chunk_size=40):
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    for i, chunk in enumerate(chunks):
        await update.message.reply_text(f"📱 Telegram Users (Part {i+1}):\n" + "\n".join(chunk))

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Just send phone numbers directly (with country code).\n"
        "➤ Separate each number by newline or space.\n"
        "➤ 12–15 digit numbers only."
    )

# Handle text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message.text
        numbers = extract_numbers_from_text(message)

        if not numbers:
            await update.message.reply_text("⚠️ No valid phone numbers found. Please try again.")
            return

        await update.message.reply_text("🔍 Checking numbers...")
        found = await check_telegram_numbers(numbers)
        if found:
            await send_chunks(update, found)
            file_path = save_to_txt(found)
            await update.message.reply_document(document=open(file_path, 'rb'), filename="telegram_users.txt")
        else:
            await update.message.reply_text("❌ No Telegram accounts found among the numbers.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error occurred: {e}")

# Main setup
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Bot is running...")
    app.run_polling()
