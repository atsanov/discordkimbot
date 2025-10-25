import os
import random
import time
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Modal, TextInput
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io

# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

if not TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== 設定 ====================
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 1500
TIMEOUT_DURATION = 3600
user_messages = {}

# ==================== データ ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg",
]

GOROKU_LIST = [
    {"word": "ｱｰｲｷｿ", "usage": "イキそうな時に", "note": "半角で表記"},
    {"word": "あーソレいいよ", "usage": "賛辞を贈る際に", "note": "野獣が遠野にイチモツをしゃぶらせた時の感想"},
    {"word": "アイスティーしかなかったんだけどいいかな", "usage": "", "note": ""},
    {"word": "頭にきますよ!!", "usage": "頭にきた時", "note": "MURにシャワーをかける時の空耳"},
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
        "/2048 - 2048ゲーム\n"
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

@bot.tree.command(name="ニュース", description="最新ニュース取得（GNews）")
@app_commands.describe(キーワード="検索ワード")
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

# ==================== !yaju ====================
@bot.command(name="yaju")
async def yaju(ctx, count: int = 1):
    content = "やりますねえ！\n"
    for _ in range(min(count, 20)):
        await ctx.send(content)

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # スパム対策
    now = time.time()
    msgs = user_messages.get(message.author.id, [])
    msgs = [t for t in msgs if now - t < SPAM_THRESHOLD]
    msgs.append(now)
    user_messages[message.author.id] = msgs
    if len(msgs) > SPAM_COUNT:
        await message.channel.send(f"⚠️ {message.author.mention} スパム警告")
        try:
            await message.author.timeout(duration=TIMEOUT_DURATION, reason="スパム行為")
        except:
            pass

    # 長文監視
    if len(message.content) > LONG_TEXT_LIMIT:
        await message.channel.send(f"⚠️ {message.author.mention} 長文は投稿できません")
    
    await bot.process_commands(message)

# ==================== 2048ゲーム Cog ====================
class Game2048(discord.ui.View):
    SIZE = 4

    def __init__(self):
        super().__init__(timeout=None)
        self.board = [[0]*self.SIZE for _ in range(self.SIZE)]
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        empty = [(r,c) for r in range(self.SIZE) for c in range(self.SIZE) if self.board[r][c]==0]
        if empty:
            r,c = random.choice(empty)
            self.board[r][c] = random.choice([2]*9 + [4])

    def render_board(self):
        img = Image.new("RGB", (400,400), color=(255,255,255))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        cell_size = 100
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                val = self.board[r][c]
                x0, y0 = c*cell_size, r*cell_size
                x1, y1 = x0+cell_size, y0+cell_size
                draw.rectangle([x0,y0,x1,y1], outline=(0,0,0), width=2, fill=(200,200,200) if val==0 else (255,255,150))
                if val>0:
                    w,h = draw.textsize(str(val), font=font)
                    draw.text((x0+cell_size/2-w/2, y0+cell_size/2-h/2), str(val), fill=(0,0,0), font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    async def send_board(self, interaction: discord.Interaction):
        buf = self.render_board()
        file = discord.File(buf, filename="2048.png")
        await interaction.response.send_message("2048ゲーム", file=file, view=self)

@bot.tree.command(name="2048", description="2048ゲーム開始")
async def game_2048(interaction: discord.Interaction):
    view = Game2048()
    await view.send_board(interaction)

# ==================== Bot 起動 ====================
bot.run(TOKEN)
