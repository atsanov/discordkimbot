import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import json
import csv
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# =====================
# Bot 定義
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =====================
# データ読み込み
# =====================
GOROKU_CSV = "goroku.csv"
RATIO_JSON = "ratio.json"

goroku_list = []
try:
    with open(GOROKU_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "言葉" in row and "意味" in row:
                goroku_list.append({"言葉": row["言葉"], "意味": row["意味"]})
except FileNotFoundError:
    print("goroku.csv が見つかりません。")

try:
    with open(RATIO_JSON, encoding="utf-8") as f:
        ratio_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ratio_data = {}

# =====================
# 起動時イベント
# =====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# =====================
# /goroku コマンド
# =====================
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(
    channel="対象チャンネル（#チャンネル形式）",
    percentage="メッセージに応じて出す割合（%）"
)
async def send_goroku(interaction: discord.Interaction, channel: discord.TextChannel, percentage: int):
    if percentage < 0 or percentage > 100:
        await interaction.response.send_message("❌ 割合は0～100の整数で指定してください", ephemeral=True)
        return

    count = ratio_data.get(str(channel.id), 0)  # 前回メッセージカウント
    ratio_data[str(channel.id)] = count + 1

    # 指定割合に応じて出すか判定
    if random.randint(1, 100) <= percentage:
        entry = random.choice(goroku_list)
        embed = discord.Embed(title=entry["言葉"], description=entry["意味"], color=0xff0000)
        await channel.send(embed=embed)

    await interaction.response.send_message(f"✅ 語録を判定しました（現在のカウント: {ratio_data[str(channel.id)]}）", ephemeral=True)

    # ratio.json 更新
    with open(RATIO_JSON, "w", encoding="utf-8") as f:
        json.dump(ratio_data, f, ensure_ascii=False, indent=2)

# =====================
# /goroku辞典 コマンド
# =====================
@bot.tree.command(name="goroku辞典", description="淫夢語録の辞典を表示します")
async def goroku_dictionary(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("❌ 語録が読み込まれていません", ephemeral=True)
        return

    embeds = []
    for entry in goroku_list:
        embed = discord.Embed(title=entry["言葉"], description=entry["意味"], color=0xff0000)
        embeds.append(embed)

    for embed in embeds:
        await interaction.response.send_message(embed=embed)

# =====================
# !yaju コマンド
# =====================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# =====================
# 実行
# =====================
bot.run(TOKEN)

