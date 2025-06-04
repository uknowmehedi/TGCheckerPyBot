
from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
from uuid import uuid4
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Load credentials from .env
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_NAME = os.getenv("SESSION_NAME", "checker_session")

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Function to extract phone numbers
def extract_numbers(file_path):
    numbers = []
    if file_path.endswith('.txt'):
        with open(file_path, 'r') as f:
            for line in f:
                num = line.strip()
                if num:
                    numbers.append(num)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
        for col in df.columns:
            numbers.extend(df[col].dropna().astype(str).tolist())
    return list(set(numbers))

# Check using Telethon
def check_telegram_numbers(numbers):
    found, not_found = [], []
    with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        contacts = [
            InputPhoneContact(
                client_id=uuid4().int & (1<<64)-1,
                phone=phone,
                first_name="User",
                last_name=""
            ) for phone in numbers
        ]
        result = client(ImportContactsRequest(contacts))
        for user in result.users:
            found.append(user.phone)
        found_set = set(found)
        for phone in numbers:
            if phone not in found_set:
                not_found.append(phone)
        client(DeleteContactsRequest(id=[user.id for user in result.users]))
    return found, not_found

# Save result to Excel
def save_results(found, not_found, output_path="data/result.xlsx"):
    df1 = pd.DataFrame({'Telegram Users': found})
    df2 = pd.DataFrame({'Not on Telegram': not_found})
    with pd.ExcelWriter(output_path) as writer:
        df1.to_excel(writer, sheet_name='Telegram Users', index=False)
        df2.to_excel(writer, sheet_name='Not on Telegram', index=False)
    return output_path

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Please upload a .txt or .xlsx file containing phone numbers. I will check which ones have Telegram accounts.")

# Telegram file handler
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        document: Document = update.message.document
        file = await context.bot.get_file(document.file_id)
        file_ext = os.path.splitext(document.file_name)[-1]
        file_path = f"data/uploaded{file_ext}"
        await file.download_to_drive(file_path)
        await update.message.reply_text("📂 File received. Checking numbers...")

        numbers = extract_numbers(file_path)
        found, not_found = check_telegram_numbers(numbers)
        result_file = save_results(found, not_found)

        await update.message.reply_document(document=open(result_file, 'rb'), filename='result.xlsx')
        await update.message.reply_text(f"✅ Done! Total: {len(numbers)}, Found: {len(found)}, Not Found: {len(not_found)}")
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {e}")

# Main bot setup
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    print("🤖 Bot is running...")
    app.run_polling()
