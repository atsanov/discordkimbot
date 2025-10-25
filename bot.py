import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Modal, TextInput
from datetime import datetime, timedelta, timezone
import aiohttp
import csv
import json
from dotenv import load_dotenv

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

# ==================== スパム・長文監視 ====================
user_messages = {}
SPAM_THRESHOLD = 30       # 秒
SPAM_COUNT = 6            # この数以上でスパム判定
LONG_TEXT_LIMIT = 1500    # 長文判定
TIMEOUT_DURATION = 3600   # タイムアウト時間（秒）

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/9/9b/Flag_of_the_Soviet_Union.svg",
    "https://upload.wikimedia.org/wikipedia/commons/3/3e/Lenin_Square_Minsk.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/17/RedSquare_Moscow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
]

# ==================== 淫夢語録 ====================
GOROKU_FILE = "goroku.csv"
goroku_list = []
if os.path.exists(GOROKU_FILE):
    with open(GOROKU_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "言葉" in row and "意味" in row and row["言葉"] and row["意味"]:
                goroku_list.append({"word": row["言葉"], "meaning": row["意味"]})

# ==================== ratio.json ====================
RATIO_FILE = "ratio.json"
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

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# ==================== 起動時イベント ====================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} — READY")
    await bot.tree.sync()
    print(f"✅ Slash commands synced")

# ==================== /ping ====================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ==================== /画像 ====================
@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
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
            if resp.status != 200:
                await interaction.followup.send(f"❌ ニュース取得失敗: {resp.status}")
                return
            data = await resp.json()
            articles = data.get("articles", [])
            if not articles:
                await interaction.followup.send("❌ ニュースが見つかりませんでした")
                return
            embed = discord.Embed(title="📰 最新ニュース", color=0x00ff00)
            for a in articles:
                title = a.get("title", "タイトルなし")
                desc = a.get("description", "説明なし")
                url_article = a.get("url")
                embed.add_field(name=title, value=f"{desc}\n[リンク]({url_article})", inline=False)
            await interaction.followup.send(embed=embed)

# ==================== /goroku ====================
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(channel="投稿先チャンネル（#チャンネル名形式）", ratio="送信割合（整数％）")
async def send_goroku(interaction: discord.Interaction, channel: str, ratio: int = 100):
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
    if ratio < 0 or ratio > 100:
        await interaction.response.send_message("❌ 送信割合は0〜100で指定してください", ephemeral=True)
        return

    messages_sent = 0
    for entry in goroku_list:
        if random.randint(1,100) <= ratio:
            embed = discord.Embed(title=entry["word"], description=entry["meaning"], color=0xFF69B4)
            await dest_channel.send(embed=embed)
            messages_sent += 1
    await interaction.response.send_message(f"✅ {messages_sent}件の淫夢語録を送信しました", ephemeral=True)

# ==================== !yaju ====================
@bot.command()
async def yaju(ctx, *, message: str = "やりますねぇ"):
    for _ in range(5):
        await ctx.send(message)

# ==================== ロール申請・承認・拒否 ====================
@bot.tree.command(name="ロール申請", description="希望ロールを申請")
@app_commands.describe(role="希望ロール")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    class RoleApproveView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="承認", style=discord.ButtonStyle.success)
        async def approve(self, button, i: discord.Interaction):
            if not is_admin(i.user):
                await i.response.send_message("❌ 権限なし", ephemeral=True)
                return
            await interaction.user.add_roles(role)
            await i.response.edit_message(content=f"✅ {interaction.user.display_name} に {role.name} 付与済", view=None)
            self.stop()

        @discord.ui.button(label="拒否", style=discord.ButtonStyle.danger)
        async def reject(self, button, i: discord.Interaction):
            if not is_admin(i.user):
                await i.response.send_message("❌ 権限なし", ephemeral=True)
                return
            await i.response.edit_message(content=f"❌ {interaction.user.display_name} の申請拒否", view=None)
            self.stop()

    await interaction.response.send_message(f"{interaction.user.mention} が `{role.name}` を申請", view=RoleApproveView())

# ==================== 宣伝ボタン設置 ====================
@bot.tree.command(name="宣伝設置", description="管理者専用: 宣伝ボタン設置")
@app_commands.describe(channel="宣伝を設置するチャンネル")
async def setup_promo(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return

    class PromoView(View):
        @discord.ui.button(label="宣伝する", style=discord.ButtonStyle.blurple)
        async def promo_button(self, button, i: discord.Interaction):
            class PromoModal(Modal):
                def __init__(self):
                    super().__init__(title="宣伝入力")
                    self.message_input = TextInput(label="宣伝内容", style=discord.TextStyle.long)
                    self.add_item(self.message_input)

                async def on_submit(self, modal_interaction: discord.Interaction):
                    await channel.send(f"📢 宣伝: {self.message_input.value}")
                    # ログ
                    if LOG_CHANNEL_ID:
                        log_ch = bot.get_channel(LOG_CHANNEL_ID)
                        if log_ch:
                            await log_ch.send(f"{i.user} が宣伝を実行: {self.message_input.value}")
                    await modal_interaction.response.send_message("✅ 宣伝送信完了", ephemeral=True)

            await i.response.send_modal(PromoModal())

    await channel.send("📢 宣伝ボタン設置完了", view=PromoView())
    await interaction.response.send_message(f"{channel.mention} に宣伝ボタンを設置しました", ephemeral=True)

# ==================== 要望送信 ====================
@bot.tree.command(name="要望", description="管理者に要望を送信します")
@app_commands.describe(message="送信したい要望内容")
async def request_to_admin(interaction: discord.Interaction, message: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です", ephemeral=True)
        return

    admin_members = [m for m in guild.members if is_admin(m) and not m.bot]
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

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 自動応答
    if "MURさん 夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")
    if "ソ連画像" in message.content:
        url = random.choice(SOVIET_IMAGES)
        embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
        embed.set_image(url=url)
        await message.channel.send(embed=embed)

    # スパム・長文・不審リンク検知
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    is_spam = len(user_messages[uid]) >= SPAM_COUNT
    is_long = len(message.content) > LONG_TEXT_LIMIT
    is_suspicious = any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com"])

    if (is_spam or is_long or is_suspicious) and not is_admin(message.author):
        try:
            await message.delete()
            embed = discord.Embed(
                title="🚫 クソスパマーをブロックしました。",
                description=f"{message.author.mention} を1時間タイムアウトしました\n理由: {'長文' if is_long else 'スパム・不審リンク'}\n検知メッセージ: {message.content}",
                color=0xff0000
            )
            until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
            await message.author.timeout(until_time, reason="スパム・不審リンク・長文")

            class UnTimeoutView(View):
                @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
                async def untout(self, button, i: discord.Interaction):
                    if not is_admin(i.user):
                        await i.response.send_message("❌ 権限なし", ephemeral=True)
                        return
                    await message.author.remove_timeout()
                    await i.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)

            await message.channel.send(embed=embed, view=UnTimeoutView())

            # ログ送信
            if NUKE_LOG_CHANNEL_ID:
                log_ch = bot.get_channel(NUKE_LOG_CHANNEL_ID)
                if log_ch:
                    await log_ch.send(f"{message.author} をタイムアウト: {message.content}")

        except Exception as e:
            print(f"[ERROR] ブロック失敗: {e}")

    await bot.process_commands(message)

# ==================== 実行 ====================
bot.run(TOKEN)
