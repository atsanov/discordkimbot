import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Modal, TextInput
from datetime import datetime, timedelta, timezone
import aiohttp
import csv
from dotenv import load_dotenv

# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN:
    raise ValueError("❌ BOTトークンが設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム監視 ====================
user_messages = {}
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 1500
TIMEOUT_DURATION = 3600  # 秒

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Yuri_Andropov.jpg/120px-Yuri_Andropov.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Kosygin_1970.jpg/120px-Kosygin_1970.jpg"
]

# ==================== CSV 読み込み (淫夢語録) ====================
GOROKU_FILE = "goroku.csv"
goroku_list = []
if os.path.exists(GOROKU_FILE):
    with open(GOROKU_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("語録") and row.get("使用方法"):
                goroku_list.append({
                    "word": row["語録"],
                    "usage": row["使用方法"],
                    "note": row.get("備考","")
                })

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# ==================== 起動時イベント ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — READY")

# ==================== スラッシュコマンド ====================
# /ping
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency*1000)}ms")

# /画像
@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# /help
@bot.tree.command(name="help", description="コマンド一覧")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "/ping - 動作確認\n"
        "/画像 - ソ連画像をランダム表示\n"
        "/ニュース - 最新ニュース取得\n"
        "/dm - 管理者専用DM送信\n"
        "/goroku - 管理者専用淫夢語録一覧\n"
        "/ロール付与 - 管理者: ユーザーにロール付与\n"
        "/ロール削除 - 管理者: ユーザーからロール削除\n"
        "/ロール申請 - 希望ロールを申請\n"
        "/宣伝設置 - 管理者専用: 宣伝ボタン設置\n"
        "!yaju - 任意メッセージ連投"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# /ニュース
@bot.tree.command(name="ニュース", description="最新ニュースを取得")
async def news(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with aiohttp.ClientSession() as session:
        url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=3"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                articles = data.get("articles", [])
                if not articles:
                    await interaction.followup.send("ニュースを取得できませんでした")
                    return
                msg = "\n\n".join([f"📰 **{a.get('title','')}**\n{a.get('url','')}" for a in articles])
                await interaction.followup.send(msg)
        except Exception as e:
            await interaction.followup.send(f"ニュース取得中にエラー: {e}")

# /dm (管理者専用)
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDM送信")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return
    try:
        await user.send(f"📩 管理者 {interaction.user} からのメッセージ:\n{message}")
        await interaction.response.send_message(f"✅ 送信完了: {user.display_name}", ephemeral=True)
    except Exception:
        await interaction.response.send_message("❌ DM送信失敗", ephemeral=True)

# /goroku (管理者専用)
@bot.tree.command(name="goroku", description="管理者専用: 淫夢語録一覧")
async def goroku_command(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return
    if not goroku_list:
        await interaction.response.send_message("❌ 読み込める語録がありません", ephemeral=True)
        return
    embed = discord.Embed(title="📜 淫夢語録一覧", color=0xFF69B4)
    for g in goroku_list:
        embed.add_field(name=g["word"], value=f"使用方法: {g['usage']}\n備考: {g['note']}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# /ロール付与 / ロール削除
@bot.tree.command(name="ロール付与", description="管理者: ユーザーにロール付与")
@app_commands.describe(user="対象ユーザー", role="付与するロール")
async def role_add(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return
    await user.add_roles(role)
    await interaction.response.send_message(f"✅ {user.display_name} に {role.name} 付与")

@bot.tree.command(name="ロール削除", description="管理者: ユーザーからロール削除")
@app_commands.describe(user="対象ユーザー", role="削除するロール")
async def role_remove(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return
    await user.remove_roles(role)
    await interaction.response.send_message(f"✅ {user.display_name} から {role.name} 削除")

# /ロール申請
@bot.tree.command(name="ロール申請", description="希望ロールを申請")
@app_commands.describe(role="希望ロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        @discord.ui.button(label="承認", style=discord.ButtonStyle.success)
        async def approve(self, button, i: discord.Interaction):
            if not is_admin(i.user):
                await i.response.send_message("❌ 権限なし", ephemeral=True)
                return
            await interaction.user.add_roles(role)
            await i.response.edit_message(content=f"✅ {interaction.user.display_name} に {role.name} 付与済", view=None)

        @discord.ui.button(label="拒否", style=discord.ButtonStyle.danger)
        async def reject(self, button, i: discord.Interaction):
            if not is_admin(i.user):
                await i.response.send_message("❌ 権限なし", ephemeral=True)
                return
            await i.response.edit_message(content=f"❌ {interaction.user.display_name} の申請拒否", view=None)

    await interaction.response.send_message(f"{interaction.user.mention} が `{role.name}` を申請", view=RoleApproveView())

# ==================== !yaju コマンド ====================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 自動応答
    if "MURさん 夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")
    if "ソ連画像" in message.content:
        url = random.choice(SOVIET_IMAGES)
        embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
        embed.set_image(url=url)
        await message.channel.send(embed=embed)

    # スパム・長文監視
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    is_spam = len(user_messages[uid]) >= SPAM_COUNT or len(message.content) > LONG_TEXT_LIMIT

    if is_spam or any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com"]):
        if not is_admin(message.author):
            try:
                await message.delete()
                until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
                await message.author.timeout(until_time, reason="スパム・不審リンク")
            except Exception as e:
                print(f"[ERROR] ブロック失敗: {e}")

    await bot.process_commands(message)

# ==================== 実行 ====================
bot.run(TOKEN)
