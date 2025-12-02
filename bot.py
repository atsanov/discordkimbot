# ============================================================
#  Discord Bot 最終統合版 (Raspberry Pi 3/1GB 環境向け)
#  - 破壊復元機能、語録一覧表示機能を搭載
#  - AI、2048ゲーム機能を削除
#  - バックアップファイル名を raito.json に変更
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
import asyncio
import json
import csv # 語録機能用

# ==================== 環境変数 & 定数 ====================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))
BACKUP_DIR = "server_backups" # サーバーバックアップファイルを保存するディレクトリ

if not TOKEN:
    raise ValueError("❌ 必須環境変数（DISCORD_BOT_TOKEN）が設定されていません")

# ==================== Helper Function (共通処理) ====================
def is_admin(member: discord.Member) -> bool:
    """メンバーがサーバー内で管理者権限を持っているか確認します。"""
    if member.guild:
        return member.guild_permissions.administrator
    return False

# 💡 変更箇所 1: バックアップファイル名を raito.json に変更
def get_backup_path(guild_id):
    """サーバーIDに基づいたバックアップファイルの完全パスを返します。"""
    return os.path.join(BACKUP_DIR, "raito.json")

def extract_role_data(guild):
    """サーバーからロール構造を抽出します。"""
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
    """サーバーからチャンネル構造と権限上書きを抽出します。"""
    channels_data = []
    categories = {c.id: c.name for c in guild.categories}
    
    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel) or \
           isinstance(channel, discord.VoiceChannel) or \
           isinstance(channel, discord.CategoryChannel):

            overwrites = []
            for target, overwrite in channel.overwrites.items():
                if isinstance(target, discord.Role): # ロールの上書きのみ保存
                    overwrites.append({
                        "id": target.id,
                        "type": 0, # 0=Role
                        "allow": overwrite.allow.value,
                        "deny": overwrite.deny.value
                    })
            
            data = {
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "overwrites": overwrites
            }

            if not isinstance(channel, discord.CategoryChannel):
                data["category_id"] = channel.category_id
                data["category_name"] = categories.get(channel.category_id)
                if isinstance(channel, discord.TextChannel):
                    data["topic"] = channel.topic
                elif isinstance(channel, discord.VoiceChannel):
                    data["bitrate"] = channel.bitrate
                    data["user_limit"] = channel.user_limit
            
            channels_data.append(data)
            
    return channels_data


# ==================== Bot 初期化 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==================== スパム管理定数 ====================
user_messages = {}
SPAM_THRESHOLD = 30
SPAM_COUNT = 6
LONG_TEXT_LIMIT = 1500
TIMEOUT_DURATION = 3600  # 秒

# ==================== ソ連画像リスト ====================
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

# ============================================================
## 📜 コマンド実装
# ============================================================

### 1. ユーティリティコマンド

@bot.tree.command(name="help", description="Botのコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Botコマンド一覧", color=0x00ff00)
    embed.add_field(name="/ping", value="Botの応答速度を確認します", inline=False)
    embed.add_field(name="/画像", value="ランダムにソ連画像を表示します", inline=False)
    embed.add_field(name="/ニュース", value="最新ニュースを取得します", inline=False)
    embed.add_field(name="/要望", value="管理者に要望を送信します", inline=False)
    embed.add_field(name="/語録", value="登録されている全語録を表示します", inline=False)
    embed.add_field(name="--- 管理/復旧 ---", value="サーバー管理・災害復旧コマンド", inline=False)
    embed.add_field(name="/ロール付与/削除", value="管理者専用: ロールを管理します", inline=True)
    embed.add_field(name="/dm", value="管理者専用: 指定ユーザーにDMを送信", inline=True)
    embed.add_field(name="/サーバーコピー", value="管理者専用: サーバーテンプレートを作成", inline=True)
    embed.add_field(name="/backup", value="管理者専用: サーバー構造をローカルに保存", inline=True)
    embed.add_field(name="/restore", value="管理者専用: サーバー構造を復元 (破壊的)", inline=True)
    embed.set_footer(text="※コマンドはスラッシュ（/）から入力してください")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Botの応答速度を確認します")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.tree.command(name="画像", description="ソ連画像をランダム表示")
