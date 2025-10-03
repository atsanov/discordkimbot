import os
import time
import random
import requests
from collections import defaultdict
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY:
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== DeepSeek API ====================
DEEPSEEK_CHAT_URL = "https://api.deepseek.com"

def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7,
    }
    try:
        r = requests.post(f"{DEEPSEEK_CHAT_URL}/v1/chat", json=data, headers=headers, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI応答に失敗しました"

# ==================== Discord Bot ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム・nuke対策 ====================
user_messages = defaultdict(list)
SPAM_THRESHOLD = 30    # 秒
SPAM_COUNT = 6         # 連投回数
TIMEOUT_DURATION = 300 # 秒（5分）

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg"
]

# ==================== ロール申請管理 ====================
ROLE_REQUESTS = {}  # message_id: (user_id, role_id)

# ==================== ヘルプ ====================
@bot.tree.command(name="help", description="このBOTの使い方を表示します")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- `/ping` : 動作確認
- `/help` : このヘルプを表示
- `/ニュース [キーワード]` : 最新ニュースを取得
- `/画像` : ソビエト画像をランダムで表示
- `/ロール付与` : ロール付与権限者のみ
- `/ロール削除` : ロール付与権限者のみ
- `/ロール申請` : ユーザーのロール申請
"""
    await interaction.response.send_message(help_text)

# ==================== Ping ====================
@bot.tree.command(name="ping", description="動作確認: Pong! を返します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# ==================== ソ連画像 ====================
@bot.tree.command(name="画像", description="ソビエト画像をランダムで表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== ニュース機能 ====================
@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
@app_commands.describe(query="検索ワード（省略可能）")
async def news_command(interaction: discord.Interaction, query: str = "日本"):
    await interaction.response.defer()
    url = f"https://gnews.io/api/v4/search?q={query}&lang=ja&token={GNEWS_API_KEY}&max=5"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles", [])
        if not articles:
            await interaction.followup.send("🔍 ニュースが見つかりませんでした。")
            return
        embed = discord.Embed(title=f"📰 {query} に関する最新ニュース", color=0x00ff00)
        for a in articles:
            title = a.get("title")
            link = a.get("url")
            source = a.get("source", {}).get("name", "")
            embed.add_field(name=f"{title} ({source})", value=link, inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ ニュース取得に失敗しました: {e}")

# ==================== メッセージ処理 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間の連続投稿は禁止です。")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except:
            pass
        return

    if message.content.count("http") >= 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} リンクスパムは禁止です！")
        except:
            pass
        return

    if message.attachments and len(message.attachments) > 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 画像の大量投稿は禁止です！")
        except:
            pass
        return

    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# ==================== ロール申請 ====================
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
@app_commands.describe(role="希望するロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="承認", style=discord.ButtonStyle.success)
        async def approve(self, button: Button, button_interaction: discord.Interaction):
            if not button_interaction.user.guild_permissions.manage_roles:
                await button_interaction.response.send_message("❌ 権限がありません", ephemeral=True)
                return
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                try:
                    await member.add_roles(role)
                    await button_interaction.response.send_message(f"✅ {member.display_name} にロールを付与しました")
                except:
                    await button_interaction.response.send_message("❌ ロール付与に失敗しました")
            self.stop()

        @discord.ui.button(label="拒否", style=discord.ButtonStyle.danger)
        async def reject(self, button: Button, button_interaction: discord.Interaction):
            await button_interaction.response.send_message("❌ ロール申請が拒否されました")
            self.stop()

    await interaction.response.send_message(f"{interaction.user.mention} が `{role.name}` ロールを申請しました", view=RoleApproveView())

# ==================== 起動 ====================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンド {len(synced)} 件同期")
    except Exception as e:
        print("Slash command sync error:", e)
    print(f"Logged in as {bot.user} — READY")

bot.run(TOKEN)

