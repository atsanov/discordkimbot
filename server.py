import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import io
import json
import os

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib import font_manager

    # ── 日本語フォントを自動検出して設定（文字化け対策）──
    _JP_FONT_CANDIDATES = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "IPAGothic",
        "Hiragino Sans",          # macOS
        "Yu Gothic",              # Windows
        "MS Gothic",              # Windows fallback
    ]
    _jp_font = None
    for _name in _JP_FONT_CANDIDATES:
        if any(_name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
            _jp_font = _name
            break

    if _jp_font:
        matplotlib.rcParams["font.family"] = _jp_font
    else:
        import os
        _SEARCH_PATHS = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
        ]
        _FONT_KEYWORDS = ("noto", "ipa", "gothic", "cjk")
        for _root in _SEARCH_PATHS:
            if not os.path.isdir(_root):
                continue
            for _dirpath, _, _files in os.walk(_root):
                for _fname in _files:
                    if _fname.endswith(".ttf") and any(k in _fname.lower() for k in _FONT_KEYWORDS):
                        font_manager.fontManager.addfont(os.path.join(_dirpath, _fname))
                        matplotlib.rcParams["font.family"] = \
                            font_manager.FontProperties(fname=os.path.join(_dirpath, _fname)).get_name()
                        _jp_font = matplotlib.rcParams["font.family"]
                        break
                if _jp_font: break
            if _jp_font: break

    matplotlib.rcParams["axes.unicode_minus"] = False  
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

JST = timezone(timedelta(hours=9))
DATA_FILE = "server_stats.json"

