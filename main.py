import os
import re
import asyncio
import threading
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ================= Configuration =================
API_ID = 30077734
API_HASH = "884d4e8e52cf6752fff31a3040aed2a1"
BOT_TOKEN = "8973355682:AAHxtXBfL6IehfWUCAdie_jQH36rA8nsLjU"
OWNER_ID = 8900371852

# Database Handling (SQLite Database)
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

# Create Tables if not exist
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS approved_groups (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS cards (file_unique_id TEXT PRIMARY KEY, name TEXT, card_id TEXT, rarity TEXT, anime TEXT)")
conn.commit()

# Initialize Pyrogram Bot
app = Client(
    "CheatBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= Web Server (For Render Keep-Alive) =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# Helper Function
def format_card_response(card_data):
    name, card_id, rarity = card_data[1], card_data[2], card_data[3]
    name_parts = name.split()
    hint_name = name_parts[0] if name_parts else name

    text = (
        f"**NAME :** {name}\n"
        f"**ID :** {card_id}\n"
        f"**RARITY :** {rarity}\n"
        f"────────────────\n"
        f"🔹 **Hint :** `/dao {hint_name}`\n"
        f"🔸 **Full :** `/dao {name}`\n\n"
        f"Powered by @Speed_Characters_Cheats_Bot"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Update Channel", url="https://t.me/Auraupadte")]
    ])
    return text, keyboard

# ================= Start Command =================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    
    text = "Cheat Bot ပါ\n\nReply ထောက်ပီး\n.w ရိုက်ပီး name ယူပါ"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Update Channel", url="https://t.me/Auraupadte")]
    ])
    await message.reply_text(text, reply_markup=keyboard)

# ================= Stats Command =================
@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_cmd(client: Client, message: Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM approved_groups")
    total_groups = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cards")
    total_cards = cursor.fetchone()[0]
    
    stats_text = (
        f"📊 **Bot Statistics**\n\n"
        f"👤 **Total Users:** `{total_users}`\n"
        f"👥 **Approved Groups:** `{total_groups}`\n"
        f"🃏 **Total Cards Saved:** `{total_cards}`"
    )
    await message.reply_text(stats_text)

# ================= Broadcast Command =================
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("⚠️ Message ကို Reply ထောက်ပြီး `/broadcast` လို့ ရိုက်ပါ။")
        return

    status_msg = await message.reply_text("🚀 ကြော်ညာ ပို့ဆောင်နေပါပြီ...")
    
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    cursor.execute("SELECT chat_id FROM approved_groups")
    groups = cursor.fetchall()

    success_u, failed_u = 0, 0
    success_g, failed_g = 0, 0

    for u in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(u[0])
            else:
                await client.send_message(u[0], message.text.split(None, 1)[1])
            success_u += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_u += 1

    for g in groups:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(g[0])
            else:
                await client.send_message(g[0], message.text.split(None, 1)[1])
            success_g += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_g += 1

    await status_msg.edit_text(
        f"✅ **Broadcast ပြီးစီးပါပြီ!**\n\n"
        f"👤 Users: {success_u} အောင်မြင် | {failed_u} ကျရှုံး\n"
        f"👥 Groups: {success_g} အောင်မြင် | {failed_g} ကျရှုံး"
    )

# ================= Approve Group =================
@app.on_message(filters.command("approve") & filters.group)
async def approve_group(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    cursor.execute("INSERT OR IGNORE INTO approved_groups VALUES (?)", (message.chat.id,))
    conn.commit()
    await message.reply_text("✅ ဒီ Group ကို Auto Cheat ဖော်ပေးရန် Approve လုပ်လိုက်ပါပြီ။")

# ================= Add Card (Owner) =================
@app.on_message(filters.private & filters.user(OWNER_ID) & filters.photo)
async def add_card_to_db(client: Client, message: Message):
    if not message.caption:
        return

    file_unique_id = message.photo.file_unique_id
    caption = message.caption
    
    name_m = re.search(r"👤 Name:\s*(.+)", caption)
    id_m = re.search(r"🆔 ID:\s*(.+)", caption)
    rarity_m = re.search(r"🏷 Rarity:\s*(.+)", caption)
    anime_m = re.search(r"🌴 Anime:\s*(.+)", caption)

    if name_m:
        card_name = name_m.group(1).strip()
        card_id = id_m.group(1).strip() if id_m else "N/A"
        rarity = rarity_m.group(1).strip() if rarity_m else "N/A"
        anime = anime_m.group(1).strip() if anime_m else "N/A"

        cursor.execute(
            "INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?)",
            (file_unique_id, card_name, card_id, rarity, anime)
        )
        conn.commit()
        await message.reply_text(f"✅ Card သိမ်းဆည်းပြီးပါပြီ!\n\n**Name:** {card_name}\n**ID:** {card_id}")

# ================= Auto Group Card Finder =================
@app.on_message(filters.group & filters.photo)
async def auto_group_card_finder(client: Client, message: Message):
    cursor.execute("SELECT chat_id FROM approved_groups WHERE chat_id = ?", (message.chat.id,))
    if not cursor.fetchone():
        return

    file_unique_id = message.photo.file_unique_id
    cursor.execute("SELECT * FROM cards WHERE file_unique_id = ?", (file_unique_id,))
    card = cursor.fetchone()

    if card:
        text, keyboard = format_card_response(card)
        await message.reply_text(text, reply_markup=keyboard, reply_to_message_id=message.id)

# ================= Manual Group Check (.w) =================
@app.on_message(filters.group & filters.regex(r"^\.w$"))
async def manual_card_finder(client: Client, message: Message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        bot_username = (await client.get_me()).username
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Bot DM Start နှိပ်ရန်", url=f"https://t.me/{bot_username}?start=start")]
        ])
        await message.reply_text("အသုံးပြုရန် Bot Dm start နှိပ်ပါ", reply_markup=kb)
        return

    reply_msg = message.reply_to_message
    if not reply_msg or not reply_msg.photo:
        return

    file_unique_id = reply_msg.photo.file_unique_id
    cursor.execute("SELECT * FROM cards WHERE file_unique_id = ?", (file_unique_id,))
    card = cursor.fetchone()

    if card:
        text, keyboard = format_card_response(card)
        await message.reply_text(text, reply_markup=keyboard, reply_to_message_id=reply_msg.id)

# ================= DM Photo Finder =================
@app.on_message(filters.private & filters.photo)
async def dm_card_finder(client: Client, message: Message):
    if message.from_user.id == OWNER_ID:
        return

    file_unique_id = message.photo.file_unique_id
    cursor.execute("SELECT * FROM cards WHERE file_unique_id = ?", (file_unique_id,))
    card = cursor.fetchone()

    if card:
        text, keyboard = format_card_response(card)
        await message.reply_text(text, reply_markup=keyboard)

# ================= Async Main Execution =================
async def main():
    keep_alive()
    print("Starting Bot...")
    await app.start()
    print("Bot is successfully running!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
