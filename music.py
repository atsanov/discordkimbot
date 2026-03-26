import discord
from discord.ext import commands
import yt_dlp
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ライブ配信でも安定して取得するための設定
        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'allowed_extractors': ['youtube', 'youtube:live'], # ライブを許可
        }
        # ライブ配信中にパケットが途切れても再接続する設定
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    @commands.command(name="join")
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
        else:
            await ctx.send("先にボイスチャンネルに入っておいてね！")

    @commands.command(name="play")
    async def play(self, ctx, *, url):
        # 接続確認
        if not ctx.voice_client:
            await ctx.invoke(self.join)

        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    # ライブ配信の場合はこちらからURLを取得
                    url2 = info['url']
                    title = info.get('title', '不明なタイトル')

                # 音声ソースの作成
                source = await discord.FFmpegOpusAudio.from_probe(url2, **self.FFMPEG_OPTIONS)
                
                # 再生中の場合は一度止める
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()
                
                ctx.voice_client.play(source)
                await ctx.send(f"📻 ライブ/動画 再生開始: **{title}**")
                
            except Exception as e:
                await ctx.send(f"⚠️ エラーが発生したよ: {e}")

    @commands.command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("バイバイ！👋")
        else:
            await ctx.send("ボイスチャンネルにいないよ。")

async def setup(bot):
    await bot.add_cog(Music(bot))
