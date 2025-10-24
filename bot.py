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
GOROKU_FILE = "goroku.csv"
RATIO_FILE = "ratio.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================================
# 語録読み込み
# ================================
goroku_list = []
with open(GOROKU_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames
    if len(headers) < 2:
        print("語録CSVの列が足りません")
    else:
        for row in reader:
            word = row[headers[0]].strip()
            meaning = row[headers[1]].strip()
            if word and meaning:
                goroku_list.append({"言葉": word, "意味": meaning})

# ================================
# ratio.json読み込み
# ================================
if os.path.exists(RATIO_FILE):
    with open(RATIO_FILE, encoding="utf-8") as f:
        ratio_data = json.load(f)
else:
    ratio_data = {}

# ================================
# 起動時イベント
# ================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# ================================
# メッセージ監視（指定チャンネルで語録自動送信）
# ================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # チャンネル名で割合を取得
    ch_name = message.channel.name
    ratio = ratio_data.get(ch_name, 0)
    if ratio > 0 and random.randint(1, 100) <= ratio:
        if goroku_list:
            entry = random.choice(goroku_list)
            embed = discord.Embed(title=entry["言葉"], description=entry["意味"], color=0xff69b4)
            await message.channel.send(embed=embed)

    await bot.process_commands(message)

# ================================
# /ping
# ================================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ================================
# /画像
# ================================
@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    images = [
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Flag_of_the_Soviet_Union.svg",
        "https://upload.wikimedia.org/wikipedia/commons/3/3e/Lenin_Square_Minsk.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/17/RedSquare_Moscow.jpg"
    ]
    await interaction.response.send_message(random.choice(images))

# ================================
# /ニュース
# ================================
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

# ================================
# /dm
# ================================
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def admin_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(f"📩 管理者からのメッセージ:\n{message}")
        await interaction.response.send_message("✅ 送信しました。", ephemeral=True)
    except Exception:
        await interaction.response.send_message("❌ 送信できませんでした。", ephemeral=True)

# ================================
# /ロール付与
# ================================
@bot.tree.command(name="ロール付与", description="管理者専用: ユーザーにロールを付与します")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} に {role.name} を付与しました。", ephemeral=True)

# ================================
# /ロール削除
# ================================
@bot.tree.command(name="ロール削除", description="管理者専用: ユーザーからロールを削除します")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ {member.mention} から {role.name} を削除しました。", ephemeral=True)

# ================================
# /ロール申請
# ================================
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

# ================================
# /要望
# ================================
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

# ================================
# !yaju コマンド（そのまま）
# ================================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ================================
# /goroku ランダム送信
# ================================
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
async def goroku_cmd(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("語録が読み込まれていません。")
        return
    entry = random.choice(goroku_list)
    embed = discord.Embed(title=entry["言葉"], description=entry["意味"], color=0xff69b4)
    await interaction.response.send_message(embed=embed)

# ================================
# /goroku辞典 全語録一覧
# ================================
@bot.tree.command(name="goroku辞典", description="淫夢語録辞典を表示します")
async def goroku_dict(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("語録が読み込まれていません。")
        return
    embeds = []
    for entry in goroku_list:
        embed = discord.Embed(title=entry["言葉"], description=entry["意味"], color=0xff69b4)
        embeds.append(embed)
    for i in range(0, len(embeds), 10):
        await interaction.response.send_message(embeds=embeds[i:i+10])

# ================================
# 実行
# ================================
bot.run(TOKEN)
