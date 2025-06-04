
from telethon.sync import TelegramClient

API_ID = int(input("Enter your API ID: "))
API_HASH = input("Enter your API Hash: ")
SESSION_NAME = "checker_session"

print("\n🔐 Logging in with your Telegram account...")
with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
    me = client.get_me()
    print(f"✅ Logged in as {me.first_name} (@{me.username}) [ID: {me.id}]")
    print(f"✅ Session file '{SESSION_NAME}.session' created successfully.")
