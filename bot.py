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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 語録データ読み込み =====
GOROKU_FILE = "goroku.csv"
RATIO_FILE = "ratio.json"

goroku_list = []
with open(GOROKU_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["言葉"] and row["意味"]:
            goroku_list.append({"言葉": row["言葉"], "意味": row["意味"]})

try:
    with open(RATIO_FILE, encoding="utf-8") as f:
        ratio_data = json.load(f)
except Exception:
    ratio_data = {}

# ===== 起動時イベント =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# ===== /ping =====
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ===== /画像 =====
@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    images = [
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Flag_of_the_Soviet_Union.svg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3e/Lenin_Square_Minsk.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/17/RedSquare_Moscow.jpg"
    ]
    await interaction.response.send_message(random.choice(images))

# ===== /ニュース =====
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

# ===== /dm =====
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def admin_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(f"📩 管理者からのメッセージ:\n{message}")
        await interaction.response.send_message("✅ 送信しました。", ephemeral=True)
    except Exception:
        await interaction.response.send_message("❌ 送信できませんでした。", ephemeral=True)

# ===== /ロール付与 =====
@bot.tree.command(name="ロール付与", description="管理者専用: ユーザーにロールを付与します")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} に {role.name} を付与しました。", ephemeral=True)

# ===== /ロール削除 =====
@bot.tree.command(name="ロール削除", description="管理者専用: ユーザーからロールを削除します")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} から {role.name} を削除しました。", ephemeral=True)

# ===== /ロール申請 =====
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

# ===== /要望 =====
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

# ===== /goroku =====
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(channel_name="#チャンネル名", ratio="表示割合（整数パーセント）")
async def goroku_cmd(interaction: discord.Interaction, channel_name: str, ratio: int):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return
    channel = discord.utils.get(guild.text_channels, name=channel_name.replace("#",""))
    if not channel:
        await interaction.response.send_message("❌ チャンネルが見つかりません", ephemeral=True)
        return

    ratio = max(0, min(100, ratio))
    count = max(1, round(len(goroku_list) * (ratio / 100)))
    selected = random.sample(goroku_list, count)

    embed = discord.Embed(title="淫夢語録", color=discord.Color.red())
    for g in selected:
        embed.add_field(name=g["言葉"], value=g["意味"], inline=False)

    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ {channel.mention} に語録を送信しました", ephemeral=True)

# ===== /goroku辞典 =====
@bot.tree.command(name="goroku辞典", description="全ての淫夢語録を表示します")
async def goroku_dict(interaction: discord.Interaction):
    embed = discord.Embed(title="淫夢語録辞典", color=discord.Color.blue())
    for g in goroku_list:
        embed.add_field(name=g["言葉"], value=g["意味"], inline=False)
    await interaction.response.send_message(embed=embed)

# ===== !yaju コマンド =====
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ===== 実行 =====
bot.run(TOKEN)
