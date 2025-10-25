import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Modal, TextInput
from datetime import datetime, timedelta, timezone
from discord.ext import commands
import os
import random
import aiohttp
from dotenv import load_dotenv

# ==================== 環境変数 ====================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))  # 宣伝ログ用
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))  # タイムアウトログ用
load_dotenv()

if not TOKEN:
    raise ValueError("❌ 必須環境変数が設定されていません")
TOKEN = os.getenv("DISCORD_TOKEN")

# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理 ====================
user_messages = {}
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 1500
TIMEOUT_DURATION = 3600  # 秒

# ==================== ソ連画像 ====================
SOVIET_IMAGES = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_Library_%28cropped%29.jpg",
    # 追加
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Yuri_Andropov.jpg/120px-Yuri_Andropov.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Kosygin_1970.jpg/120px-Kosygin_1970.jpg"
]

# ==================== ユーティリティ ====================
def is_admin(user: discord.Member):
    return user.guild_permissions.administrator or user.guild_permissions.manage_roles
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

# ==================== スラッシュコマンド ====================
@bot.tree.command(name="ping", description="動作確認")
# =====================================================
# /ping
# =====================================================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
# =====================================================
# /画像
# =====================================================
@bot.tree.command(name="画像", description="ソ連の画像をランダム表示")
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
        "/ニュース - 最新ニュース取得\n"
        "/dm - 管理者専用DM送信\n"
        "/ロール付与 - 管理者: ユーザーにロール付与\n"
        "/ロール削除 - 管理者: ユーザーからロール削除\n"
        "/ロール申請 - 希望ロールを申請\n"
        "/宣伝設置 - 管理者専用: 宣伝ボタン設置\n"
        "!yaju - 任意メッセージの連投\n"
        "/2048 - start the 2048 game\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

# ==================== 最新ニュース ====================
@bot.tree.command(name="ニュース", description="最新ニュースを取得")
async def get_news(interaction: discord.Interaction):
    await interaction.response.defer()
    url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=5"
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
    except Exception as e:
        await interaction.followup.send(f"❌ エラー: {e}")

# ==================== 管理者 DM ====================
@bot.tree.command(name="dm", description="管理者: 指定ユーザーにDM送信")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
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
    try:
        await user.send(message)
        await user.send("||||"*10)
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

# ==================== 宣伝設置 ====================
@bot.tree.command(name="宣伝設置", description="管理者専用: 宣伝ボタン設置")
@app_commands.describe(channel="宣伝を設置するチャンネル")
async def setup_promo(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 権限なし", ephemeral=True)
    admin_role = discord.utils.get(guild.roles, permissions__administrator=True)
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

# ==================== メッセージ監視 ====================
@bot.event
async def on_message(message):
    if message.author.bot:
    
    admin_members = [m for m in guild.members if m.guild_permissions.administrator and not m.bot]
    if not admin_members:
        await interaction.response.send_message("❌ 管理者が見つかりません", ephemeral=True)
        return

    # 自動応答
    if "MURさん 夜中腹減んないすか？" in message.content:
        await message.channel.send(f"{message.author.mention} 腹減ったなぁ")

    if "ソ連画像" in message.content:
        url = random.choice(SOVIET_IMAGES)
        embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
        embed.set_image(url=url)
        await message.channel.send(embed=embed)

    # スパム・長文監視
    now = time.time()
    uid = message.author.id
    user_messages.setdefault(uid, [])
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    user_messages[uid].append(now)

    is_spam = len(user_messages[uid]) >= SPAM_COUNT or len(message.content) > LONG_TEXT_LIMIT

    if is_spam or any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com"]):
        if not is_admin(message.author):
            try:
                await message.delete()
                embed = discord.Embed(
                    title="🚫 クソスパマーをブロックしました。",
                    description=f"{message.author.mention} を1時間タイムアウトしました\n理由: {'長文' if len(message.content) > LONG_TEXT_LIMIT else 'スパム・不審リンク'}\n検知メッセージ: {message.content}",
                    color=0xff0000
                )
                until_time = datetime.now(timezone.utc) + timedelta(seconds=TIMEOUT_DURATION)
                await message.author.timeout(until_time, reason="スパム・不審リンク")

                # タイムアウト解除ボタン（管理者のみ）
                class UnTimeoutView(View):
                    @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.success)
                    async def untout(self, button, interaction: discord.Interaction):
                        if not is_admin(interaction.user):
                            await interaction.response.send_message("❌ 権限なし", ephemeral=True)
                            return
                        await message.author.remove_timeout()
                        await interaction.response.edit_message(content=f"{message.author.mention} のタイムアウトを解除しました", view=None)

                await message.channel.send(embed=embed, view=UnTimeoutView())

                # ログ
                if NUKE_LOG_CHANNEL_ID:
                    log_ch = bot.get_channel(NUKE_LOG_CHANNEL_ID)
                    if log_ch:
                        await log_ch.send(f"{message.author} をタイムアウト: {message.content}")

            except Exception as e:
                print(f"[ERROR] ブロック失敗: {e}")

    await bot.process_commands(message)

# ==================== 起動 ====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} — READY")

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
# !yaju コマンド
# =====================================================
@bot.command()
async def yaju(ctx, *, message: str = "||||||||||||||||||||||||||||||||||||||||||||||||||||||||"):
    for _ in range(5):
        await ctx.send(message)


