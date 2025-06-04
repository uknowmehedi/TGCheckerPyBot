
from dotenv import load_dotenv
load_dotenv()

import os
from uuid import uuid4
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Load credentials from .env
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_NAME = os.getenv("SESSION_NAME", "checker_session")

# Extract phone numbers and clean them
def extract_numbers_from_text(text):
    numbers = []
    lines = text.splitlines()
    for line in lines:
        num = line.strip().replace(" ", "").replace("+", "")
        if num.isdigit() and 11 <= len(num) <= 15:
            numbers.append("+" + num)
    return list(set(numbers))  # remove duplicates

# Check with Telethon
async def check_telegram_numbers(numbers):
    found = []
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        batch_size = 10000  # handle up to 100k by batches if needed
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
                found.append("+" + user.phone)
            await client(DeleteContactsRequest(id=[user.id for user in result.users]))
    return found

# Send result in chunks
async def send_chunked_results(update, numbers, chunk_size=50):
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    for i, chunk in enumerate(chunks):
        await update.message.reply_text("\n".join(chunk))

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Send a list of phone numbers (11–15 digits with country code, one per line).\n"
        "Example:\n584162314157\n584167562626\n...\n"
        "✅ I will return the list of numbers that have Telegram accounts."
    )

# Handle number checking
async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message.text
        numbers = extract_numbers_from_text(message)

        if not numbers:
            await update.message.reply_text("⚠️ No valid numbers found. Please send numbers with 11–15 digits.")
            return

        await update.message.reply_text(f"🔍 Checking {len(numbers)} numbers...")
        found = await check_telegram_numbers(numbers)

        if found:
            await update.message.reply_text(f"✅ Found {len(found)} Telegram accounts:")
            await send_chunked_results(update, found)
        else:
            await update.message.reply_text("❌ No Telegram accounts found.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Run bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_numbers))
    print("🤖 Bot is running...")
    app.run_polling()
