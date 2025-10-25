import os
import random
import discord
from discord.ext import commands
from discord import app_commands, ui
from datetime import datetime, timedelta, timezone
import aiohttp
import asyncio
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
import time

# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

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

SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg"
]

GOROKU_LIST = [
    {"word": "ｱｰｲｷｿ", "usage": "イキそうな時に", "note": "半角で表記"},
    {"word": "あーソレいいよ", "usage": "賛辞を贈る際に", "note": ""},
    {"word": "暴れんなよ…暴れんなよ…", "usage": "暴れてる相手を制止したい時", "note": ""}
]

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

@bot.tree.command(name="ニュース", description="最新ニュース取得")
@app_commands.describe(キーワード="検索キーワード")
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

# ==================== スパム監視 ====================
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
                await message.channel.send(f"🚫 {message.author.mention} を1時間タイムアウトしました。")
            except Exception as e:
                print(f"[ERROR] タイムアウト失敗: {e}")

    await bot.process_commands(message)

# ==================== !yaju ====================
@bot.command(name="yaju")
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ==================== 2048ゲーム ====================
class Game2048View(ui.View):
    def __init__(self, board=None):
        super().__init__(timeout=None)
        self.board = board or [[0]*4 for _ in range(4)]
        self.add_random()
        self.add_random()

    def add_random(self):
        empty = [(r,c) for r in range(4) for c in range(4) if self.board[r][c]==0]
        if empty:
            r,c = random.choice(empty)
            self.board[r][c] = random.choice([2,4])

    def board_image(self):
        img = Image.new("RGB",(400,400),(250,248,239))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        for r in range(4):
            for c in range(4):
                val = self.board[r][c]
                color = (200,200,200) if val==0 else (255-10*val,255-5*val,200)
                draw.rectangle([c*100,r*100,(c+1)*100,(r+1)*100], fill=color)
                if val:
                    w,h = draw.textsize(str(val),font=font)
                    draw.text((c*100+50-w/2,r*100+50-h/2),str(val),fill=(0,0,0),font=font)
        buf = io.BytesIO()
        img.save(buf,format="PNG")
        buf.seek(0)
        return buf

    async def update_message(self, interaction):
        self.add_random()
        img = self.board_image()
        file = discord.File(img,filename="board.png")
        embed = discord.Embed(title="2048ゲーム",color=0x00ff00)
        embed.set_image(url="attachment://board.png")
        await interaction.response.edit_message(embed=embed,attachments=[file],view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True  # 全員操作可能

# スラッシュ開始コマンド
@bot.tree.command(name="2048", description="2048ゲームを開始")
async def start_2048(interaction: discord.Interaction):
    view = Game2048View()
    img = view.board_image()
    file = discord.File(img,filename="board.png")
    embed = discord.Embed(title="2048ゲーム", color=0x00ff00)
    embed.set_image(url="attachment://board.png")
    await interaction.response.send_message(embed=embed, file=file, view=view)

# ==================== 実行 ====================
bot.run(TOKEN)
