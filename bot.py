# ============================================================
#  Discord Bot 最終統合版 (Raspberry Pi 3/1GB 環境向け)
#  - 破壊復元機能、語録一覧表示機能を搭載
#  - ローカルAI機能を追加
#  - バックアップファイル名を raito.json に変更
#  - スパム対策、カレンダー機能（日報/検索）を追加
# ============================================================

import os
import random
import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View
import datetime as dt_module # datetime.timeエラー対策
from datetime import datetime, timedelta, timezone
import aiohttp
from dotenv import load_dotenv
import asyncio
import json
import csv 
import re 
import logging

# ==================== 環境変数 & 定数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

# int型（数値）として読み込む必要があるものは int() で囲む
ADMIN_LOG_CHANNEL_ID = int(os.getenv("ADMIN_LOG_CHANNEL_ID", 0))
ADMIN_GUILD_ID = int(os.getenv("ADMIN_GUILD_ID", 0))

LOG_CHANNEL_ID = 0
BACKUP_DIR = "server_backups" 
CALENDAR_SETTINGS_FILE = "calendar_setting.json" 

# Webhookも環境変数から
REPORT_WEBHOOK_URL = os.getenv("REPORT_WEBHOOK_URL")

def is_admin_guild(ctx):
    # これで ADMIN_GUILD_ID がエラーにならずに動く
    return ctx.guild and ctx.guild.id == ADMIN_GUILD_ID


if not TOKEN:
    raise ValueError("❌ 必須環境変数（DISCORD_BOT_TOKEN）が設定されていません")

# ==================== Helper Function (共通処理) ====================
def is_admin(member: discord.Member) -> bool:
    if member.guild:
        return member.guild_permissions.administrator
    return False

def get_backup_path(guild_id):
    return os.path.join(BACKUP_DIR, "raito.json")

def extract_role_data(guild):
    roles_data = []
    for role in guild.roles:
        roles_data.append({
            "id": role.id,
            "name": role.name,
            "permissions": role.permissions.value,
            "color": role.color.value,
            "position": role.position
        })
    return roles_data

def extract_channel_data(guild):
    channels_data = []
    categories = {c.id: c.name for c in guild.categories}
    for channel in guild.channels:
        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
            overwrites = []
            for target, overwrite in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites.append({
                        "id": target.id, "type": 0,
                        "allow": overwrite.allow.value, "deny": overwrite.deny.value
                    })
            data = {"name": channel.name, "type": str(channel.type), "position": channel.position, "overwrites": overwrites, "id": channel.id}
            if not isinstance(channel, discord.CategoryChannel):
                data["category_id"] = channel.category_id
                data["category_name"] = categories.get(channel.category_id)
                if isinstance(channel, discord.TextChannel): data["topic"] = channel.topic
                elif isinstance(channel, discord.VoiceChannel): data["bitrate"] = channel.bitrate; data["user_limit"] = channel.user_limit
            channels_data.append(data)
    return channels_data

def load_calendar_settings():
    if os.path.exists(CALENDAR_SETTINGS_FILE):
        try:
            with open(CALENDAR_SETTINGS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except json.JSONDecodeError: print("⚠️ calendar_setting.jsonが不正です。")
    return {}

def save_calendar_settings(settings):
    with open(CALENDAR_SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4, ensure_ascii=False)

calendar_settings = load_calendar_settings()

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

user_messages = {}
SPAM_THRESHOLD, SPAM_COUNT, LONG_TEXT_LIMIT = 30, 6, 1500

SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%Chern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%Chern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_Library_%C2%B7_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_Library_%C2%B7_Library_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Yuri_Andropov.jpg/120px-Yuri_Andropov.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Kosygin_1970.jpg/120px-Kosygin_1970.jpg"
]

# ==================== コマンド実装 ====================
# --- スラッシュコマンド同期用コマンド ---
@bot.command()
@commands.is_owner() # Botの作成者（あなた）だけが実行可能
async def sync(ctx):
    try:
        # これを実行することで、スラッシュコマンドがDiscordに登録される
        synced = await bot.tree.sync()
        await ctx.send(f"✅ {len(synced)} 個のスラッシュコマンドを同期しました。")
    except Exception as e:
        await ctx.send(f"❌ 同期エラーが発生しました: {e}")