class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self._load_data()
        self._dirty = False

        self.flush_cache.start()
        self.daily_report.start()
        self.weekly_report.start()
        self.monthly_report.start()

    def cog_unload(self):
        self._save_data()
        self.flush_cache.cancel()
        self.daily_report.cancel()
        self.weekly_report.cancel()
        self.monthly_report.cancel()

    # ─── データ管理 (JSON) ─────────────────────────────

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"guilds": {}, "settings": {}}

    def _save_data(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        self._dirty = False

    def today_str(self):
        return datetime.now(JST).strftime("%Y-%m-%d")

    def yesterday_str(self):
        return (datetime.now(JST) - timedelta(days=1)).strftime("%Y-%m-%d")

    def _get_daily_data(self, guild_id: int, date_str: str):
        gid = str(guild_id)
        if gid not in self.data["guilds"]:
            self.data["guilds"][gid] = {}
        
        if date_str not in self.data["guilds"][gid]:
            self.data["guilds"][gid][date_str] = {
                "date": date_str,
                "message_count": 0,
                "member_join": 0,
                "member_leave": 0,
                "member_count": 0,
                "reactions": {}
            }
        return self.data["guilds"][gid][date_str]

    # ─── 定期保存 ───────────────────────

    @tasks.loop(minutes=1)
    async def flush_cache(self):
        if self._dirty:
            self._save_data()

    @flush_cache.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()

    # ─── イベント ─────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        day_data = self._get_daily_data(message.guild.id, self.today_str())
        day_data["message_count"] += 1
        self._dirty = True

    @commands.Cog.listener()
    async def on_member_join(self, member):
        day_data = self._get_daily_data(member.guild.id, self.today_str())
        day_data["member_join"] += 1
        day_data["member_count"] = member.guild.member_count
        self._dirty = True

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        day_data = self._get_daily_data(member.guild.id, self.today_str())
        day_data["member_leave"] += 1
        day_data["member_count"] = member.guild.member_count
        self._dirty = True

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot or not reaction.message.guild:
            return
        day_data = self._get_daily_data(reaction.message.guild.id, self.today_str())
        emoji = str(reaction.emoji)
        day_data["reactions"][emoji] = day_data["reactions"].get(emoji, 0) + 1
        self._dirty = True

    @commands.command(name="set_report_channel")
    @commands.has_permissions(administrator=True)
    async def set_report_channel(self, ctx, channel: discord.TextChannel = None):
        """レポートを送信するチャンネルを設定します"""
        channel = channel or ctx.channel
        gid = str(ctx.guild.id)
        if gid not in self.data["settings"]:
            self.data["settings"][gid] = {}
        self.data["settings"][gid]["server_channel"] = channel.id
        self._save_data()
        await ctx.send(f"✅ レポート送信先を {channel.mention} に設定しました。")

    @commands.command(name="server")
    async def server_status(self, ctx: commands.Context):
        """今日のサーバー統計を表示する"""
        if not ctx.guild: return
        data = self._get_daily_data(ctx.guild.id, self.today_str())
        
        reactions = data.get("reactions", {})
        top_emoji = "　".join(f"{e} {c}回" for e, c in sorted(reactions.items(), key=lambda x: x[1], reverse=True)[:3]) if reactions else "なし"

        embed = discord.Embed(title="📊 本日のサーバー統計", description=f"{self.today_str()}", color=discord.Color.blurple(), timestamp=datetime.now(JST))
        embed.add_field(name="💬 メッセージ数", value=f"{data['message_count']} 件")
        embed.add_field(name="👥 メンバー数", value=f"{ctx.guild.member_count} 人")
        embed.add_field(name="📥 参加 / 📤 退出", value=f"+{data['member_join']} / -{data['member_leave']}")
        embed.add_field(name="🏅 リアクション Top3", value=top_emoji, inline=False)
        await ctx.send(embed=embed)

    # ─── 集計・グラフロジック (JSONデータ用に最適化) ──────────────────

    def fetch_daily_series(self, guild_id: int, days: int) -> dict:
        gid = str(guild_id)
        if gid not in self.data["guilds"]: return {}
        
        start_date = (datetime.now(JST) - timedelta(days=days)).strftime("%Y-%m-%d")
        return {d: v for d, v in self.data["guilds"][gid].items() if d >= start_date}

    def _make_line_chart(self, labels, msg_values, member_values, title):
        if not MATPLOTLIB_AVAILABLE: return None
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), facecolor="#2b2d31", gridspec_kw={"height_ratios": [3, 2]})
        for ax in (ax1, ax2):
            ax.set_facecolor("#2b2d31")
            ax.tick_params(colors="white", labelsize=8)
            ax.grid(axis="y", color="#3f4147", linewidth=0.5, linestyle="--")
        xs = range(len(labels))
        ax1.plot(xs, msg_values, color="#5865f2", linewidth=2, marker="o", markersize=4)
        ax1.set_title(title, color="white", fontsize=12)
        ax2.plot(xs, member_values, color="#57f287", linewidth=2, marker="o", markersize=4)
        ax2.set_xticklabels(labels, rotation=30, ha="right", color="white")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
        plt.close(fig); buf.seek(0)
        return buf

    # ─── レポート送信 ─────────────────────────────

    async def _send_report(self, report_type: str, days: int, title: str, color: discord.Color):
        for guild in self.bot.guilds:
            settings = self.data["settings"].get(str(guild.id), {})
            channel = guild.get_channel(settings.get("server_channel"))
            if not channel: continue

            daily_data = self.fetch_daily_series(guild.id, days)
            # 簡易的なラベル生成
            labels = sorted(daily_data.keys())[-7:] if days <= 7 else sorted(daily_data.keys())[::max(1, days//7)]
            msgs = [daily_data.get(d, {}).get("msg", 0) for d in labels]
            members = [daily_data.get(d, {}).get("member_count", guild.member_count) for d in labels]

            embed = discord.Embed(title=title, color=color, timestamp=datetime.now(JST))
            chart_buf = self._make_line_chart(labels, msgs, members, f"過去{days}日の推移")
            if chart_buf:
                file = discord.File(chart_buf, filename="chart.png")
                embed.set_image(url="attachment://chart.png")
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)

    @tasks.loop(time=datetime.min.time())
    async def daily_report(self):
        await self._send_report("daily", 7, "📊 デイリーレポート", discord.Color.blurple())

    @tasks.loop(time=datetime.min.time())
    async def weekly_report(self):
        if datetime.now(JST).weekday() == 6:
            await self._send_report("weekly", 28, "📅 週間レポート", discord.Color.green())

    @tasks.loop(time=datetime.min.time())
    async def monthly_report(self):
        if datetime.now(JST).day == 1:
            await self._send_report("monthly", 180, "🗓 月間レポート", discord.Color.orange())

async def setup(bot):
    await bot.add_cog(Server(bot))
