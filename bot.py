import os
import time
import requests
from collections import defaultdict
import discord
from discord.ext import commands

# 環境変数から取得
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.ai/analyze"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

user_messages = defaultdict(list)
SPAM_THRESHOLD = 5       # 秒
SPAM_COUNT = 3           # 連投回数
TIMEOUT_DURATION = 60    # 秒

def check_message_ai(message_text: str) -> bool:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {"text": message_text, "model": "moderation"}
    try:
        r = requests.post(DEEPSEEK_URL, json=data, headers=headers, timeout=5)
        r.raise_for_status()
        result = r.json()
        return result.get("is_toxic", False)
    except Exception as e:
        print("DeepSeek error:", e)
        return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    # 連投チェック
    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間の連続投稿は禁止です。")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except Exception as e:
            print("Timeout error:", e)
        return

    # AI判定
    if check_message_ai(message.content):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 荒らし行為は禁止です。")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except Exception as e:
            print("AI moderation error:", e)
        return

    # URL/画像スパムチェック
    if any(word in message.content for word in ["http://", "https://"]):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} リンクスパムは禁止です！")
        except:
            pass

    if message.attachments and len(message.attachments) > 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 画像の大量投稿は禁止です！")
        except:
            pass

    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません！")
    bot.run(TOKEN)
