import os
import random
import time
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

if not TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== 設定 ====================
SPAM_THRESHOLD = 30       # 秒
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 1500    # 文字
TIMEOUT_DURATION = 3600   # 秒
user_messages = {}

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg"
]

# ==================== 淫夢語録 ====================
GOROKU_LIST = [
    {"word": "ｱｰｲｷｿ", "usage": "イキそうな時に", "note": "半角で表記"},
    {"word": "あーソレいいよ", "usage": "賛辞を贈る際に", "note": "野獣が遠野にイチモツをしゃぶらせた時の感想"},
    {"word": "アイスティーしかなかったんだけどいいかな", "usage": "", "note": ""},
    {"word": "頭にきますよ!!", "usage": "頭にきた時", "note": "MURにシャワーをかける時の空耳"},
    {"word": "暴れんなよ…暴れんなよ…", "usage": "暴れてる相手を制止したい時", "note": ""},
    {"word": "ありますあります", "usage": "自分に経験があるとき", "note": ""},
    {"word": "114514", "usage": "相手の誘いを受け入れる時", "note": "読みは「いいよ、来いよ」"},
    {"word": "イキスギィ!", "usage": "絶頂の直前になったとき", "note": ""},
    {"word": "痛いですね…これは痛い", "usage": "痛い時", "note": ""},
    {"word": "王道を征く", "usage": "", "note": "王者の風格"},
    {"word": "おかのした", "usage": "仕事を任された時", "note": ""},
    {"word": "お前の事が好きだったんだよ!", "usage": "気持ちを告白する時", "note": ""},
    {"word": "†悔い改めて†", "usage": "何かを戒める時に", "note": ""}
]

# ==================== 管理者判定 ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# ==================== 起動 ====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="ping", description="Botの応答確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency*1000)}ms")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="goroku", description="淫夢語録をランダム表示")
async def goroku(interaction: discord.Interaction):
    entry = random.choice(GOROKU_LIST)
    embed = discord.Embed(title=entry["word"], description=f"使用: {entry['usage']}\n備考: {entry['note']}", color=0x00FF00)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="コマンド一覧")
async def help_cmd(interaction: discord.Interaction):
    text = (
        "/ping - 動作確認\n"
        "/画像 - ソ連画像表示\n"
        "/goroku - 淫夢語録表示\n"
        "/ニュース - 最新ニュース表示\n"
        "/dm - 管理者専用DM\n"
        "!yaju - メッセージ連投"
    )
    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="dm", description="管理者専用DM送信")
@app_commands.describe(user="送信先ユーザー", message="送信内容")
async def dm(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者専用です", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user} に送信しました", ephemeral=True)
    except:
        await interaction.response.send_message("❌ DM送信失敗", ephemeral=True)

@bot.tree.command(name="ニュース", description="最新のニュースを取得します（GNews）")
@app_commands.describe(キーワード="検索したいニュースキーワード")
async def news(interaction: discord.Interaction, キーワード: str = "Japan"):
    await interaction.response.defer()
    if not GNEWS_API_KEY:
        await interaction.followup.send("❌ GNEWS_API_KEY が設定されていません。")
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://gnews.io/api/v4/search?q={キーワード}&lang=ja&max=3&apikey={GNEWS_API_KEY}"
            ) as resp:
                data = await resp.json()
                if "articles" not in data or not data["articles"]:
                    await interaction.followup.send("ニュースが見つかりませんでした。")
                    return
                embed = discord.Embed(title=f"📰 最新ニュース ({キーワード})", color=0x00AAFF)
                for art in data["articles"]:
                    embed.add_field(name=art["title"], value=art["url"], inline=False)
                await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ ニュース取得失敗: {e}")

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

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
                await message.author.timeout(until_time, reason="スパム・リンク・長文")
                embed = discord.Embed(
                    title="🚫 クソスパマーをブロックしました。",
                    description=f"{message.author.mention} を1時間タイムアウトしました。",
                    color=0xff0000
                )
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"[ERROR] タイムアウト失敗: {e}")

    await bot.process_commands(message)

# ==================== 実行 ====================
bot.run(TOKEN)
