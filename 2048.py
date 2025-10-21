import discord
from discord.ext import commands
from discord import app_commands
import random
from PIL import Image, ImageDraw, ImageFont
import io

class Game2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

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
