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
YAJU_OWNER_ID = int(os.getenv("YAJU_OWNER_ID", 0))

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
TIMEOUT_DURATION = 300  # 5分

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
]

# ==================== DeepSeek API ====================
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat"

def ask_deepseek(message_text: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7
    }
    try:
        r = requests.post(DEEPSEEK_CHAT_URL, json=data, headers=headers, timeout=10)
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
        return "\n".join([f"{a['title']}: {a['url']}" for a in articles])
    except:
        return "ニュース取得に失敗しました"

# ==================== スラッシュコマンド ====================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンド {len(synced)} 件同期")
    except Exception as e:
        print("Slash command sync error:", e)
    print(f"Logged in as {bot.user} — READY")

@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="help", description="このBOTの使い方を表示")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- /ping : 動作確認
- /help : ヘルプ表示
- /ニュース [キーワード] : 最新ニュース取得
- /画像 : ソビエト画像表示
- /ロール申請 : ロールを申請
- /ロール付与 : 管理者用
- /ロール削除 : 管理者用
- /DM : 管理者が任意ユーザーにメッセージ送信
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name="ニュース", description="最新ニュース取得")
@app_commands.describe(query="検索ワード（省略可）")
async def news_command(interaction: discord.Interaction, query: str = "日本"):
    await interaction.response.send_message(fetch_news(query))

@bot.tree.command(name="画像", description="ソ連画像表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== 管理者専用ロール付与/削除 ====================
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
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
@app_commands.describe(role="希望するロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="承認", style=ButtonStyle.success)
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

        @discord.ui.button(label="拒否", style=ButtonStyle.danger)
        async def reject(self, button: Button, button_interaction: discord.Interaction):
            await button_interaction.response.send_message("❌ ロール申請が拒否されました")
            self.stop()

    await interaction.response.send_message(f"{interaction.user.mention} が `{role.name}` を申請しました", view=RoleApproveView())

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ==================== YAJU DM（誰でも使用可） ====================
    if message.content.startswith("!yaju"):
        parts = message.content.split()
        if len(parts) == 3:
            try:
                target_id = int(parts[1])
                count = int(parts[2])
                target = await bot.fetch_user(target_id)
                msg_to_send = "||||" * 200
                for _ in range(count):
                    await target.send(msg_to_send)
                await message.channel.send(f"✅ {target} に DM を {count} 回送信しました")
            except Exception as e:
                await message.channel.send(f"❌ DM送信エラー: {e}")

    # ==================== スパム監視 ====================
    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)
    if len(user_messages[uid]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} 短時間連投は禁止です")
            await message.author.timeout(duration=TIMEOUT_DURATION)
        except:
            pass
        return

    if message.content.count("http") >= 6:
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

    # ==================== 特定フレーズ反応 ====================
    if "MURさん夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")
        return

    # ==================== BOTメンションでAI応答 ====================
    if bot.user in message.mentions:
        reply = ask_deepseek(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    await bot.process_commands(message)

# ==================== /DM コマンド（管理者専用） ====================
@app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="DM", description="管理者: 指定ユーザーにメッセージを送信")
@app_commands.describe(user="送信先ユーザー", content="メッセージ内容")
async def dm_command(interaction: discord.Interaction, user: discord.User, content: str):
    try:
        await user.send(content)
        await interaction.response.send_message(f"✅ {user} に DM を送信しました")
    except Exception as e:
        await interaction.response.send_message(f"❌ DM送信失敗: {e}")

# ==================== 起動 ====================
bot.run(TOKEN)