# ==================== 2048ゲーム Cog ====================
class Game2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    # ここに先ほどの2048クラスのコードを丸ごと統合
    # new_board, move_left, move_right, move_up, move_down, is_game_over, render_board など


    # 🎮 盤面生成
    def new_board(self):
        board = [[0]*4 for _ in range(4)]
        self.add_tile(board)
        self.add_tile(board)
        return board

    # ➕ 新しいタイルを追加
    def add_tile(self, board):
        empty = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        board[r][c] = random.choice([2, 4])

    # 🔄 動作ロジック
    def compress(self, row):
        new_row = [i for i in row if i != 0]
        new_row += [0] * (4 - len(new_row))
        return new_row

    def merge(self, row):
        for i in range(3):
            if row[i] != 0 and row[i] == row[i+1]:
                row[i] *= 2
                row[i+1] = 0
        return row

    def move_left(self, board):
        new_board = []
        for row in board:
            row = self.compress(row)
            row = self.merge(row)
            row = self.compress(row)
            new_board.append(row)
        return new_board

    def reverse(self, board):
        return [list(reversed(row)) for row in board]

    def transpose(self, board):
        return [list(row) for row in zip(*board)]

    def move_right(self, board):
        reversed_board = self.reverse(board)
        moved = self.move_left(reversed_board)
        return self.reverse(moved)

    def move_up(self, board):
        transposed = self.transpose(board)
        moved = self.move_left(transposed)
        return self.transpose(moved)

    def move_down(self, board):
        transposed = self.transpose(board)
        moved = self.move_right(transposed)
        return self.transpose(moved)

    # 🧠 Game Over 判定
    def is_game_over(self, board):
        for r in range(4):
            for c in range(4):
                if board[r][c] == 0:
                    return False
                if c < 3 and board[r][c] == board[r][c+1]:
                    return False
                if r < 3 and board[r][c] == board[r+1][c]:
                    return False
        return True

    # 🖼 盤面画像生成
    def render_board_image(self, board):
        tile_colors = {
            0:(204,192,179), 2:(238,228,218), 4:(237,224,200), 8:(242,177,121),
            16:(245,149,99), 32:(246,124,95), 64:(246,94,59), 128:(237,207,114),
            256:(237,204,97), 512:(237,200,80), 1024:(237,197,63), 2048:(237,194,46)
        }

        img = Image.new("RGB", (400, 400), (187,173,160))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()

        for r in range(4):
            for c in range(4):
                val = board[r][c]
                color = tile_colors.get(val, (60,58,50))
                x, y = c * 100 + 10, r * 100 + 10
                draw.rounded_rectangle([x, y, x + 80, y + 80], 8, fill=color)
                if val:
                    text = str(val)
                    w, h = draw.textsize(text, font=font)
                    draw.text((x + 40 - w/2, y + 40 - h/2), text, fill=(0,0,0), font=font)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return discord.File(buffer, filename="board.png")

    # 🔹 UI更新
    async def update_message(self, interaction, user_id):
        board = self.active_games[user_id]["board"]
        score = sum(sum(row) for row in board)
        file = self.render_board_image(board)
        embed = discord.Embed(title=f"🎮 2048", description=f"Score: **{score}**", color=0xFFD700)
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self.active_games[user_id]["view"])

    # ▶️ コマンド開始
    @app_commands.command(name="2048", description="2048ゲームを開始します")
    async def start_game(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in self.active_games:
            await interaction.response.send_message("⚠️ すでにゲーム中です！", ephemeral=True)
            return

        board = self.new_board()

        # ボタンビュー
        view = discord.ui.View(timeout=None)

        async def move_callback(inter, direction):
            if inter.user.id != user_id:
                await inter.response.send_message("❌ 他人のゲームは操作できません。", ephemeral=True)
                return

            old_board = [row[:] for row in self.active_games[user_id]["board"]]
            if direction == "up":
                new_board = self.move_up(old_board)
            elif direction == "down":
                new_board = self.move_down(old_board)
            elif direction == "left":
                new_board = self.move_left(old_board)
            elif direction == "right":
                new_board = self.move_right(old_board)
            else:
                return

            if new_board != old_board:
                self.add_tile(new_board)
            self.active_games[user_id]["board"] = new_board

            # Game Over 判定
            if self.is_game_over(new_board):
                file = self.render_board_image(new_board)
                score = sum(sum(row) for row in new_board)
                embed = discord.Embed(title="💀 Game Over!", description=f"Score: **{score}**", color=0xFF0000)
                await inter.response.edit_message(embed=embed, attachments=[file], view=None)
                del self.active_games[user_id]
                return

            await self.update_message(inter, user_id)
            await inter.response.defer()

        directions = [("⬆️", "up"), ("⬇️", "down"), ("⬅️", "left"), ("➡️", "right"), ("🛑", "stop")]
        for emoji, dir in directions:
            button = discord.ui.Button(label=emoji, style=discord.ButtonStyle.primary)
            async def callback(inter, d=dir):
                if d == "stop":
                    await inter.response.edit_message(content="🛑 ゲームを終了しました。", view=None)
                    del self.active_games[user_id]
                    return
                await move_callback(inter, d)
            button.callback = callback
            view.add_item(button)

        self.active_games[user_id] = {"board": board, "view": view}

        file = self.render_board_image(board)
        embed = discord.Embed(title="🎮 2048", description="タイルを動かして2048を目指そう！", color=0x00FFAA)
        await interaction.response.send_message(embed=embed, file=file, view=view)

# 🔹 Cog登録
async def setup(bot):
    await bot.add_cog(Game2048(bot))

bot.add_cog(Game2048(bot))

# =====================================================
# 実行
# =====================================================
bot.run(TOKEN)
