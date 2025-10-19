import os
import random
import time
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
user_messages = {}
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
TIMEOUT_DURATION = 3600  # 1時間

# ==================== 危険リンク検知 ====================
BLOCK_URL_KEYWORDS = [
    "discord.gg", "bit.ly", "tinyurl.com", "is.gd", "t.co", "example-illegal-site.com"
]

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

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# ==================== ブロック処理 ====================
async def block_user(message, reason="不明"):
    try:
        embed = discord.Embed(
            title="🚫 クソスパマーをブロックしました。",
            description=f"{message.author.mention} を1時間タイムアウトしました\n理由: {reason}\n検知メッセージ: {message.content}",
            color=0xff0000
        )
        await message.channel.send(embed=embed)

        until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
        await message.author.timeout(until=until_time)

        class UnTimeoutView(View):
            @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
            async def untout(self, button: Button, interaction: discord.Interaction):
                if not is_admin(interaction.user):
                    await interaction.response.send_message("❌ 権限なし", ephemeral=True)
                    return
                try:
                    await message.author.remove_timeout()
                    await interaction.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)
                except:
                    await interaction.response.send_message("❌ 解除失敗", ephemeral=True)

        await message.channel.send(view=UnTimeoutView())
        await message.delete()
    except Exception as e:
        print(f"[ERROR] ブロック失敗: {e}")

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

    # スパム監視
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)
    if len(user_messages[uid]) >= SPAM_COUNT:
        await block_user(message, reason="短時間連投")
        return

    # 危険リンク検知
    for keyword in BLOCK_URL_KEYWORDS:
        if keyword in message.content and not is_admin(message.author):
            await block_user(message, reason="不審リンク")
            return

    await bot.process_commands(message)

# ==================== !yaju コマンド ====================
@bot.command(name="yaju")
async def yaju(ctx, user: discord.User = None, count: int = 1):
    if not user:
        await ctx.send("|||||||||||||||||||||"*10)
        return
    for _ in range(count):
        try:
            await user.send("|||||||||||||||||||||"*10)
        except:
            await ctx.send(f"❌ {user.display_name} にDM送信できません")

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

@bot.tree.command(name="dm", description="管理者: 指定ユーザーにDM送信")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
        return
    try:
        await user.send(message)
        await user.send("||||"*10)
        await interaction.response.send_message(f"✅ {user.display_name} にDM送信完了", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {user.display_name} にDM送信できません", ephemeral=True)

# ==================== /help コマンド ====================
@bot.tree.command(name="help", description="スラッシュコマンド一覧")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="/help", description="利用可能なスラッシュコマンド一覧", color=0x00ff00)
    for cmd in bot.tree.get_commands():
        embed.add_field(name=f"/{cmd.name}", value=cmd.description or "説明なし", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 起動 ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — READY")

bot.run(TOKEN)
