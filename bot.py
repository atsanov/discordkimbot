import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Modal, TextInput
from datetime import datetime, timedelta, timezone

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
SPREAD_LOG_CHANNEL_ID = int(os.getenv("SPREAD_LOG_CHANNEL_ID", 0))
SPREAD_CHANNEL_ID = int(os.getenv("SPREAD_CHANNEL_ID", 0))

if not TOKEN or not DEEPSEEK_API_KEY or not GNEWS_API_KEY:
    raise ValueError("❌ 必須環境変数が設定されていません")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
user_messages = {}
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 800  # 長文スパム閾値
TIMEOUT_DURATION = 3600  # 1時間

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg",
    # 追加画像
    "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Yuri_Andropov_1983.jpg/120px-Yuri_Andropov_1983.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Leonid_Brezhnev_1972.jpg/120px-Leonid_Brezhnev_1972.jpg"
]

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="コマンド一覧")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "/ping - 動作確認\n"
        "/画像 - ソ連画像をランダム表示\n"
        "/dm - 管理者専用DM送信\n"
        "/ロール付与 - 管理者: ユーザーにロール付与\n"
        "/ロール削除 - 管理者: ユーザーからロール削除\n"
        "/ロール申請 - 希望ロールを申請\n"
        "!yaju - 任意メッセージの連投\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ==================== 管理者 DM ====================
@bot.tree.command(name="dm", description="管理者: 指定ユーザーにDM送信")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
        return
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ {user.display_name} にDM送信完了", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {user.display_name} にDM送信できません", ephemeral=True)

# ==================== !yaju コマンド ====================
@bot.command(name="yaju")
async def yaju(ctx, user: discord.User=None, count: int=1):
    content = "|||||"*10
    try:
        if user:
            for _ in range(count):
                await user.send(content)
        else:
            for _ in range(count):
                await ctx.send(content)
    except discord.Forbidden:
        await ctx.send("❌ DM送信できません")

# ==================== ロール付与/削除 ====================
@app_commands.checks.has_permissions(manage_roles=True)
@bot.tree.command(name="ロール付与", description="管理者: ユーザーにロール付与")
@app_commands.describe(user="対象ユーザー", role="付与するロール")
async def role_add(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.add_roles(role)
        await interaction.response.send_message(f"✅ {user.display_name} に {role.name} を付与")
    except Exception as e:
        await interaction.response.send_message(f"❌ 付与失敗: {e}")

@app_commands.checks.has_permissions(manage_roles=True)
@bot.tree.command(name="ロール削除", description="管理者: ユーザーからロール削除")
@app_commands.describe(user="対象ユーザー", role="削除するロール")
async def role_remove(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.remove_roles(role)
        await interaction.response.send_message(f"✅ {user.display_name} から {role.name} を削除")
    except Exception as e:
        await interaction.response.send_message(f"❌ 削除失敗: {e}")

# ==================== ロール申請 ====================
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

    # スパム監視（短時間連投・長文）
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    long_text_spam = len(message.content) >= LONG_TEXT_LIMIT

    if len(user_messages[uid]) >= SPAM_COUNT or long_text_spam or any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com"]):
        if not is_admin(message.author):
            try:
                await message.delete()
                embed = discord.Embed(
                    title="🚫 クソスパマーをブロックしました。",
                    description=f"{message.author.mention} を1時間タイムアウトしました\n理由: スパム・不審リンク・長文\n検知メッセージ: {message.content}",
                    color=0xff0000
                )
                until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
                await message.author.timeout(until_time, reason="スパム・不審リンク・長文")

                class UnTimeoutView(View):
                    @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
                    async def untout(self, button, interaction: discord.Interaction):
                        if not is_admin(interaction.user):
                            await interaction.response.send_message("❌ 権限なし", ephemeral=True)
                            return
                        await message.author.remove_timeout()
                        await interaction.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)

                await message.channel.send(embed=embed, view=UnTimeoutView())

            except Exception as e:
                print(f"[ERROR] ブロック失敗: {e}")

    await bot.process_commands(message)

# ==================== 宣伝ボタン ====================
class SpreadModal(Modal):
    def __init__(self):
        super().__init__(title="宣伝メッセージ送信")
        self.content_input = TextInput(label="メッセージ", style=discord.TextStyle.paragraph)
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        spread_ch = bot.get_channel(SPREAD_CHANNEL_ID)
        log_ch = bot.get_channel(SPREAD_LOG_CHANNEL_ID)
        if spread_ch:
            await spread_ch.send(self.content_input.value)
        if log_ch:
            await log_ch.send(f"{interaction.user} が宣伝ボタンを使用")

class SpreadView(View):
    @discord.ui.button(label="宣伝ボタン", style=discord.ButtonStyle.primary)
    async def spread_button(self, button, interaction: discord.Interaction):
        await interaction.response.send_modal(SpreadModal())

@bot.tree.command(name="宣伝設置", description="指定チャンネルに宣伝ボタンを設置")
@app_commands.describe(channel="設置するチャンネル")
async def setup_spread(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
        return
    view = SpreadView()
    await channel.send("宣伝ボタンはこちら", view=view)
    await interaction.response.send_message(f"✅ 宣伝ボタンを {channel.mention} に設置しました", ephemeral=True)

# ==================== 起動 ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — READY")

bot.run(TOKEN)
