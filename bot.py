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

# ================================
# ファイルパス
# ================================
GOROKU_FILE = "goroku.csv"
RATIO_FILE = "ratio.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================================
# ratio.json読み込み（空ファイル or 非存在時対応）
# ================================
ratio_data = {}
if os.path.exists(RATIO_FILE):
    try:
        with open(RATIO_FILE, encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                ratio_data = json.loads(content)
            else:
                ratio_data = {}
    except json.JSONDecodeError:
        print("⚠ ratio.jsonが無効です。空の辞書を使用します。")
        ratio_data = {}

# ================================
# goroku.csv読み込み（言葉・意味）
# ================================
goroku_list = []
if os.path.exists(GOROKU_FILE):
    with open(GOROKU_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "言葉" in row and "意味" in row and row["言葉"] and row["意味"]:
                goroku_list.append({"word": row["言葉"], "meaning": row["意味"]})

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

# =====================================================
# /ping
# =====================================================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# =====================================================
# /画像
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
# /ニュース
# =====================================================
@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
async def news(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with aiohttp.ClientSession() as session:
        async with session.get("https://newsdata.io/api/1/news?country=jp&apikey=pub_34002fe3") as resp:
            data = await resp.json()
            if "results" in data:
                articles = data["results"][:3]
                msg = "\n\n".join([f"📰 **{a['title']}**\n{a.get('link','')}" for a in articles])
                await interaction.followup.send(msg)
            else:
                await interaction.followup.send("ニュースを取得できませんでした。")

# =====================================================
# /dm
# =====================================================
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def admin_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(f"📩 管理者からのメッセージ:\n{message}")
        await interaction.response.send_message("✅ 送信しました。", ephemeral=True)
    except Exception:
        await interaction.response.send_message("❌ 送信できませんでした。", ephemeral=True)

# =====================================================
# /ロール付与
# =====================================================
@bot.tree.command(name="ロール付与", description="管理者専用: ユーザーにロールを付与します")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} に {role.name} を付与しました。", ephemeral=True)

# =====================================================
# /ロール削除
# =====================================================
@bot.tree.command(name="ロール削除", description="管理者専用: ユーザーからロールを削除します")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} から {role.name} を削除しました。", ephemeral=True)

# =====================================================
# /ロール申請
# =====================================================
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
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
    await interaction.response.send_message("✅ 申請を送信しました。", ephemeral=True)

# =====================================================
# /要望（新機能）
# =====================================================
@bot.tree.command(name="要望", description="管理者に要望を送信します")
@app_commands.describe(message="送信したい要望内容")
async def request_to_admin(interaction: discord.Interaction, message: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です", ephemeral=True)
        return
    admin_members = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
    if not admin_members:
        await interaction.response.send_message("❌ 管理者が見つかりません", ephemeral=True)
        return
    dm_content = f"📩 **{interaction.user}** から要望が届きました:\n```\n{message}\n```"
    sent_count = 0
    for admin in admin_members:
        try:
            await admin.send(dm_content)
            sent_count += 1
        except discord.Forbidden:
            continue
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に要望を送信しました。", ephemeral=True)

# =====================================================
# !yaju コマンド（そのまま残す）
# =====================================================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# =====================================================
# /goroku コマンド（淫夢語録埋め込み・意味付き）
# =====================================================
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(channel="投稿先チャンネル（#チャンネル名形式）", ratio="送信割合（整数％）")
async def send_goroku(interaction: discord.Interaction, channel: str, ratio: int = 100):
    # チャンネル取得
    if not interaction.guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return
    if not channel.startswith("#"):
        await interaction.response.send_message("❌ #チャンネル名で指定してください", ephemeral=True)
        return
    channel_name = channel[1:]
    dest_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
    if not dest_channel:
        await interaction.response.send_message(f"❌ チャンネル「{channel}」が見つかりません", ephemeral=True)
        return

    # ratioチェック
    if ratio < 0 or ratio > 100:
        await interaction.response.send_message("❌ 送信割合は0〜100の整数で指定してください", ephemeral=True)
        return

    # 送信
    messages_sent = 0
    for entry in goroku_list:
        if random.randint(1, 100) <= ratio:
            embed = discord.Embed(title=entry["word"], description=entry["meaning"], color=0xFF69B4)
            await dest_channel.send(embed=embed)
            messages_sent += 1

    await interaction.response.send_message(f"✅ {messages_sent}件の淫夢語録を送信しました", ephemeral=True)

# =====================================================
# /goroku辞典（全表示）
# =====================================================
@bot.tree.command(name="goroku_dict", description="淫夢語録辞典を表示します")
async def goroku_dict(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("❌ 読み込める語録がありません", ephemeral=True)
        return
    embeds = []
    for entry in goroku_list:
        embed = discord.Embed(title=entry["word"], description=entry["meaning"], color=0xFF69B4)
        embeds.append(embed)
    for embed in embeds:
        await interaction.response.send_message(embed=embed)

# =====================================================
# 実行
# =====================================================
bot.run(TOKEN)