async def soviet_image(interaction: discord.Interaction):
    url = random.choice(SOVIET_IMAGES)
    embed = discord.Embed(title="🇷🇺 ソビエト画像", color=0xff0000)
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed)

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
            continue
    
    await interaction.response.send_message(f"✅ {sent_count}人の管理者に申請を送信しました。", ephemeral=True)

bot.remove_command("yaju")
@bot.command()
async def yaju(ctx, *, message: str = "|||||||||||||||||||||||||||||||||||||"*10):
    if not is_admin(ctx.author):
        await ctx.send("❌ このコマンドは管理者のみ実行可能です。")
        return
    
    for _ in range(5):
        await ctx.send(message)

---

### 2. 語録機能 (goroku.csv)

@bot.tree.command(name="語録", description="goroku.csvから全語録を埋め込みで一覧表示します")
async def goroku_list(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    
    file_path = "goroku.csv"
    
    if not os.path.exists(file_path):
        await interaction.followup.send("❌ `goroku.csv` ファイルが見つかりません。ボットと同じディレクトリに設置してください。", ephemeral=True)
        return

    try:
        data = []
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            for row in reader:
                if len(row) >= 3:
                    data.append(row)
        
        if not data:
            await interaction.followup.send("❌ `goroku.csv` に語録データがありませんでした。", ephemeral=True)
            return

        embed = discord.Embed(
            title="📚 サーバー語録一覧",
            description=f"現在登録されている語録は **{len(data)}** 件です。",
            color=0x9b59b6
        )
        
        goroku_text = ""
        for i, row in enumerate(data):
            goroku_text += f"**{row[0]}**\n"
            goroku_text += f"　- **使用方法:** {row[1]}\n"
            goroku_text += f"　- **備考:** {row[2]}\n\n"
            
            # Discordの埋め込み制限を考慮したフィールド分割
            if len(goroku_text) > 900 or (i == len(data) - 1 and goroku_text):
                field_name = f"語録 ({len(embed.fields) + 1})"
                if len(goroku_text) > 1024:
                    goroku_text = goroku_text[:1020] + "..."
                
                embed.add_field(name=field_name, value=goroku_text, inline=False)
                goroku_text = ""
                
                if len(embed.fields) >= 25:
                    embed.set_footer(text="※フィールド数の制限により、一部の語録は表示されていません。")
                    break

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ 語録の読み込み中にエラーが発生しました: {e}", ephemeral=True)

---

### 3. 管理者向けコマンド

@bot.tree.command(name="サーバーコピー", description="現在のサーバーのテンプレートを作成し、URLを提供します (サーバー管理権限が必要)")
@app_commands.checks.has_permissions(manage_guild=True)
async def create_server_template(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ サーバー内でのみ使用可能です。", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        template_name = f"{guild.name}のコピー by Bot ({datetime.now().strftime('%Y-%m-%d')})"
        template_description = "Botによって自動作成されたサーバーテンプレートです。"
        
        template = await guild.create_template(name=template_name, description=template_description)
        template_url = f"https://discord.new/{template.code}"
        
        embed = discord.Embed(
            title="✅ サーバーテンプレートが作成されました",
            description=f"このURLを使用して、現在のサーバーと同じ設定（チャンネル、ロール等）の新しいサーバーを作成できます。",
            color=0x3498db
        )
        embed.add_field(name="🔗 招待URL", value=f"[ここをクリックして新しいサーバーを作成]({template_url})", inline=False)
        embed.set_footer(text="このURLは管理者のみに表示されています。共有にはご注意ください。")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await interaction.followup.send("❌ Botに「サーバーの管理 (manage_guild)」権限がないため、テンプレートを作成できません。", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ テンプレート作成中にエラーが発生しました: {e}", ephemeral=True)

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

@bot.tree.command(name="dm", description="管理者専用: 任意のユーザーにDMを送信します")
@app_commands.describe(user="送信先ユーザー", message="送信するメッセージ")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
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

---

### 4. サーバー破壊復元機能

class RestoreConfirmView(discord.ui.View):
    def __init__(self, bot, guild_id, data, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.data = data
        self.message = None

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(content="⚠️ 復元確認がタイムアウトしました。処理は実行されません。", view=self)

    @discord.ui.button(label="はい、復元を実行します (全チャンネル削除)", style=discord.ButtonStyle.danger)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 管理者権限が必要です。", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="⏳ 復元処理を開始します... (数分かかる場合があります)", view=self)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ サーバーが見つかりません。", ephemeral=True)
            return

        await self.execute_restore(guild, self.data, interaction.followup, interaction.message)
        
    async def execute_restore(self, guild, data, followup, original_message):
        start_time = time.time()
        
        # --- 1. 全チャンネルの削除 --- 
        await followup.send("1️⃣ 既存の全チャンネルを削除中...", ephemeral=True)
        try:
            sorted_channels = sorted(guild.channels, key=lambda c: isinstance(c, discord.CategoryChannel))
            for channel in sorted_channels:
                if channel.id != original_message.channel.id:
                    await channel.delete()
                    await asyncio.sleep(0.3)
        except discord.Forbidden:
            await followup.send("❌ チャンネル削除に必要な権限がBotにありません。", ephemeral=True)
            return

        # --- 2. ロールマップの作成と更新 ---
        await followup.send("2️⃣ ロール構造を再構築中...", ephemeral=True)
        role_map = {}
        
        for role_data in sorted(data['roles'], key=lambda x: x['position']):
            if role_data['name'] == '@everyone':
                role = guild.default_role
                await role.edit(permissions=discord.Permissions(role_data['permissions']))
            else:
                role = discord.utils.get(guild.roles, name=role_data['name'])
                if not role:
                    try:
                        role = await guild.create_role(
                            name=role_data['name'],
                            permissions=discord.Permissions(role_data['permissions']),
                            color=discord.Color(role_data['color']),
                            reason="サーバー復元によるロール再作成"
                        )
                    except discord.Forbidden:
                        await followup.send("⚠️ ロール作成に必要な権限が不足しています。ロールの復元が不完全です。", ephemeral=True)
                        break
                
            role_map[role_data['id']] = role

        # --- 3. チャンネルの再作成 ---
        await followup.send("3️⃣ チャンネルとカテゴリを再作成中...", ephemeral=True)
        category_map = {}

        def sort_key(c):
            is_category = 'category' in c['type']
            return (0 if is_category else 1, c.get('position', 9999))

        sorted_channels = sorted(data['channels'], key=sort_key)
        
        for channel_data in sorted_channels:
            
            overwrites = {}
            for ow in channel_data['overwrites']:
                target = role_map.get(ow['id']) 
                if target:
                    overwrites[target] = discord.PermissionOverwrite(
                        allow=discord.Permissions(ow['allow']),
                        deny=discord.Permissions(ow['deny'])
                    )

            parent = None
            if channel_data.get('category_id') and channel_data.get('category_name'):
                if channel_data['category_id'] not in category_map:
                    try:
                        parent = await guild.create_category(
                            channel_data['category_name'],
                            overwrites=overwrites if 'category' in channel_data['type'] else None,
                            position=channel_data['position']
                        )
                        category_map[channel_data['category_id']] = parent
                    except Exception:
                        parent = None
                else:
                    parent = category_map[channel_data['category_id']]

            try:
                if 'category' in channel_data['type']:
                    pass
                elif 'text' in channel_data['type']:
                    await guild.create_text_channel(
                        channel_data['name'],
                        topic=channel_data.get('topic'),
                        category=parent,
                        overwrites=overwrites
                    )
                elif 'voice' in channel_data['type']:
                    await guild.create_voice_channel(
                        channel_data['name'],
                        bitrate=channel_data.get('bitrate'),
                        user_limit=channel_data.get('user_limit'),
                        category=parent,
                        overwrites=overwrites
                    )
                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"チャンネル作成エラー ({channel_data['name']}): {e}")


        end_time = time.time()
        await original_message.edit(content=f"✅ サーバーの復元が完了しました！ ({end_time - start_time:.2f}秒)", view=None)


@bot.tree.command(name="backup", description="サーバーのチャンネル・ロール構造をローカルに保存します (管理者専用)")
@app_commands.checks.has_permissions(administrator=True)
async def backup_server(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        backup_data = {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "roles": extract_role_data(guild),
            "channels": extract_channel_data(guild),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # 💡 変更箇所 2: ファイル名を raito.json に変更
        file_path = get_backup_path(guild.id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=4)

        await interaction.followup.send(f"✅ サーバー構造のバックアップが完了しました！\nファイル: `{file_path}`", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ バックアップ中にエラーが発生しました: {e}", ephemeral=True)


@bot.tree.command(name="restore", description="バックアップデータからサーバーを復元します (破壊的処理/管理者専用)")
@app_commands.checks.has_permissions(administrator=True)
async def restore_server(interaction: discord.Interaction):
    guild = interaction.guild
    
    # 💡 変更箇所 3: ファイル名を raito.json に変更
    file_path = get_backup_path(guild.id)

    if not os.path.exists(file_path):
        await interaction.response.send_message("❌ バックアップファイルが見つかりません。先に `/backup` を実行してください。", ephemeral=True)
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        backup_time = datetime.fromisoformat(data['created_at']).astimezone(timezone(timedelta(hours=9))).strftime('%Y年%m月%d日 %H時%M分')

        embed = discord.Embed(
            title="⚠️ サーバー復元の最終確認 (破壊的処理)",
            description=f"バックアップデータ（{backup_time}作成）を使用してサーバー構造を復元しますか？\n\n**この操作は、現在の** **`全てのチャンネルを削除`** **し、ロール設定を上書きします。**",
            color=0xffa500
        )
        
        view = RestoreConfirmView(bot, guild.id, data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
        
    except Exception as e:
        await interaction.response.send_message(f"❌ 復元準備中にエラーが発生しました: {e}", ephemeral=True)

---

### 5. イベントリスナー

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

    # スパム・長文監視
    now = time.time()
    uid = message.author.id
    
    if not is_admin(message.author):
        user_messages.setdefault(uid, [])
        user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
        user_messages[uid].append(now)

        is_spam = len(user_messages[uid]) >= SPAM_COUNT
        is_long = len(message.content) > LONG_TEXT_LIMIT
        has_link = any(x in message.content for x in ["discord.gg", "bit.ly", "tinyurl.com", "http://", "https://"])

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
                warn_msg = await message.channel.send(embed=embed)
                await message.author.timeout(timedelta(seconds=TIMEOUT_DURATION), reason=reason)
                await asyncio.sleep(10)
                await warn_msg.delete()

            except discord.Forbidden:
                print(f"権限エラー: {message.author} のスパム投稿を処理できませんでした。")
            except Exception as e:
                print(f"スパム処理エラー: {e}")
            
            return

    await bot.process_commands(message)

@bot.event
async def on_guild_remove(guild):
    """Botがサーバーから削除されたとき、バックアップファイルを削除します。"""
    file_path = get_backup_path(guild.id)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✅ サーバー離脱に伴いバックアップファイルを削除しました: {file_path}")
        except Exception as e:
            print(f"❌ バックアップファイルの削除中にエラーが発生しました: {e}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"✅ 導入サーバー数: {len(bot.guilds)}")
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"✅ バックアップディレクトリ `{BACKUP_DIR}` を作成しました。")

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)}個のスラッシュコマンドを同期しました。")
    except Exception as e:
        print(f"❌ スラッシュコマンドの同期に失敗: {e}")

# ==================== メイン実行 ====================
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
