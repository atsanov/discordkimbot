# ============================================================
#  Discord × Google Gemini 統合Bot（完全版 / 省略なし）
# ============================================================

import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
from datetime import datetime, timedelta, timezone
import aiohttp
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
from google import genai
from google.genai import types
from io import BytesIO

# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not TOKEN or not GOOGLE_API_KEY:
    raise ValueError("❌ 必須環境変数（DISCORD_BOT_TOKEN, GOOGLE_API_KEY）が設定されていません")

# ==================== Google Gemini Client ====================
client = genai.Client(api_key=GOOGLE_API_KEY)

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

# ==================== /help ====================
@bot.tree.command(name="help", description="Botのコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Botコマンド一覧", color=0x00ff00)
    embed.add_field(name="/ping", value="Botの応答速度を確認します", inline=False)
    embed.add_field(name="/画像", value="ランダムにソ連画像を表示します", inline=False)
    embed.add_field(name="/ニュース", value="最新ニュースを取得します", inline=False)
    embed.add_field(name="/要望", value="管理者に要望を送信します", inline=False)
    embed.add_field(name="/2048", value="2048ゲームを開始します", inline=False)
    embed.add_field(name="/ロール付与", value="ロールを付与します", inline=False)
    embed.add_field(name="/ロール削除", value="ロールを削除します", inline=False)
    embed.add_field(name="/ロール申請", value="ロールを申請します", inline=False)
    embed.add_field(name="/dm", value="管理者専用: 指定ユーザーにDMを送信", inline=False))
    embed.add_field(name="メンション", value="Chat", inline=False)
    embed.set_footer(text="※Botの全機能を一覧で確認できます")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== /ロール付与 ====================
@bot.tree.command(name="ロール付与", description="管理者専用: ユーザーにロールを付与します")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} に {role.name} を付与しました。", ephemeral=True)

# ==================== /ロール削除 ====================
@bot.tree.command(name="ロール削除", description="管理者専用: ユーザーからロールを削除します")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} から {role.name} を削除しました。", ephemeral=True)

