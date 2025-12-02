# ============================================================
#  Discord × Google Gemini 統合Bot
# (AI機能削除 / サーバーコピー機能追加 / バグ修正版)
# ============================================================

import os
import random
import time
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View
from datetime import datetime, timedelta, timezone
import aiohttp
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
from io import BytesIO
# import openai # AI機能削除
# from google import genai # AI機能削除
# from google.genai import types # AI機能削除


# ==================== 環境変数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # AI機能削除
# openai.api_key = os.getenv("OPENAI_API_KEY") # AI機能削除

if not TOKEN:
    raise ValueError("❌ 必須環境変数（DISCORD_BOT_TOKEN）が設定されていません")

# ==================== Helper Function (バグ修正) ====================
def is_admin(member: discord.Member) -> bool:
    """メンバーがサーバー内で管理者権限を持っているか確認します。"""
    if member.guild:
        return member.guild_permissions.administrator
    return False

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
TIMEOUT_DURATION = 3600  # 秒

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
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Yuri_Andropov.jpg/120px-Yuri_Andropov.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Kosygin_1970.jpg/120px-Kosygin_1970.jpg"
]

# ==================== /help (AI削除・新機能追加) ====================
@bot.tree.command(name="help", description="Botのコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Botコマンド一覧", color=0x00ff00)
    embed.add_field(name="/ping", value="Botの応答速度を確認します", inline=False)
    embed.add_field(name="/画像", value="ランダムにソ連画像を表示します", inline=False)
    embed.add_field(name="/ニュース", value="最新ニュースを取得します", inline=False)
    embed.add_field(name="/要望", value="管理者に要望を送信します", inline=False)
    embed.add_field(name="/2048", value="2048ゲームを開始します", inline=False)
    embed.add_field(name="/ロール付与", value="管理者専用: ロールを付与します", inline=False)
    embed.add_field(name="/ロール削除", value="管理者専用: ロールを削除します", inline=False)
    embed.add_field(name="/ロール申請", value="ロールを申請します", inline=False)
    embed.add_field(name="/dm", value="管理者専用: 指定ユーザーにDMを送信", inline=False)
    embed.add_field(name="/サーバーコピー", value="管理者専用: サーバーテンプレートを作成します", inline=False) # <-- 新機能
    embed.add_field(name="!yaju", value="スパムテスト用コマンド", inline=False)
    # embed.add_field(name="/画像生成", value="画像生成", inline=False) # AI機能削除
    embed.set_footer(text="※Botの全機能を一覧で確認できます")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== /画像生成コマンド (AI機能削除) ==========
# @bot.tree.command(name="画像生成", description="Geminiで画像を生成します。")
# @app_commands.describe(prompt="作りたい画像の説明を入力")
# async def 画像(interaction: discord.Interaction, prompt: str):
#     ... (AI機能のためすべて削除)


# ==================== /サーバーコピー（新機能） ====================
@bot.tree.command(name="サーバーコピー", description="現在のサーバーのテンプレートを作成し、URLを提供します (サーバー管理権限が必要)")
@app_commands.checks.has_permissions(manage_guild=True)
async def create_server_template(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です。", ephemeral=True)
        return

    # 応答に時間がかかるため、一時応答（defer）を使用
    await interaction.response.defer(ephemeral=True)

    try:
        # テンプレートの作成
        template_name = f"{guild.name}のコピー by Bot ({datetime.now().strftime('%Y-%m-%d')})"
        template_description = "Botによって自動作成されたサーバーテンプレートです。"
        
        # テンプレートを作成し、templateオブジェクトを取得
        template = await guild.create_template(name=template_name, description=template_description)

        # テンプレートURLの生成
        template_url = f"https://discord.new/{template.code}"
        
        embed = discord.Embed(
            title="✅ サーバーテンプレートが作成されました",
            description=f"このURLを使用して、現在のサーバーと同じ設定（チャンネル、ロール等）の新しいサーバーを作成できます。\n\n**テンプレート名:** `{template_name}`",
            color=0x3498db
        )
        embed.add_field(name="🔗 招待URL", value=f"[ここをクリックして新しいサーバーを作成]({template_url})", inline=False)
        embed.set_footer(text="このURLは管理者のみに表示されています。共有にはご注意ください。")

        # follow_upを使用して結果を送信 (ephemeral=Trueで自分にのみ表示)
        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send("❌ Botに「サーバーの管理 (manage_guild)」権限がないため、テンプレートを作成できません。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ テンプレート作成中にエラーが発生しました: {e}", ephemeral=True)


# ==================== /ロール付与 ====================
@bot.tree.command(name="ロール付与", description="管理者専用: ユーザーにロールを付与します")
@app_commands.checks.has_permissions(administrator=True)
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ {member.mention} に {role.name} を付与しました。", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Botのロールより上位のロールを付与できません。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ エラー: {e}", ephemeral=True)


