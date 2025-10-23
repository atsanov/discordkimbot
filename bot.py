import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
from datetime import datetime, timedelta, timezone

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))  # Guild単位同期用

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY or not GUILD_ID:
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
LONG_TEXT_THRESHOLD = 300  # 文字数で長文判定
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
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Yuri_Andropov_1983.jpg/120px-Yuri_Andropov_1983.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Leonid_Brezhnev_1973.jpg/120px-Leonid_Brezhnev_1973.jpg"
]

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

async def timeout_member(member: discord.Member, reason: str, channel: discord.TextChannel, content: str):
    try:
        until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
        await member.timeout(until_time, reason=reason)

        embed = discord.Embed(
            title="🚫 クソスパマーをブロックしました。",
            description=f"{member.mention} を1時間タイムアウトしました\n理由: {reason}\n検知メッセージ: {content}",
            color=0xff0000
        )

        class UnTimeoutView(View):
            @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
            async def untout(self, button, interaction):
                if not is_admin(interaction.user):
                    await interaction.response.send_message("❌ 権限なし", ephemeral=True)
                    return
                await member.remove_timeout()
                await interaction.response.edit_message(content=f"{member.mention} のタイムアウトを解除しました", view=None)

        await channel.send(embed=embed, view=UnTimeoutView())
    except Exception as e:
        print(f"[ERROR] ブロック失敗: {e}")

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ニュースコマンド（例としてGNEWS API使用）
@bot.tree.command(name="ニュース", description="最新ニュース取得")
async def news_command(interaction: discord.Interaction):
    # API呼び出しは省略、ダミーで返す
    embed = discord.Embed(title="📰 最新ニュース", description="ここにニュースを表示", color=0x00ff00)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="コマンド一覧")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "/ping - 動作確認\n"
        "/画像 - ソ連画像をランダム表示\n"
        "/ニュース - 最新ニュース取得\n"
        "/dm - 管理者専用DM送信\n"
        "/ロール付与 - 管理者: ユーザーにロール付与\n"
        "/ロール削除 - 管理者: ユーザーからロール削除\n"
        "/ロール申請 - 希望ロールを申請\n"
        "/宣伝設置 - 管理者専用: 宣伝ボタン設置\n"
        "!yaju - 任意メッセージの連投"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# 管理者DM
@bot.tree.command(name="dm", description="管理者: 指定ユーザーにDM送信")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user.display_name} にDM送信完了", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {user.display_name} にDM送信できません", ephemeral=True)

# !yaju
@bot.command(name="yaju")
async def yaju(ctx, user: discord.User=None, count: int=1):
    content = "|||||"*10
    try:
        if user:
            for _ in range(count):
                await user.send(content)
        else:
            for _ in range(count):
                await ctx.send(content)
    except discord.Forbidden:
        await ctx.send("❌ DM送信できません")

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # スパム監視
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    long_text_spam = len(message.content) >= LONG_TEXT_THRESHOLD

    if len(user_messages[uid]) >= SPAM_COUNT or long_text_spam or any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com"]):
        await message.delete()
        reason = "短時間連投" if len(user_messages[uid]) >= SPAM_COUNT else ("長文" if long_text_spam else "不審リンク")
        await timeout_member(message.author, reason, message.channel, message.content)
        return

    await bot.process_commands(message)

# ==================== 起動 ====================
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Logged in as {bot.user} — READY")

bot.run(TOKEN)
