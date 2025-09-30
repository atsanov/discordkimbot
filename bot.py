import os
import time
import requests
from collections import defaultdict
import discord
from discord.ext import commands

# ====== 環境変数 ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません！")
if not DEEPSEEK_API_KEY:
    raise ValueError("❌ DEEPSEEK_API_KEY が設定されていません！")

# ====== DeepSeek API エンドポイント ======
DEEPSEEK_MOD_URL = "https://api.deepseek.com/lyze"   # moderation
DEEPSEEK_CHAT_URL = "https://api.deepseek.com"   # chat

# ====== Intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ====== スパム判定用 ======
user_messages = defaultdict(list)
SPAM_THRESHOLD = 5       # 秒
SPAM_COUNT = 3           # 連投回数
TIMEOUT_DURATION = 60    # 秒

# ============================
# DeepSeek: 荒らし判定 (リトライ付き)
# ============================
def is_toxic(text: str, threshold: float = 0.6) -> bool:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {"text": text, "model": "moderation"}
    for attempt in range(3):
        try:
            r = requests.post(DEEPSEEK_MOD_URL, json=data, headers=headers, timeout=5)
            r.raise_for_status()
            result = r.json()
            score = result.get("toxicity", 0.0)  # スコア取得
            print(f"[DEBUG] Toxicity score: {score}")
            return score >= threshold
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} – DeepSeek moderation error:", e)
            time.sleep(1)
    return False  # 3回失敗なら安全側で False

# ============================
# DeepSeek: チャット応答 (リトライ付き)
# ============================
def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7,
    }
    for attempt in range(3):
        try:
            r = requests.post(DEEPSEEK_CHAT_URL, json=data, headers=headers, timeout=10)
            r.raise_for_status()
            result = r.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} – DeepSeek chat error:", e)
            time.sleep(1)
    return "⚠️ AI応答に失敗しました（ネットワークエラー）"

# ============================
# スラッシュコマンド
# ============================
@bot.tree.command(name="ping", description="動作確認: Pong! を返します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="help", description="このBOTの使い方を表示します")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- `/ping` : 動作確認
- `/help` : このヘルプを表示
- メンション : AI チャット開始
"""
    await interaction.response.send_message(help_text)

# ============================
# 起動時
# ============================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンド {len(synced)} 件同期しました")
    except Exception as e:
        print("Slash command sync error:", e)

    print(f"Logged in as {bot.user} — READY")

# ============================
# メッセージ処理
# ============================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ---- AI荒らし判定 ----
    if is_toxic(message.content):
        try:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} 🚫 荒らしメッセージを検知しました。"
            )
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except Exception as e:
            print("Failed to delete toxic message:", e)
        return

    # ---- スパム（短時間の連投） ----
    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間の連続投稿は禁止です。")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except Exception as e:
            print("Timeout error:", e)
        return

    # ---- URL スパム ----
    if any(word in message.content for word in ["http://", "https://"]):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} リンクスパムは禁止です！")
        except:
            pass

    # ---- 画像スパム ----
    if message.attachments and len(message.attachments) > 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 画像の大量投稿は禁止です！")
        except:
            pass

    # ---- BOTメンションでAIチャット ----
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# ============================
# メイン
# ============================
if __name__ == "__main__":
    bot.run(TOKEN)