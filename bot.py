import os
import time
import random
import requests
from collections import defaultdict

import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle
from discord.ui import Button, View

# ====== 環境変数 ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

# ====== Bot 初期化 ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== スパム管理 ======
user_messages = defaultdict(list)
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
TIMEOUT_DURATION = 300  # 5分

# ====== ソ連画像 ======
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    # 以下略
]

# =======================
# DeepSeek API (AI応答)
# =======================
def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7,
    }
    try:
        r = requests.post("https://api.deepseek.com/v1/chat", headers=headers, json=data, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI応答に失敗しました"

# =======================
# ニュース取得
# =======================
def fetch_news():
    url = f"https://gnews.io/api/v4/top-headlines?lang=ja&token={GNEWS_API_KEY}&max=5"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return "\n".join([f"{a['title']}: {a['url']}" for a in articles])
    except:
        return "ニュース取得に失敗しました"

# =======================
# スラッシュコマンド
# =======================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="help", description="ヘルプ表示")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 コマンド一覧
- /ping : 動作確認
- /help : このヘルプ
- /ニュース : 最新ニュース表示
- /画像 : ソ連画像召喚
- /ロール付与 : 管理者用
- /ロール削除 : 管理者用
- /ロール申請 : ロール申請
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name="ニュース", description="最新ニュース取得")
async def news(interaction: discord.Interaction):
    await interaction.response.send_message(fetch_news())

@bot.tree.command(name="画像", description="ソ連画像表示")
async def soviet_image(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(SOVIET_IMAGES))

# =======================
# ロール付与/削除（管理者）
# =======================
@app_commands.checks.has_permissions(manage_roles=True)
@bot.tree.command(name="ロール付与", description="管理者: ユーザーにロール付与")
@app_commands.describe(user="対象ユーザー", role="付与するロール")
async def role_add(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.add_roles(role)
        await interaction.response.send_message(f"✅ {user.display_name} に {role.name} を付与")
    except Exception as e:
        await interaction.response.send_message(f"❌ 付与失敗: {e}")

@app_commands.checks.has_permissions(manage_roles=True)
@bot.tree.command(name="ロール削除", description="管理者: ユーザーからロール削除")
@app_commands.describe(user="対象ユーザー", role="削除するロール")
async def role_remove(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.remove_roles(role)
        await interaction.response.send_message(f"✅ {user.display_name} から {role.name} を削除")
    except Exception as e:
        await interaction.response.send_message(f"❌ 削除失敗: {e}")

# =======================
# ロール申請
# =======================
@bot.tree.command(name="ロール申請", description="ユーザーが希望するロールを申請")
@app_commands.describe(role="希望ロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    approve = Button(label="承認", style=ButtonStyle.green)
    reject = Button(label="拒否", style=ButtonStyle.red)
    async def approve_callback(i: discord.Interaction):
        if not i.user.guild_permissions.manage_roles:
            await i.response.send_message("権限なし", ephemeral=True)
            return
        await interaction.user.add_roles(role)
        await i.response.edit_message(content=f"{interaction.user.display_name} に {role.name} 付与済", view=None)
    async def reject_callback(i: discord.Interaction):
        if not i.user.guild_permissions.manage_roles:
            await i.response.send_message("権限なし", ephemeral=True)
            return
        await i.response.edit_message(content=f"{interaction.user.display_name} の申請拒否", view=None)
    approve.callback = approve_callback
    reject.callback = reject_callback
    view = View()
    view.add_item(approve)
    view.add_item(reject)
    await interaction.response.send_message(f"{interaction.user.display_name} が {role.name} を申請", view=view)

# =======================
# メッセージ監視（スパム・リンクスパム）
# =======================
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
            await message.author.timeout(duration=TIMEOUT_DURATION)
            await message.channel.send(f"{message.author.mention} 短時間連投は禁止")
        except:
            pass

    # リンクスパム
    if message.content.count("http") >= 6:
        try:
            await message.delete()
            await message.author.timeout(duration=TIMEOUT_DURATION)
            await message.channel.send(f"{message.author.mention} リンクスパム禁止")
        except:
            pass

    # BOTメンションでAI応答
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")

    await bot.process_commands(message)

# =======================
# 起動処理
# =======================
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("✅ スラッシュコマンド同期完了")
    except Exception as e:
        print(e)
    print(f"Logged in as {bot.user}")

if __name__ == "__main__":
    bot.run(TOKEN)