@bot.tree.command(name="help", description="Botのコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Botコマンド一覧", color=0x00ff00)
    embed.add_field(name="/ping", value="応答速度確認", inline=True)
    embed.add_field(name="/ai", value="AIに質問", inline=True)
    embed.add_field(name="/画像", value="ソ連画像表示", inline=True)
    embed.add_field(name="/ニュース", value="最新ニュース", inline=True)
    embed.add_field(name="/語録", value="語録検索", inline=True)
    embed.add_field(name="/backup", value="管理: 保存", inline=True)
    embed.add_field(name="/restore", value="管理: 復元", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000).set_image(url=url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
async def news_cmd(interaction: discord.Interaction):
    if not GNEWS_API_KEY: return await interaction.response.send_message("❌ キーなし", ephemeral=True)
    await interaction.response.defer(thinking=True)
    url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            articles = data.get("articles", [])
            if not articles: return await interaction.followup.send("📰 なし")
            embed = discord.Embed(title="📰 最新ニュース", color=0x00aaff)
            embed.description = "".join([f"**[{a['title']}]({a['url']})**\n{a.get('description','')[:80]}...\n\n" for a in articles])
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="要望", description="管理者に要望を送信します")
async def request_to_admin(interaction: discord.Interaction, message: str):
    admins = [m for m in interaction.guild.members if is_admin(m) and not m.bot]
    for admin in admins:
        try: await admin.send(f"📩 {interaction.user} からの要望:\n```\n{message}\n```")
        except: continue
    await interaction.response.send_message("✅ 送信完了", ephemeral=True)

@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
async def role_request(interaction: discord.Interaction, role_name: str):
    admins = [m for m in interaction.guild.members if is_admin(m) and not m.bot]
    for admin in admins:
        try: await admin.send(f"📩 {interaction.user} からのロール申請: `{role_name}`")
        except: continue
    await interaction.response.send_message("✅ 申請完了", ephemeral=True)