# ==================== /ロール削除 ====================
@bot.tree.command(name="ロール削除", description="管理者専用: ユーザーからロールを削除します")
@app_commands.checks.has_permissions(administrator=True)
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ {member.mention} から {role.name} を削除しました。", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Botのロールより上位のロールを削除できません。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ エラー: {e}", ephemeral=True)

# ==================== /ロール申請 ====================
@bot.tree.command(name="ロール申請", description="希望するロールを申請します")
async def role_request(interaction: discord.Interaction, role_name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内で使用してください", ephemeral=True)
        return

    admin_members = [m for m in guild.members if is_admin(m) and not m.bot]
    sent_count = 0
    
    if not admin_members:
        await interaction.response.send_message("❌ 申請を送信できる管理者が見つかりません。", ephemeral=True)
        return

    for admin in admin_members:
        try:
            await admin.send(f"📩 **{interaction.user}** (ID: `{interaction.user.id}`) がサーバー **{guild.name}** でロールを申請しました:\n`{role_name}`")
            sent_count += 1
        except discord.Forbidden:
            # ユーザーがDMを閉鎖している場合など
            continue
    
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に申請を送信しました。", ephemeral=True)

# ==================== /dm 復活 ====================
@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    # is_admin (バグ修正) を使用
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ 管理者権限が必要です", ephemeral=True)
        return

    try:
        await user.send(f"📩 サーバー **{interaction.guild.name}** の管理者 {interaction.user} からのメッセージ:\n```\n{message}\n```")
        await interaction.response.send_message(f"✅ {user.mention} にDM送信しました。", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {user.mention} にDMを送信できませんでした（DMがブロックされている可能性があります）。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 送信失敗: {e}", ephemeral=True)

# ==================== /ping ====================
@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

# ==================== /画像 ====================
@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

# ==================== /ニュース ====================
@bot.tree.command(name="ニュース", description="最新ニュースを取得します")
async def news(interaction: discord.Interaction):
    if not GNEWS_API_KEY:
        await interaction.response.send_message("❌ ニュース機能は現在設定されていません (GNEWS_API_KEYがありません)", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    url = f"https://gnews.io/api/v4/top-headlines?token={GNEWS_API_KEY}&lang=ja&max=5"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ ニュースAPIエラー: {resp.status}")
                    return
                
                data = await resp.json()
                articles = data.get("articles", [])
                
                if not articles:
                    await interaction.followup.send("📰 現在取得可能なトップニュースはありませんでした。")
                    return
                
                embed = discord.Embed(title="📰 最新トップニュース (GNews)", color=0x00aaff)
                msg_content = ""
                for a in articles:
                    title = a.get('title','タイトルなし')
                    article_url = a.get('url','')
                    msg_content += f"**[{title}]({article_url})**\n{a.get('description','概要なし')}\n\n"
                
                embed.description = msg_content
                await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ ニュース取得中にエラーが発生しました: {e}")


# ==================== /要望 ====================
@bot.tree.command(name="要望", description="管理者に要望を送信します")
@app_commands.describe(message="送信したい要望内容")
async def request_to_admin(interaction: discord.Interaction, message: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です", ephemeral=True)
        return
    
    admin_members = [m for m in guild.members if is_admin(m) and not m.bot]
    sent_count = 0
    
    if not admin_members:
        await interaction.response.send_message("❌ 要望を送信できる管理者が見つかりません。", ephemeral=True)
        return

    for admin in admin_members:
        try:
            await admin.send(f"📩 **{interaction.user}** (ID: `{interaction.user.id}`) がサーバー **{guild.name}** で要望を送信しました:\n```\n{message}\n```")
            sent_count += 1
        except discord.Forbidden:
            continue
    
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に要望を送信しました。", ephemeral=True)

# ==================== !yaju ====================
bot.remove_command("yaju")
@bot.command()
async def yaju(ctx, *, message: str = "|||||||||||||||||||||||||||||||||||||"*10):
    # スパム対策をバイパスしないよう、管理者のみ実行可能にする
    if not is_admin(ctx.author):
        await ctx.send("❌ このコマンドは管理者のみ実行可能です。")
        return
    
    for _ in range(5):
        await ctx.send(message)



# ==================== 2048ゲーム Cog ====================
class Game2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {} # {user_id: board}

    def new_board(self):
        board = [[0]*4 for _ in range(4)]
        self.add_tile(board)
        self.add_tile(board)
        return board

    def add_tile(self, board):
        empty = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        board[r][c] = random.choice([2, 2, 2, 4]) # 2が出やすいように調整

    def compress(self, row):
        new_row = [i for i in row if i != 0]
        new_row += [0]*(4-len(new_row))
        return new_row

    def merge(self, row):
        for i in range(3):
            if row[i] != 0 and row[i] == row[i+1]:
                row[i] *= 2
                row[i+1] = 0
        return row

    def move_left(self, board):
        return [self.compress(self.merge(self.compress(row))) for row in board]

    def reverse(self, board):
        return [list(reversed(row)) for row in board]

    def transpose(self, board):
        return [list(row) for row in zip(*board)]

    def move_right(self, board):
        return self.reverse(self.move_left(self.reverse(board)))

    def move_up(self, board):
        return self.transpose(self.move_left(self.transpose(board)))

    def move_down(self, board):
        return self.transpose(self.move_right(self.transpose(board)))

    def is_game_over(self, board):
        for r in range(4):
            for c in range(4):
                if board[r][c] == 0: # 空きマスがある
                    return False
                if c < 3 and board[r][c] == board[r][c+1]: # 横にマージ可能
                    return False
                if r < 3 and board[r][c] == board[r+1][c]: # 縦にマージ可能
                    return False
        return True # どの手も打てない

    def render_board_image(self, board):
        tile_colors = {
            0: (204, 192, 179), 2: (238, 228, 218), 4: (237, 224, 200),
            8: (242, 177, 121), 16: (245, 149, 99), 32: (246, 124, 95),
            64: (246, 94, 59), 128: (237, 207, 114), 256: (237, 204, 97),
            512: (237, 200, 80), 1024: (237, 197, 63), 2048: (237, 194, 46)
        }
        img_size = 400
        padding = 8
        tile_size = (img_size - padding * 5) // 4
        
        img = Image.new("RGB", (img_size, img_size), (187, 173, 160))
        draw = ImageDraw.Draw(img)
        
        try:
            # フォントは環境に合わせてパスを調整する必要があるかもしれません
            font = ImageFont.truetype("arialbd.ttf", 32) # Boldフォントを試す
        except IOError:
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except IOError:
                font = ImageFont.load_default() # 最悪の場合デフォルト

        for r in range(4):
            for c in range(4):
                val = board[r][c]
                color = tile_colors.get(val, (60, 58, 50)) # 2048より大きい場合
                
                x0 = padding + c * (tile_size + padding)
                y0 = padding + r * (tile_size + padding)
                x1 = x0 + tile_size
                y1 = y0 + tile_size
                
                draw.rounded_rectangle([x0, y0, x1, y1], radius=5, fill=color)
                
                if val != 0:
                    text = str(val)
                    text_color = (119, 110, 101) if val in [2, 4] else (249, 246, 242)
                    
                    # textsize は Pillow 10.0.0 で削除されたため、textbbox を使用
                    try:
                        bbox = draw.textbbox((0, 0), text, font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        text_x = x0 + (tile_size - w) / 2
                        text_y = y0 + (tile_size - h) / 2 - (bbox[1]) # Y位置を微調整
                    except AttributeError: # 古いPillowの場合
                        w, h = draw.textsize(text, font=font)
                        text_x = x0 + (tile_size - w) / 2
                        text_y = y0 + (tile_size - h) / 2
                    
                    draw.text((text_x, text_y), text, fill=text_color, font=font)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    async def send_board(self, ctx_or_interaction, board, message=None):
        img_buffer = self.render_board_image(board)
        file = discord.File(fp=img_buffer, filename="2048.png")
        
        # スコア計算
        score = sum(sum(row) for row in board)
        content = f"**2048 Game**\nScore: `{score}`"

        if message: # 既存のメッセージを編集
            await message.edit(content=content, attachments=[file])
            return message
        else: # 新規メッセージを送信
            if isinstance(ctx_or_interaction, discord.Interaction):
                # スラッシュコマンドの場合 (followup)
                await ctx_or_interaction.followup.send(content=content, file=file, view=self.GameView(self))
                return await ctx_or_interaction.original_response()
            else:
                # プレフィックスコマンドの場合 (!2048)
                return await ctx_or_interaction.send(content=content, file=file, view=self.GameView(self))

    # 2048 View (リアクションの代わりにボタンを使用)
    class GameView(discord.ui.View):
        def __init__(self, cog_instance, timeout=180.0):
            super().__init__(timeout=timeout)
            self.cog = cog_instance
            self.game_owner_id = None # interaction.user.id を後で設定

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            # ゲームを開始した人だけがボタンを押せるようにする
            if interaction.user.id == self.game_owner_id:
                return True
            await interaction.response.send_message("❌ このゲームの操作は開始した人のみ可能です。", ephemeral=True)
            return False

        async def on_timeout(self):
            if self.game_owner_id in self.cog.active_games:
                del self.cog.active_games[self.game_owner_id]
            
            # タイムアウトしたらボタンを無効化
            for item in self.children:
                item.disabled = True
            # メッセージを編集してタイムアウトを通知
            try:
                await self.message.edit(content=self.message.content + "\n\n⌛ タイムアウトしました。", view=self)
            except discord.NotFound:
                pass # メッセージが削除されていた場合

        async def handle_move(self, interaction: discord.Interaction, move_function):
            user_id = interaction.user.id
            if user_id not in self.cog.active_games:
                await interaction.response.send_message("❌ アクティブなゲームがありません。", ephemeral=True)
                return

            board = self.cog.active_games[user_id]
            old_board = [row[:] for row in board]
            
            board = move_function(board)
            
            if board != old_board:
                self.cog.add_tile(board)
                self.cog.active_games[user_id] = board # ボードを更新
            
            # メッセージを編集してボードを更新
            img_buffer = self.cog.render_board_image(board)
            file = discord.File(fp=img_buffer, filename="2048.png")
            score = sum(sum(row) for row in board)
            content = f"**2048 Game**\nScore: `{score}`"
            
            await interaction.response.edit_message(content=content, attachments=[file], view=self)

            if self.cog.is_game_over(board):
                del self.cog.active_games[user_id]
                # ゲームオーバー時はボタンを無効化
                for item in self.children:
                    item.disabled = True
                await interaction.followup.send(f"💀 ゲームオーバー！ {interaction.user.mention} (Score: {score})")
                await interaction.message.edit(view=self) # ボタンを無効化したViewを適用

        @discord.ui.button(label="⬆️", style=discord.ButtonStyle.secondary, row=0)
        async def move_up_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_move(interaction, self.cog.move_up)

        @discord.ui.button(label="⬇️", style=discord.ButtonStyle.secondary, row=0)
        async def move_down_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_move(interaction, self.cog.move_down)

        @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, row=1)
        async def move_left_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_move(interaction, self.cog.move_left)

        @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, row=1)
        async def move_right_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.handle_move(interaction, self.cog.move_right)

        @discord.ui.button(label="終了", style=discord.ButtonStyle.danger, row=2)
        async def quit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = interaction.user.id
            if user_id in self.cog.active_games:
                del self.cog.active_games[user_id]
            
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(content=interaction.message.content + "\n\n👋 ゲームを終了しました。", view=self)


    @commands.hybrid_command(name="2048", description="2048ゲームを開始します")
    async def start_game(self, ctx: commands.Context):
        author_id = ctx.author.id
        if author_id in self.active_games:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("❌ 既にアクティブなゲームがあります。まずは前のゲームを終了してください。", ephemeral=True)
            else:
                await ctx.send("❌ 既にアクティブなゲームがあります。まずは前のゲームを終了してください。")
            return

        board = self.new_board()
        self.active_games[author_id] = board
        
        view = self.GameView(self)
        view.game_owner_id = author_id # ViewにオーナーIDを設定
        
        # スラッシュコマンドとプレフィックスコマンドの両方に対応
        if isinstance(ctx, discord.Interaction):
            await ctx.response.defer() # thinking...
            message = await self.send_board(ctx, board, message=None)
        else:
            message = await self.send_board(ctx, board, message=None)
        
        view.message = message # Viewにメッセージオブジェクトを保存


# ==================== メッセージ監視・AI応答 (AI削除) ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # AIメンション応答 (削除)
    # if bot.user.mention in message.content: ...
 
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
    
    # is_admin (バグ修正) を使用
    if not is_admin(message.author):
        user_messages.setdefault(uid, [])
        user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
        user_messages[uid].append(now)

        is_spam = len(user_messages[uid]) >= SPAM_COUNT
        is_long = len(message.content) > LONG_TEXT_LIMIT
        has_link = any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com", "http://", "https://"])

        # スパム判定を強化: 短時間でのリンク投稿もスパムとみなす
        if is_spam or is_long or (has_link and len(user_messages[uid]) > 2):
            try:
                await message.delete()
                
                reason = "スパム投稿" if is_spam else "長文投稿"
                if has_link and not is_spam and not is_long:
                    reason = "短時間でのリンク投稿"

                embed = discord.Embed(
                    title="🚫 スパム/違反投稿を検出",
                    description=f"{message.author.mention} を1時間タイムアウトしました\n理由: {reason}",
                    color=0xff0000
                )
                # タイムアウト処理
                await message.author.timeout(timedelta(seconds=TIMEOUT_DURATION), reason=reason)
                # チャンネルに警告を表示
                warn_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(10) # 10秒後に警告を削除
                await warn_msg.delete()

            except discord.Forbidden:
                # Botに権限がない場合（メッセージ削除・タイムアウト）
                print(f"権限エラー: {message.author} のスパム投稿を処理できませんでした。")
            except Exception as e:
                print(f"スパム処理エラー: {e}")
            
            return # スパム処理後はコマンドを実行しない

    # プレフィックスコマンド(!)の処理
    await bot.process_commands(message)

# ==================== 起動イベント ====================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"✅ 導入サーバー数: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}個のスラッシュコマンドを同期しました。")
    except Exception as e:
        print(f"❌ スラッシュコマンドの同期に失敗: {e}")
    
    # 2048ゲームCogをロード
    try:
        await bot.add_cog(Game2048(bot))
        print("✅ 2048 Game Cog をロードしました。")
    except Exception as e:
        print(f"❌ 2048 Game Cog のロードに失敗: {e}")

# ==================== メイン実行 ====================
async def main():
    async with bot:
        # on_ready でCogをロードするように変更したため、ここでは start のみ
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