# ==================== /ロール申請 ====================
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
async def role_request(interaction: discord.Interaction, role_name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return

    admin_members = [m for m in guild.members if is_admin(m) and not m.bot]
    sent_count = 0
    for admin in admin_members:
        try:
            await admin.send(f"📩 **{interaction.user}** がロールを申請しました: `{role_name}`")
            sent_count += 1
        except discord.Forbidden:
            continue
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に申請を送信しました。", ephemeral=True)

# ==================== /dm 復活 ====================
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
        return

    try:
        await user.send(f"📩 管理者 {interaction.user} からのメッセージ:\n```\n{message}\n```")
        await interaction.response.send_message(f"✅ {user.mention} にDM送信しました。", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {user.mention} にDMを送信できません。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 送信失敗: {e}", ephemeral=True)

# ==================== /ping ====================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ==================== /画像 ====================
@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== /ニュース ====================
@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
async def news(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            articles = data.get("articles", [])
            if not articles:
                await interaction.followup.send("ニュースを取得できませんでした。")
                return
            msg = "\n\n".join([f"📰 **{a.get('title','タイトルなし')}**\n{a.get('url','')}" for a in articles])
            await interaction.followup.send(msg)

# ==================== /要望 ====================
@bot.tree.command(name="要望", description="管理者に要望を送信します")
@app_commands.describe(message="送信したい要望内容")
async def request_to_admin(interaction: discord.Interaction, message: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です", ephemeral=True)
        return
    admin_members = [m for m in guild.members if is_admin(m) and not m.bot]
    sent_count = 0
    for admin in admin_members:
        try:
            await admin.send(f"📩 **{interaction.user}** から要望が届きました:\n```\n{message}\n```")
            sent_count += 1
        except discord.Forbidden:
            continue
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に要望を送信しました。", ephemeral=True)

# ==================== !yaju ====================
bot.remove_command("yaju")
@bot.command()
async def yaju(ctx, *, message: str = "|||||||||||||||||||||||||||||||||||||"*10):
    for _ in range(5):
        await ctx.send(message)



# ==================== 2048ゲーム Cog ====================
class Game2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    def new_board(self):
        board = [[0]*4 for _ in range(4)]
        self.add_tile(board)
        self.add_tile(board)
        return board

    def add_tile(self, board):
        empty = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        board[r][c] = random.choice([2,4])

    def compress(self, row):
        new_row = [i for i in row if i != 0]
        new_row += [0]*(4-len(new_row))
        return new_row

    def merge(self, row):
        for i in range(3):
            if row[i] != 0 and row[i] == row[i+1]:
                row[i] *= 2
                row[i+1] = 0
        return row

    def move_left(self, board):
        return [self.compress(self.merge(self.compress(row))) for row in board]

    def reverse(self, board):
        return [list(reversed(row)) for row in board]

    def transpose(self, board):
        return [list(row) for row in zip(*board)]

    def move_right(self, board):
        return self.reverse(self.move_left(self.reverse(board)))

    def move_up(self, board):
        return self.transpose(self.move_left(self.transpose(board)))

    def move_down(self, board):
        return self.transpose(self.move_right(self.transpose(board)))

    def is_game_over(self, board):
        for r in range(4):
            for c in range(4):
                if board[r][c] == 0:
                    return False
                if c<3 and board[r][c]==board[r][c+1]:
                    return False
                if r<3 and board[r][c]==board[r+1][c]:
                    return False
        return True

    def render_board_image(self, board):
        tile_colors = {0:(204,192,179),2:(238,228,218),4:(237,224,200),8:(242,177,121),
                       16:(245,149,99),32:(246,124,95),64:(246,94,59),128:(237,207,114),
                       256:(237,204,97),512:(237,200,80),1024:(237,197,63),2048:(237,194,46)}
        img = Image.new("RGB",(400,400),(187,173,160))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf",36)
        except:
            font = ImageFont.load_default()
        for r in range(4):
            for c in range(4):
                val = board[r][c]
                color = tile_colors.get(val,(60,58,50))
                x, y = c*100+10, r*100+10
                draw.rounded_rectangle([x,y,x+80,y+80],8,fill=color)
                if val:
                    text=str(val)
                    w,h=draw.textsize(text,font=font)
                    draw.text((x+40-w/2, y+40-h/2), text, fill=(0,0,0), font=font)
        buffer = io.BytesIO()
        img.save(buffer,format="PNG")
        buffer.seek(0)
        return buffer

    async def send_board(self, ctx, board):
        img = self.render_board_image(board)
        file = discord.File(fp=img, filename="2048.png")
        msg = await ctx.send(file=file)
        return msg

    @commands.hybrid_command(name="2048", description="2048ゲームを開始します")
    async def start_game(self, ctx):
        board = self.new_board()
        self.active_games[ctx.author.id] = board
        msg = await self.send_board(ctx, board)
        for emoji in ["⬆️","⬇️","⬅️","➡️"]:
            await msg.add_reaction(emoji)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬆️","⬇️","⬅️","➡️"] and reaction.message.id == msg.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=120.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send("⌛ ゲーム終了（操作がありませんでした）")
                del self.active_games[ctx.author.id]
                await msg.clear_reactions()
                break

            old_board = [row[:] for row in board]
            if str(reaction.emoji) == "⬆️":
                board = self.move_up(board)
            elif str(reaction.emoji) == "⬇️":
                board = self.move_down(board)
            elif str(reaction.emoji) == "⬅️":
                board = self.move_left(board)
            elif str(reaction.emoji) == "➡️":
                board = self.move_right(board)

            if board != old_board:
                self.add_tile(board)

            img = self.render_board_image(board)
            file = discord.File(fp=img, filename="2048.png")
            await msg.edit(content=None, attachments=[file])
            await msg.remove_reaction(reaction.emoji, user)

            if self.is_game_over(board):
                await ctx.send(f"💀 ゲームオーバー！ {ctx.author.mention}")
                del self.active_games[ctx.author.id]
                await msg.clear_reactions()
                break

# ==================== Google Gemini 応答機能 ====================
async def gemini_reply(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text if hasattr(response, "text") else "（AI応答を取得できませんでした）"
    except Exception as e:
        return f"⚠️ Geminiエラー: {e}"

# ==================== メッセージ監視・AI応答 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # BOTへのリプライまたはメンションに反応
    if message.reference and message.reference.resolved and message.reference.resolved.author == bot.user:
        query = message.content
        async with message.channel.typing():
            ai_response = await gemini_reply(query)
        await message.reply(ai_response)
        return

    if bot.user in message.mentions:
        query = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if query:
            async with message.channel.typing():
                ai_response = await gemini_reply(query)
            await message.reply(ai_response)
            return

    await bot.process_commands(message)

# ==================== 起動イベント ====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

async def main():
    async with bot:
        await bot.add_cog(Game2048(bot))
        await bot.start(TOKEN)

asyncio.run(main())
