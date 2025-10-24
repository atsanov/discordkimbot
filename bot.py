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

# =====================================================
# JSONファイル読み込み（ratio.json）
# =====================================================
RATIO_JSON = "ratio.json"
ratio_data = {}
if os.path.exists(RATIO_JSON):
    if os.path.getsize(RATIO_JSON) > 0:
        with open(RATIO_JSON, encoding="utf-8") as f:
            ratio_data = json.load(f)
    else:
        ratio_data = {}
else:
    ratio_data = {}

# =====================================================
# CSVファイル読み込み（goroku.csv）
# =====================================================
GOROKU_CSV = "goroku.csv"
goroku_list = []
if os.path.exists(GOROKU_CSV):
    with open(GOROKU_CSV, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                goroku_list.append({"言葉": row[0], "名前": row[1], "意味": row[2]})

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
# /要望
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
# /goroku
# 淫夢語録をメッセージ回数と割合でランダム表示
# =====================================================
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(channel_id="対象チャンネルID", percentage="メッセージに応じて出す割合（%）")
async def send_goroku(interaction: discord.Interaction, channel_id: int, percentage: int):
    guild = interaction.guild
    channel = guild.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message("❌ チャンネルが見つかりません", ephemeral=True)
        return

    # メッセージ回数取得
    count = 0
    async for _ in channel.history(limit=None):
        count += 1

    # ratio_data の更新
    if str(channel_id) not in ratio_data:
        ratio_data[str(channel_id)] = 0
    ratio_data[str(channel_id)] += count

    # 確率で出すか判定
    if random.randint(1, 100) <= percentage:
        if goroku_list:
            entry = random.choice(goroku_list)
            await channel.send(f"{entry['言葉']} — {entry['名前']} ({entry['意味']})")
        else:
            await channel.send("❌ goroku.csv が読み込まれていません。")
    else:
        await channel.send("今回は語録を送信しませんでした。")

    # JSON保存
    with open(RATIO_JSON, "w", encoding="utf-8") as f:
        json.dump(ratio_data, f, ensure_ascii=False, indent=4)

# =====================================================
# !yaju コマンド（従来のまま）
# =====================================================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# =====================================================
# 実行
# =====================================================
bot.run(TOKEN)
