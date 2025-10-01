import os
import time
from collections import defaultdict, deque
import discord
from discord.ext import commands
from openai import OpenAI
import aiohttp
import asyncio

# =======================
# 環境変数
# =======================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", "0"))
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

if not TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("必須環境変数が設定されていません！")

# =======================
# DeepSeekクライアント
# =======================
client_ds = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# =======================
# Bot設定
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# スパム監視
# =======================
user_messages = defaultdict(lambda: deque(maxlen=6))
SPAM_THRESHOLD = 30
TIMEOUT_DURATION = 300  # 5分

# =======================
# nuke監視
# =======================
NUKE_WINDOW = 30
NUKE_THRESHOLD = 3
nuke_events = defaultdict(lambda: deque(maxlen=5))

async def log_nuke(event: str, user: discord.Member, guild: discord.Guild):
    if NUKE_LOG_CHANNEL_ID == 0:
        return
    channel = guild.get_channel(NUKE_LOG_CHANNEL_ID)
    if channel:
        await channel.send(f"⚠️ Nuke検知: {event} by {user} ({user.id})")

# =======================
# DeepSeek非同期
# =======================
async def ask_deepseek(text: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client_ds.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": text}],
                stream=False
            )
        )
        return response.choices[0].message.content
    except:
        return "⚠️ AI応答に失敗しました"

async def is_toxic(text: str, threshold=0.6) -> bool:
    loop = asyncio.get_event_loop()
    def check_sync():
        import requests
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        data = {"text": text, "model": "moderation"}
        r = requests.post("https://api.deepseek.com/lyze", json=data, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("toxicity", 0.0) >= threshold
        return False
    return await loop.run_in_executor(None, check_sync)

# =======================
# ニュース取得
# =======================
async def fetch_news(query: str, max_results=3):
    if not GNEWS_API_KEY:
        return ["⚠️ GNews APIキーが設定されていません。"]
    url = f"https://gnews.io/api/v4/search?q={query}&lang=ja&max={max_results}&apikey={GNEWS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as resp:
                data = await resp.json()
                articles = data.get("articles", [])
                return [f"**{a.get('title')}**\n{a.get('url')}" for a in articles] or ["⚠️ ニュースがありません"]
        except:
            return ["⚠️ ニュース取得に失敗しました"]

# =======================
# 起動処理
# =======================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンド {len(synced)} 件同期")
    except: pass
    print(f"Logged in as {bot.user} — READY")

# =======================
# メッセージ監視
# =======================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = time.time()
    uid = message.author.id

    # ----- スパム
    user_messages[uid].append(now)
    if len(user_messages[uid]) >= 6 and now - user_messages[uid][0] < SPAM_THRESHOLD:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🚫 短時間連投は禁止")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except: pass
        return

    # ----- リンクスパム
    if sum(1 for w in message.content.split() if w.startswith("http")) >= 6:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🚫 リンクスパムは禁止")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except: pass
        return

    # ----- 画像スパム
    if message.attachments and len(message.attachments) > 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 🚫 画像スパムは禁止")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except: pass
        return

    # ----- DeepSeekチャット
    if bot.user in message.mentions:
        reply = await ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# =======================
# スラッシュコマンド
# =======================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="news", description="ニュース取得")
async def news(interaction: discord.Interaction, query: str):
    results = await fetch_news(query)
    await interaction.response.send_message("\n\n".join(results))

@bot.tree.command(name="role_add", description="ロール付与")
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"{member.mention} に {role.name} を付与しました")
    except Exception as e:
        await interaction.response.send_message(f"エラー: {e}")

@bot.tree.command(name="role_remove", description="ロール削除")
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"{member.mention} から {role.name} を削除しました")
    except Exception as e:
        await interaction.response.send_message(f"エラー: {e}")

@bot.tree.command(name="role_request", description="ロール申請")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.send_message(f"{interaction.user.mention} が {role.name} を申請しました")

# =======================
# nuke監視: チャンネル削除
# =======================
@bot.event
async def on_guild_channel_delete(channel):
    user = channel.guild.owner  # 検知対象: オーナー以外に変更可能
    now = time.time()
    nuke_events[channel.guild.id].append(now)
    times = nuke_events[channel.guild.id]
    if len(times) >= NUKE_THRESHOLD and times[-1] - times[0] < NUKE_WINDOW:
        await log_nuke("大量チャンネル削除", user, channel.guild)

# =======================
# BOT起動
# =======================
bot.run(TOKEN)
