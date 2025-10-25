import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import aiohttp
import csv
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

GOROKU_FILE = "goroku.csv"
RATIO_FILE = "ratio.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# ratio.json 読み込み
# =====================================================
ratio_data = {}
if os.path.exists(RATIO_FILE):
    try:
        with open(RATIO_FILE, encoding="utf-8") as f:
            content = f.read().strip()
            ratio_data = json.loads(content) if content else {}
    except json.JSONDecodeError:
        print("⚠ ratio.jsonが壊れています。空で続行。")
        ratio_data = {}

# =====================================================
# goroku.csv 読み込み（言葉・意味）
# =====================================================
goroku_list = []
if os.path.exists(GOROKU_FILE):
    with open(GOROKU_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "言葉" in row and "意味" in row and row["言葉"] and row["意味"]:
                goroku_list.append({"word": row["言葉"], "meaning": row["意味"]})

# =====================================================
# 起動
# =====================================================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}個のコマンドを同期しました")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# =====================================================
# /ping
# =====================================================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# =====================================================
# /画像（変更禁止）
# =====================================================
@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    images = [
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Flag_of_the_Soviet_Union.svg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3e/Lenin_Square_Minsk.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/17/RedSquare_Moscow.jpg"
    ]
    await interaction.response.send_message(random.choice(images))

# =====================================================
# /ニュース（GNEWS API）
# =====================================================
@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
async def news(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://gnews.io/api/v4/top-headlines?lang=ja&country=jp&max=3&apikey={GNEWS_API_KEY}"
            ) as resp:
                data = await resp.json()
                if "articles" not in data:
                    await interaction.followup.send("❌ ニュースを取得できませんでした。")
                    return

                msg = "\n\n".join([
                    f"📰 **{a['title']}**\n{a.get('url','')}" for a in data["articles"]
                ])
                await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"❌ ニュース取得失敗: {e}")

# =====================================================
# /dm 管理者専用
# =====================================================
@bot.tree.command(name="dm", description="管理者専用: ユーザーにDMを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def admin_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(f"📩 管理者からのメッセージ:\n{message}")
        await interaction.response.send_message("✅ DMを送信しました。", ephemeral=True)
    except Exception:
        await interaction.response.send_message("❌ DM送信に失敗しました。", ephemeral=True)

# =====================================================
# /ロール申請
# =====================================================
@bot.tree.command(name="ロール申請", description="希望ロールを申請します")
async def role_request(interaction: discord.Interaction, role_name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return
    admins = [m for m in guild.members if m.guild_permissions.administrator]
    for admin in admins:
        try:
            await admin.send(f"📩 {interaction.user} がロール「{role_name}」を申請しました。")
        except:
            pass
    await interaction.response.send_message("✅ 管理者に申請を送信しました。", ephemeral=True)

# =====================================================
# !yaju
# =====================================================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# =====================================================
# /goroku（淫夢語録送信）
# =====================================================
@bot.tree.command(name="goroku", description="淫夢語録を指定チャンネルに送信します")
@app_commands.describe(channel="投稿先チャンネル（<#チャンネルID>形式）", ratio="送信割合（0〜100）")
async def send_goroku(interaction: discord.Interaction, channel: str, ratio: int = 100):
    if not interaction.guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return

    try:
        channel_id = int(channel.strip("<#>"))
        dest_channel = bot.get_channel(channel_id)
        if not dest_channel:
            await interaction.response.send_message("❌ チャンネルが見つかりません", ephemeral=True)
            return
    except ValueError:
        await interaction.response.send_message("❌ <#チャンネルID> の形式で指定してください", ephemeral=True)
        return

    if ratio < 0 or ratio > 100:
        await interaction.response.send_message("❌ 送信割合は0〜100で指定してください", ephemeral=True)
        return

    messages_sent = 0
    for entry in goroku_list:
        if random.randint(1, 100) <= ratio:
            embed = discord.Embed(title=entry["word"], description=entry["meaning"], color=0xFF69B4)
            await dest_channel.send(embed=embed)
            messages_sent += 1

    await interaction.response.send_message(f"✅ {messages_sent}件の淫夢語録を送信しました", ephemeral=True)

# =====================================================
# /goroku_dict（淫夢語録一覧）
# =====================================================
@bot.tree.command(name="goroku_dict", description="淫夢語録一覧を表示します")
async def goroku_dict(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("❌ 読み込める語録がありません", ephemeral=True)
        return
    for entry in goroku_list:
        embed = discord.Embed(title=entry["word"], description=entry["meaning"], color=0xFF69B4)
        await interaction.response.send_message(embed=embed)

# =====================================================
# /help（コマンド一覧）
# =====================================================
@bot.tree.command(name="help", description="コマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📘 コマンド一覧", color=0x3498db)
    embed.add_field(name="/ping", value="Botの応答速度を確認", inline=False)
    embed.add_field(name="/画像", value="ソ連の画像をランダム表示", inline=False)
    embed.add_field(name="/ニュース", value="最新ニュースを取得", inline=False)
    embed.add_field(name="/goroku", value="淫夢語録を送信", inline=False)
    embed.add_field(name="/goroku_dict", value="淫夢語録一覧を表示", inline=False)
    embed.add_field(name="/dm", value="管理者専用: DM送信", inline=False)
    embed.add_field(name="/ロール申請", value="希望ロールを申請", inline=False)
    embed.add_field(name="!yaju", value="やりますねぇを連投", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# =====================================================
# スパム・長文検知（クソスパマー排除）
# =====================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if len(message.content) > 500 or message.content.count("\n") > 10:
        try:
            await message.author.ban(reason="クソスパマーをブロックしました")
            await message.channel.send(f"🚫 クソスパマーをブロックしました: {message.author.mention}")
        except:
            await message.channel.send("⚠️ スパマーをブロックできませんでした（権限不足）")
    await bot.process_commands(message)

# =====================================================
# 実行
# =====================================================
bot.run(TOKEN)