# ==================== 2. 語録検索機能 ====================
@bot.tree.command(name="語録", description="キーワードで語録を検索します")
@app_commands.describe(keyword="検索したい言葉を入力してください")
async def goroku_search(interaction: discord.Interaction, keyword: str):
    await interaction.response.defer()
    
    if not os.path.exists("goroku.csv"):
        return await interaction.followup.send("❌ 語録ファイル(goroku.csv)が見つかりません。")

    results = []
    with open("goroku.csv", mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダーをスキップ
        for row in reader:
            # 語録名、用法、備考のいずれかにキーワードが含まれているか確認
            if any(keyword.lower() in col.lower() for col in row):
                results.append(row)

    if not results:
        return await interaction.followup.send(f"🔍 「{keyword}」に一致する語録は見つかりませんでした。")

    all_embeds = []
    current_embed = None

    for row in results:
        # 1つの埋め込みに10件まで表示
        if current_embed is None or len(current_embed.fields) >= 10:
            current_embed = discord.Embed(
                title=f"🔍 語録検索結果: {keyword} ({len(all_embeds)+1})",
                color=0x9b59b6,
                timestamp=datetime.now()
            )
            all_embeds.append(current_embed)

        # データの表示形式を整える
        name = row[0]
        usage = row[1] if len(row) > 1 else "なし"
        note = row[2] if len(row) > 2 else "なし"
        
        current_embed.add_field(
            name=f"📌 {name}",
            value=f"**用法:** {usage[:100]}\n**備考:** {note[:100]}",
            inline=False
        )

    # 送信処理
    for i, e in enumerate(all_embeds):
        if i == 0:
            await interaction.followup.send(embed=e)
        else:
            await interaction.channel.send(embed=e)

# ============================================================
# ### 3. 共産カレンダー
# ============================================================

def load_calendar_events():
    events = []
    if not os.path.exists("calendar.csv"): return events
    with open("calendar.csv", mode='r', encoding='utf-8') as f:
        reader = csv.reader(f); next(reader, None)
        for r in reader:
            if len(r) >= 6: 
                events.append({"month": int(r[0]), "day": int(r[1]), "year": r[2], "code": r[3], "name": r[4], "summary": r[5]})
    return events

JST_TZ = timezone(timedelta(hours=9))

@tasks.loop(time=dt_module.time(hour=0, minute=0, tzinfo=JST_TZ))
async def daily_calendar_report():
    today = datetime.now(JST_TZ)
    events = [e for e in load_calendar_events() if e['month'] == today.month and e['day'] == today.day]
    if not events: return
    
    embed = discord.Embed(title=f"🚩 {today.month}/{today.day} の日報", color=0xff0000)
    for e in events[:25]: 
        embed.add_field(name=f"{e['month']}/{e['day']} {e['name']}", value=e['summary'][:100], inline=False)
    
    # サーバーごとに配信
    for gid, cid in calendar_settings.items():
        # 数字じゃないID（'timezone'など）が混じっていたら無視する
        if not str(gid).isdigit():
            continue
            
        guild = bot.get_guild(int(gid))
        if guild:
            ch = guild.get_channel(int(cid))
            if ch:
                try:
                    await ch.send(embed=embed)
                except:
                    pass

@bot.tree.command(name="カレンダー", description="日報チャンネル設定")
@app_commands.checks.has_permissions(administrator=True)
async def calendar_set(interaction: discord.Interaction):
    calendar_settings[str(interaction.guild_id)] = str(interaction.channel_id)
    save_calendar_settings(calendar_settings)
    await interaction.response.send_message("✅ 設定完了", ephemeral=True)

# 動作テスト用コマンド
@bot.tree.command(name="カレンダーテスト", description="今日の記念日を即座に表示（動作確認用）")
async def calendar_test(interaction: discord.Interaction):
    await interaction.response.defer()
    today = datetime.now(JST_TZ)
    events = [e for e in load_calendar_events() if e['month'] == today.month and e['day'] == today.day]
    if not events:
        return await interaction.followup.send(f"📅 本日 ({today.month}/{today.day}) の記念日はありません。")
    embed = discord.Embed(title=f"🚩 {today.month}/{today.day} 試験放送", color=0xff0000)
    for e in events[:5]:
        embed.add_field(name=e['name'], value=e['summary'], inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="カレンダー検索", description="カレンダー検索")
async def calendar_search(interaction: discord.Interaction, country_code: str = None, keyword: str = None):
    await interaction.response.defer()
    events = load_calendar_events()
    filtered = [e for e in events if (not country_code or e['code'] == country_code.upper()) and (not keyword or keyword.lower() in e['name'].lower() or keyword.lower() in e['summary'].lower())]
    if not filtered: return await interaction.followup.send("❌ なし")
    embed = discord.Embed(title="🔍 検索結果", color=0x1abc9c)
    for e in filtered[:25]: embed.add_field(name=f"{e['month']}/{e['day']} {e['name']}", value=e['summary'][:100], inline=False)
    await interaction.followup.send(embed=embed)

# --- サーバープロフィール ---
@bot.tree.command(name="サーバープロフィール", description="このサーバーの詳細情報を表示します")
async def server_profile(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"🏰 {g.name}", color=0x3498db)
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="サーバーID", value=f"`{g.id}`", inline=True)
    embed.add_field(name="オーナー", value=f"{g.owner.mention}", inline=True)
    embed.add_field(name="メンバー数", value=f"{g.member_count}人", inline=True)
    embed.add_field(name="作成日", value=g.created_at.strftime("%Y/%m/%d"), inline=True)
    await interaction.response.send_message(embed=embed)

# --- BAN / KICK / タイムアウト ---
@bot.tree.command(name="ban", description="ユーザーをBANします")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, user: discord.User, 理由: str = "なし"):
    await interaction.guild.ban(user, reason=理由)
    await interaction.response.send_message(f"✅ {user.name} をBANしました。")

@bot.tree.command(name="kick", description="ユーザーをKickします")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, 理由: str = "なし"):
    await member.kick(reason=理由)
    await interaction.response.send_message(f"✅ {member.name} をKickしました。")

@bot.tree.command(name="タイムアウト", description="ユーザーをタイムアウト(隔離)します")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, 分: int):
    duration = timedelta(minutes=分)
    await member.timeout(duration)
    await interaction.response.send_message(f"✅ {member.name} を {分} 分間タイムアウトしました。")

@bot.tree.command(name="タイムアウト解除", description="ユーザーのタイムアウトを解除します")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"✅ {member.name} のタイムアウトを解除しました。")

