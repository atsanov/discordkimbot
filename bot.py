import os
import time
import random
import requests
from collections import defaultdict

import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import View, Button

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
INVITE_TIMEOUT_DURATION = 3600  # 招待リンクタイムアウト1時間

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY:
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== Bot初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
user_messages = defaultdict(list)
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
TIMEOUT_DURATION = 300  # 秒

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
]

# ==================== DeepSeek API ====================
def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {"model": "deepseek-chat", "messages":[{"role":"user","content":message_text}], "temperature":0.7}
    try:
        r = requests.post("https://api.deepseek.com/v1/chat", headers=headers, json=data, timeout=10)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI応答に失敗しました"

# ==================== ニュース取得 ====================
def fetch_news(query="日本"):
    url = f"https://gnews.io/api/v4/search?q={query}&lang=ja&token={GNEWS_API_KEY}&max=5"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        if not articles:
            return "🔍 ニュースが見つかりません"
        return "\n".join([f"{a['title']}: {a['url']}" for a in articles])
    except:
        return "ニュース取得に失敗しました"

# ==================== 起動時 ====================
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"✅ スラッシュコマンド {len(synced)} 件同期")
    print(f"Logged in as {bot.user} — READY")

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 「MURさん 夜中腹減んないすか？」応答
    if "MURさん 夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")
        return

    # スパム監視
    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)
    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.author.timeout(duration=TIMEOUT_DURATION)
            await message.channel.send(f"{message.author.mention} 短時間連投は禁止です")
        except:
            pass
        return

    # 招待リンクスパム
    if "discord.gg" in message.content or "discord.com/invite" in message.content:
        try:
            await message.delete()
            await message.author.timeout(duration=INVITE_TIMEOUT_DURATION)
            class UnbanView(View):
                def __init__(self, member: discord.Member):
                    super().__init__(timeout=None)
                    self.member = member
                @discord.ui.button(label="タイムアウト解除", style=ButtonStyle.green)
                async def untimeout(self, button: Button, i: discord.Interaction):
                    if not i.user.guild_permissions.manage_messages:
                        await i.response.send_message("❌ 権限なし", ephemeral=True)
                        return
                    try:
                        await self.member.timeout(duration=0)
                        await i.response.edit_message(content=f"{self.member.display_name} のタイムアウトを解除しました", view=None)
                    except:
                        await i.response.send_message("❌ 解除失敗", ephemeral=True)
            await message.channel.send(f"{message.author.mention} クソスパマーをブロックしました", view=UnbanView(message.author))
        except:
            pass
        return

    # BOTメンションでAI応答
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    # !yajuコマンド
    if message.content.startswith("!yaju"):
        parts = message.content.split()
        if len(parts) >= 3:
            try:
                target_id = int(parts[1])
                count = int(parts[2])
                target = await bot.fetch_user(target_id)
                msg_to_send = "||||" * 10
                for _ in range(count):
                    await target.send(msg_to_send)
                await message.channel.send(f"{target.name} に送信しました")
            except:
                await message.channel.send("❌ 送信失敗")
        return

    await bot.process_commands(message)

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="dm", description="管理者: 指定ユーザーにDM送信")
@app_commands.describe(user="対象ユーザー", message="送信メッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user.display_name} に送信しました")
    except:
        await interaction.response.send_message("❌ 送信失敗")

# ==================== その他スラッシュコマンド ====================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="help", description="ヘルプ表示")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- /ping : 動作確認
- /help : このヘルプ
- /ニュース : 最新ニュース取得
- /画像 : ソ連画像表示
- /dm : 管理者専用DM
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name="ニュース", description="最新ニュース取得")
async def news_command(interaction: discord.Interaction):
    await interaction.response.send_message(fetch_news())

@bot.tree.command(name="画像", description="ソ連画像表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== Bot起動 ====================
bot.run(TOKEN)
