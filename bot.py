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

# -----------------------------
# 語録読み込み
# -----------------------------
GOROKU_CSV = "goroku.csv"
goroku_list = []
if os.path.exists(GOROKU_CSV):
    with open(GOROKU_CSV, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row:
                goroku_list.append(row[0])

# -----------------------------
# ratio.json
# -----------------------------
RATIO_JSON = "ratio.json"
if os.path.exists(RATIO_JSON):
    with open(RATIO_JSON, encoding="utf-8") as f:
        ratio_data = json.load(f)
else:
    ratio_data = {}

# -----------------------------
# 対象チャンネル
# -----------------------------
CHANNEL_JSON = "goroku_channels.json"
if os.path.exists(CHANNEL_JSON):
    with open(CHANNEL_JSON, encoding="utf-8") as f:
        goroku_channels = json.load(f)
else:
    goroku_channels = {}

# -----------------------------
# メッセージカウント
# -----------------------------
message_count = {}

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
# メッセージ監視（トリマ統合）
# =====================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    gid = str(message.guild.id)
    cid = str(message.channel.id)

    if gid in goroku_channels and cid in goroku_channels[gid]:
        count = message_count.get(cid, 0) + 1
        message_count[cid] = count

        base_chance = ratio_data.get(gid, 50)
        # メッセージ数50ごとに5%上昇、最大100%
        chance = min(base_chance + (count // 50) * 5, 100)

        # トリマ動作: ランダムで1~3語録を送信
        if goroku_list and random.randint(1, 100) <= chance:
            send_count = random.randint(1, 3)
            for _ in range(send_count):
                await message.channel.send(random.choice(goroku_list))

    await bot.process_commands(message)

# =====================================================
# /ratio
# =====================================================
@bot.tree.command(name="ratio", description="語録出現割合を設定します（0～100%）")
@app_commands.describe(value="語録が出る確率（%）")
@app_commands.checks.has_permissions(administrator=True)
async def set_ratio(interaction: discord.Interaction, value: int):
    if value < 0 or value > 100:
        await interaction.response.send_message("❌ 0～100の範囲で指定してください。", ephemeral=True)
        return
    gid = str(interaction.guild.id)
    ratio_data[gid] = value
    with open(RATIO_JSON, "w", encoding="utf-8") as f:
        json.dump(ratio_data, f, ensure_ascii=False, indent=2)
    await interaction.response.send_message(f"✅ 語録出現割合を {value}% に設定しました。", ephemeral=True)

# =====================================================
# /goroku_channel
# =====================================================
@bot.tree.command(name="goroku_channel", description="語録自動出力対象チャンネルを設定")
@app_commands.describe(channel="語録自動出力対象チャンネル")
@app_commands.checks.has_permissions(administrator=True)
async def set_goroku_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    gid = str(interaction.guild.id)
    cid = str(channel.id)
    if gid not in goroku_channels:
        goroku_channels[gid] = []
    if cid not in goroku_channels[gid]:
        goroku_channels[gid].append(cid)
    with open(CHANNEL_JSON, "w", encoding="utf-8") as f:
        json.dump(goroku_channels, f, ensure_ascii=False, indent=2)
    await interaction.response.send_message(f"✅ {channel.name} を語録自動出力対象に設定しました。", ephemeral=True)

# =====================================================
# /語録
# =====================================================
@bot.tree.command(name="語録", description="ランダムに淫夢語録を表示します")
async def send_goroku(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    chance = ratio_data.get(gid, 50)
    if goroku_list and random.randint(1, 100) <= chance:
        await interaction.response.send_message(random.choice(goroku_list))
    else:
        await interaction.response.send_message("💬 今回は語録は出ませんでした。")

# =====================================================
# !yaju
# =====================================================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# =====================================================
# 実行
# =====================================================
bot.run(TOKEN)