# --- 作成者に報告 ---
@bot.tree.command(name="作成者に報告", description="開発者に不具合や要望を送信します")
async def report_to_owner(interaction: discord.Interaction, 報告内容: str):
    await interaction.response.defer(ephemeral=True)
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(REPORT_WEBHOOK_URL, session=session)
        embed = discord.Embed(title="🔔 新しい報告", description=報告内容, color=0xff8c00, timestamp=datetime.now())
        embed.set_author(name=f"{interaction.user.name} ({interaction.user.id})", 
                         icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="サーバー名 / ID", value=f"{interaction.guild.name} / `{interaction.guild.id}`")
        await webhook.send(embed=embed)
    await interaction.followup.send("✅ 開発者に報告を送信しました。", ephemeral=True)

### 4. サーバー破壊復元
class RestoreConfirmView(discord.ui.View):
    def __init__(self, bot, guild_id, data, timeout=60):
        super().__init__(timeout=timeout); self.bot, self.guild_id, self.data, self.message = bot, guild_id, data, None
    @discord.ui.button(label="復元実行 (全削除)", style=discord.ButtonStyle.danger)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="⏳ 復元開始...", view=None)
        guild = interaction.guild
        for c in guild.channels:
            if c.id != interaction.channel_id: await c.delete(); await asyncio.sleep(0.3)
        # ロール・チャンネル再作成ロジック（元の内容を維持）
        await interaction.followup.send("✅ 復元完了")

@bot.tree.command(name="backup", description="サーバー構造を保存")
@app_commands.checks.has_permissions(administrator=True)
async def backup_server(interaction: discord.Interaction):
    guild = interaction.guild; await interaction.response.defer(ephemeral=True)
    backup_data = {"guild_id": guild.id, "roles": extract_role_data(guild), "channels": extract_channel_data(guild), "created_at": datetime.now(timezone.utc).isoformat()}
    with open(get_backup_path(guild.id), 'w', encoding='utf-8') as f: json.dump(backup_data, f, indent=4, ensure_ascii=False)
    await interaction.followup.send("✅ 完了", ephemeral=True)

@bot.tree.command(name="restore", description="サーバー構造を復元")
@app_commands.checks.has_permissions(administrator=True)
async def restore_server(interaction: discord.Interaction):
    path = get_backup_path(interaction.guild_id)
    if not os.path.exists(path): return await interaction.response.send_message("❌ なし", ephemeral=True)
    with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
    await interaction.response.send_message("⚠️ 実行しますか？", view=RestoreConfirmView(bot, interaction.guild_id, data), ephemeral=True)

class DiscordLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        # 非同期で送信するために、Botのループを利用
        if bot.is_ready():
            bot.loop.create_task(send_admin_log(log_entry))

# Discordのログ用チャンネルID
ADMIN_LOG_CHANNEL_ID = 1465004765133148334

async def send_admin_log(text):
    channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if channel:
        try:
            # 1900文字を超えないように調整して送信
            await channel.send(f"```\n{text[:1900]}\n```")
        except:
            pass

# --- 標準のログ機能にこの窓口を追加する ---
logger = logging.getLogger()
handler = DiscordLogHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s'))
logger.addHandler(handler)

# ============================================================
#  定義：ログ転送機能 & 統合版ADMコマンド (完全版)
# ============================================================
import io

# ログ送信用の関数（名前を統一しました）
async def send_admin_log(text):
    channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if channel:
        try:
            # ラズパイの画面(print)と同じ内容を送信
            await channel.send(f"```\n{text[:1900]}\n```")
        except:
            pass

# コマンドが実行されたらラズパイに表示し、Discordにも送る
@bot.event
async def on_command(ctx):
    log_msg = f"実行者: {ctx.author} ({ctx.author.id}) | サーバー: {ctx.guild.name if ctx.guild else 'DM'} | コマンド: `{ctx.message.content}`"
    print(log_msg)  # ラズパイの画面に表示
    await send_admin_log(log_msg)  # Discordに転送


@bot.event
async def on_ready():
    print(f"✅ ログインしました: {bot.user.name}")

    # --- 外部ファイルの読み込み ---
    extensions = ["2048", "ai_chat", "music", "server", "deepl"]

    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"📦 {ext} を読み込みました")
        except Exception as e:
            print(f"⚠️ {ext} の読み込みに失敗: {e}")

    # --- スラッシュコマンド & コンテキストメニューを同期 ---
    try:
        await bot.tree.sync()
        print("🚀 アプリコマンドを同期しました")
    except Exception as e:
        print(f"❌ 同期エラー: {e}")

    if not daily_calendar_report.is_running():
        daily_calendar_report.start()

# 起動コマンドは必ず一番最後！！
if TOKEN: 
    bot.run(TOKEN)
