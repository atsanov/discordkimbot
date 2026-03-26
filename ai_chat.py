import discord
from discord.ext import commands
import re
import os
from openai import OpenAI
from collections import defaultdict
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 環境変数からAPIキーを取得。設定されていない場合は None になる
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.history = defaultdict(list)
        self.MAX_HISTORY = 10 

    @commands.Cog.listener()
    async def on_message(self, message):
        # ここにメッセージ受信時の処理が続く...
        if message.author.bot:
            return
        #

        is_mention = self.bot.user in message.mentions
        is_reply = (message.reference and message.reference.resolved and message.reference.resolved.author == self.bot.user)

        if is_mention or is_reply:
            content = re.sub(f'<@{self.bot.user.id}>', '', message.content).strip()
            if not content:
                return

            async with message.channel.typing():
                # 🔄 賢い順 & 無料枠のフォールバックリスト
                models = [
                    "qwen/qwen3-next-80b-a3b-instruct:free",
                    "google/gemma-3-27b-it:free",
                    "tngtech/deepseek-r1t2-chimera:free",
                    "tngtech/deepseek-r1t-chimera:free",
                    "google/gemma-3-12b-it:free",
                    "liquid/lfm-2.5-1.2b-thinking:free",
                    "stepfun/step-3.5-flash:free",
                    "qwen/qwen3-4b:free"
                ]

                ai_reply = None
                used_model = ""
                history_key = str(message.channel.id)

                # ループの外で履歴のベースを作成（重複防止）
                base_messages = []
                for h in self.history[history_key][-self.MAX_HISTORY:]:
                    base_messages.append(h)

                for model_name in models:
                    try:
                        # 毎回コピーを作成して指示を追加
                        messages_for_ai = base_messages.copy()
                        instruction = "【設定：日本語で短く簡潔に、しかし親しみやすく回答してください。】\n\n"
                        messages_for_ai.append({"role": "user", "content": f"{instruction}{content}"})

                        response = self.client.chat.completions.create(
                            model=model_name,
                            messages=messages_for_ai,
                            timeout=30.0
                        )
                        
                        ai_reply = response.choices[0].message.content
                        used_model = model_name
                        break # 成功したらループを抜ける

                    except Exception as e:
                        print(f"⚠️ {model_name} でエラー: {e}")
                        continue # 次のモデルを試す

                if ai_reply:
                    # 成功した時だけ履歴に保存
                    self.history[history_key].append({"role": "user", "content": content})
                    self.history[history_key].append({"role": "assistant", "content": ai_reply})
                    
                    print(f"✅ 使用モデル: {used_model}")
                    
                    # 2000文字制限対策
                    if len(ai_reply) > 2000:
                        for i in range(0, len(ai_reply), 2000):
                            await message.reply(ai_reply[i:i+2000])
                    else:
                        await message.reply(ai_reply)
                else:
                    await message.reply("😭 申し訳ありません、現在全てのAIモデルが非常に混雑しています。数分後に再度お試しください。")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
