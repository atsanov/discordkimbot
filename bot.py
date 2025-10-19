import os
import time
import random
import requests
from collections import defaultdict

import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import Button, View

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY:
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム監視 ====================
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

# ==================== DeepSeek AI応答 ====================
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat"

def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7,
    }
    try:
        r = requests.post(DEEPSEEK_CHAT_URL, json=data, headers=headers, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result["choices"][0]["message"]["content"]
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
            return "ニュースが見つかりませんでした"
        return "\n".join([f"{a['title']}: {a['url']}" for a in articles])
    except:
        return "ニュース取得に失敗しました"

# ==================== スラッシュコマンド ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — READY")

@bot.tree.command(name="help", description="ヘルプ表示")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- /ping : 動作確認
- /help : ヘルプ表示
- /ニュース [キーワード] : 最新ニュースを取得
- /画像 : ソ連画像をランダムで表示
- /dm : 管理者専用DM送信
- /yaju : 誰でも使えるヤジュDM
- /ロール申請 : ロール申請（承認ボタン付き）
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="ニュース", description="最新ニュース取得")
@app_commands.describe(query="検索ワード（省略可能）")
async def news_command(interaction: discord.Interaction, query: str = "日本"):
    await interaction.response.send_message(fetch_news(query))

@bot.tree.command(name="画像", description="ソ連画像をランダムで表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソ連画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== 管理者専用DM ====================
@bot.tree.command(name="dm", description="管理者: 指定ユーザーにメッセージを送信")
@app_commands.describe(user="対象ユーザー", message="送信内容")
async def admin_dm(interaction: discord.Interaction, user: discord.User, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user.display_name} にDM送信しました")
    except:
        await interaction.response.send_message("❌ DM送信に失敗しました")

# ==================== 誰でも使えるYAJU DM ====================
@bot.tree.command(name="yaju", description="誰でも使えるDM送信")
@app_commands.describe(user="対象ユーザー", message="送信内容")
async def yaju_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user.display_name} にDM送信しました")
    except:
        await interaction.response.send_message("❌ DM送信に失敗しました")

# ==================== ロール申請 ====================
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
@app_commands.describe(role="希望するロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="承認", style=ButtonStyle.success)
        async def approve(self, button: Button, button_interaction: discord.Interaction):
            if not button_interaction.user.guild_permissions.manage_roles:
                await button_interaction.response.send_message("❌ 権限なし", ephemeral=True)
                return
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                try:
                    await member.add_roles(role)
                    await button_interaction.response.send_message(f"✅ {member.display_name} にロールを付与")
                except:
                    await button_interaction.response.send_message("❌ ロール付与失敗")
            self.stop()

        @discord.ui.button(label="拒否", style=ButtonStyle.danger)
        async def reject(self, button: Button, button_interaction: discord.Interaction):
            await button_interaction.response.send_message("❌ ロール申請拒否")
            self.stop()

    await interaction.response.send_message(f"{interaction.user.mention} が `{role.name}` ロールを申請しました", view=RoleApproveView())

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # スパム監視
    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間連投は禁止")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except:
            pass
        return

    # リンクスパム
    if message.content.count("http") >= 6:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} リンクスパムは禁止です！")
        except:
            pass
        return

    # 画像大量投稿
    if message.attachments and len(message.attachments) > 2:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 画像の大量投稿は禁止です！")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except:
            pass
        return

    # BOTメンションでAI応答
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# ==================== 起動 ====================
bot.run(TOKEN)
