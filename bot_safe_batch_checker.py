
from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
from uuid import uuid4
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_NAME = os.getenv("SESSION_NAME", "checker_session")

# Extract numbers from text
def extract_numbers(text):
    lines = text.splitlines()
    numbers = set()
    for line in lines:
        num = line.strip().replace(" ", "").replace("+", "")
        if num.isdigit() and 11 <= len(num) <= 15:
            numbers.add("+" + num)
    return list(numbers)

# Safe checker with batch limiter
async def safe_check_telegram(numbers, batch_size=4000, wait_seconds=10):
    found = []
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        for i in range(0, len(numbers), batch_size):
            chunk = numbers[i:i + batch_size]
            try:
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
                await asyncio.sleep(wait_seconds)
            except FloodWaitError as e:
                print(f"⏳ Flood wait for {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 5)
    return found

# Split and send in chunks
async def send_in_chunks(update, numbers, chunk_size=50):
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    for i, chunk in enumerate(chunks):
        await update.message.reply_text("\n".join(chunk))

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send phone numbers (11–15 digits) separated by new lines.\n"
        "Example:\n+584162314157\n+584167562626\n...\n"
        "📌 I’ll return only the numbers that have Telegram accounts.\n"
        "⏱ To avoid Telegram limits, results will be processed in batches."
    )

# Handle incoming message
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raw = update.message.text
        numbers = extract_numbers(raw)

        if not numbers:
            await update.message.reply_text("⚠️ No valid numbers found. Please check formatting.")
            return

        await update.message.reply_text(f"🔍 Processing {len(numbers)} numbers in batches...")
        result = await safe_check_telegram(numbers)

        if result:
            await update.message.reply_text(f"✅ Found {len(result)} Telegram users:")
            await send_in_chunks(update, result)
        else:
            await update.message.reply_text("❌ No Telegram accounts found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Run the bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🤖 Bot running with safe batch processing...")
    app.run_polling()
