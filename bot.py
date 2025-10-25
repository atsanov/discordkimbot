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
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
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

# ==================== CSV 読み込み ====================
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
else:
    print("⚠ goroku.csv が存在しません。")

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# =====================================================
# 起動時イベント
# =====================================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="コマンド一覧")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "/ping - 動作確認\n"
        "/画像 - ソ連画像をランダム表示\n"
        "/ニュース - 最新ニュース取得\n"
        "/dm - 管理者専用DM送信\n"
        "/goroku - 管理者専用: 語録一覧\n"
        "/ロール付与 - 管理者: ユーザーにロール付与\n"
        "/ロール削除 - 管理者: ユーザーからロール削除\n"
        "/ロール申請 - 希望ロールを申請\n"
        "/宣伝設置 - 管理者専用: 宣伝ボタン設置\n"
        "!yaju - 任意メッセージの連投\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ==================== 管理者専用語録表示 ====================
@bot.tree.command(name="goroku", description="管理者専用: 語録一覧を表示")
async def goroku_command(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
        return

    if not goroku_list:
        await interaction.response.send_message("❌ 読み込める語録がありません", ephemeral=True)
        return

    embed = discord.Embed(title="📜 淫夢語録一覧", color=0xFF69B4)
    for entry in goroku_list:
        embed.add_field(name=entry["word"], value=f"使用方法: {entry['usage']}\n備考: {entry['note']}", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== ニュース ====================
@bot.tree.command(name="ニュース", description="最新ニュースを取得")
async def news(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with aiohttp.ClientSession() as session:
        url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=5"
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                articles = data.get("articles", [])[:3]
                if not articles:
                    await interaction.followup.send("ニュースを取得できませんでした。")
                    return
                msg = "\n\n".join([f"📰 **{a.get('title','')}**\n{a.get('url','')}" for a in articles])
                await interaction.followup.send(msg)
        except Exception as e:
            await interaction.followup.send(f"ニュース取得中にエラー: {e}")

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

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
                embed = discord.Embed(
                    title="🚫 クソスパマーをブロックしました。",
                    description=f"{message.author.mention} を1時間タイムアウトしました\n理由: {'長文' if len(message.content) > LONG_TEXT_LIMIT else 'スパム・不審リンク'}\n検知メッセージ: {message.content}",
                    color=0xff0000
                )
                until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
                await message.author.timeout(until_time, reason="スパム・不審リンク")

                # タイムアウト解除ボタン
                class UnTimeoutView(View):
                    @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
                    async def untout(self, button, interaction: discord.Interaction):
                        if not is_admin(interaction.user):
                            await interaction.response.send_message("❌ 権限なし", ephemeral=True)
                            return
                        await message.author.remove_timeout()
                        await interaction.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)

                await message.channel.send(embed=embed, view=UnTimeoutView())

                # ログ
                if NUKE_LOG_CHANNEL_ID:
                    log_ch = bot.get_channel(NUKE_LOG_CHANNEL_ID)
                    if log_ch:
                        await log_ch.send(f"{message.author} をタイムアウト: {message.content}")

            except Exception as e:
                print(f"[ERROR] ブロック失敗: {e}")

    await bot.process_commands(message)

# ==================== !yaju コマンド ====================
@bot.command(name="yaju")
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ==================== 起動 ====================
bot.run(TOKEN)
