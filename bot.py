import os
import time
import random
import requests
from collections import defaultdict

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from discord import ButtonStyle


# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY:
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== Bot初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
user_messages = defaultdict(list)
SPAM_THRESHOLD = 30    # 秒
SPAM_COUNT = 6         # 連投回数
TIMEOUT_DURATION = 3600  # リンクスパムタイムアウト1時間

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
]

# ==================== DeepSeek API ====================
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat"

def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {"model": "deepseek-chat",
            "messages": [{"role": "user", "content": message_text}],
            "temperature": 0.7}
    try:
        r = requests.post(DEEPSEEK_CHAT_URL, headers=headers, json=data, timeout=10)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI応答に失敗しました"

# ==================== ニュース ====================
def fetch_news(query="日本"):
    url = f"https://gnews.io/api/v4/search?q={query}&lang=ja&token={GNEWS_API_KEY}&max=5"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return "\n".join([f"{a['title']}: {a['url']}" for a in articles])
    except:
        return "ニュース取得に失敗しました"

# ==================== 起動時 ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ スラッシュコマンド同期完了")
    print(f"Logged in as {bot.user} — READY")

# ==================== スパム・リンクスパム監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = time.time()
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    # 短時間連投
    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間の連続投稿は禁止です。")
            await message.author.timeout(duration=300)
        except:
            pass
        return

    # Discord招待リンク
    if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} クソスパマーをブロックしました。")
            await message.author.timeout(duration=TIMEOUT_DURATION)
            # 管理者用解除ボタン
            class UnTimeoutView(View):
                def __init__(self):
                    super().__init__(timeout=None)
                @discord.ui.button(label="タイムアウト解除", style=ButtonStyle.green)
                async def unt(self, button, inter):
                    if not inter.user.guild_permissions.administrator:
                        await inter.response.send_message("権限なし", ephemeral=True)
                        return
                    await message.author.remove_timeout()
                    await inter.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)
            await message.channel.send(view=UnTimeoutView())
        except:
            pass
        return

    # MURさん 夜中腹減んないすか？
    if "MURさん 夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")
        return

    # BOTメンションでAI応答
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# ==================== !yaju コマンド（誰でも使用可能） ====================
@bot.command(name="yaju")
async def yaju(ctx, user_id: int, count: int = 1):
    try:
        user = await bot.fetch_user(user_id)
        msg_to_send = "||||"*10
        for _ in range(count):
            await user.send(msg_to_send)
        await ctx.send(f"✅ {user} に DM を {count} 回送信しました")
    except Exception as e:
        await ctx.send(f"❌ DM送信に失敗しました: {e}")

# ==================== /dm コマンド（管理者のみ） ====================
@bot.tree.command(name="dm", description="管理者: 任意ユーザーにDM送信")
@app_commands.describe(user="送信対象", message="内容")
async def dm(interaction: discord.Interaction, user: discord.User, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("権限なし", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user} に送信しました")
    except Exception as e:
        await interaction.response.send_message(f"❌ 送信失敗: {e}")

# ==================== /ニュース ====================
@bot.tree.command(name="ニュース", description="最新ニュース取得")
@app_commands.describe(query="検索ワード")
async def news(interaction: discord.Interaction, query: str = "日本"):
    await interaction.response.send_message(fetch_news(query))

# ==================== /画像 ====================
@bot.tree.command(name="画像", description="ソビエト画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== ロール管理 ====================
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

# ==================== ロール申請 ====================
@bot.tree.command(name="ロール申請", description="希望するロールを申請")
@app_commands.describe(role="希望ロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        def __init__(self):
            super().__init__(timeout=None)
        @discord.ui.button(label="承認", style=ButtonStyle.green)
        async def approve(self, button: Button, button_interaction: discord.Interaction):
            if not button_interaction.user.guild_permissions.manage_roles:
                await button_interaction.response.send_message("権限なし", ephemeral=True)
                return
            member = interaction.guild.get_member(interaction.user.id)
            if member:
                await member.add_roles(role)
                await button_interaction.response.edit_message(content=f"✅ {member.display_name} に {role.name} 付与済", view=None)
            self.stop()
        @discord.ui.button(label="拒否", style=ButtonStyle.red)
        async def reject(self, button: Button, button_interaction: discord.Interaction):
            await button_interaction.response.edit_message(content=f"❌ {interaction.user.display_name} の申請拒否", view=None)
            self.stop()
    await interaction.response.send_message(f"{interaction.user.display_name} が {role.name} を申請", view=RoleApproveView())

# ==================== /help ====================
@bot.tree.command(name="help", description="ヘルプ表示")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- /ping : 動作確認
- /help : このヘルプ
- /ニュース [キーワード] : 最新ニュース取得
- /画像 : ソビエト画像ランダム表示
- /ロール付与 : 管理者用
- /ロール削除 : 管理者用
- /ロール申請 : ロール申請
- !yaju <ユーザーID> <回数> : 誰でもDM送信
- /dm : 管理者専用DM送信
"""
    await interaction.response.send_message(help_text)

# ==================== 起動 ====================
bot.run(TOKEN)
