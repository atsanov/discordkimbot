import discord
from discord import app_commands
from discord.ext import commands
import random
import io
from PIL import Image, ImageDraw, ImageFont

class Game2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {} # ユーザーIDごとのゲーム状態

    class GameBoard:
        def __init__(self):
            self.board = [[0]*4 for _ in range(4)]
            self.score = 0
            self.spawn()
            self.spawn()

        def spawn(self):
            empty = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
            if empty:
                r, c = random.choice(empty)
                self.board[r][c] = 2 if random.random() < 0.9 else 4

        def move(self, direction):
            def merge(row):
                new_row = [i for i in row if i != 0]
                for i in range(len(new_row)-1):
                    if new_row[i] == new_row[i+1]:
                        new_row[i] *= 2
                        self.score += new_row[i]
                        new_row[i+1] = 0
                new_row = [i for i in new_row if i != 0]
                return new_row + [0] * (4 - len(new_row))

            changed = False
            temp_board = [row[:] for row in self.board]
            
            if direction in ["up", "down"]:
                for c in range(4):
                    col = [self.board[r][c] for r in range(4)]
                    if direction == "down": col.reverse()
                    new_col = merge(col)
                    if direction == "down": new_col.reverse()
                    for r in range(4): self.board[r][c] = new_col[r]
            else:
                for r in range(4):
                    row = self.board[r]
                    if direction == "right": row.reverse()
                    new_row = merge(row)
                    if direction == "right": new_row.reverse()
                    self.board[r] = new_row

            if self.board != temp_board:
                self.spawn()
                return True
            return False

    def draw_board(self, board):
        img = Image.new("RGB", (400, 400), (187, 173, 160))
        draw = ImageDraw.Draw(img)
        colors = {0:(205,193,180), 2:(238,228,218), 4:(237,224,200), 8:(242,177,121), 16:(245,149,99)} # 略
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 40)
        except:
            font = ImageFont.load_default()

        for r in range(4):
            for c in range(4):
                val = board[r][c]
                color = colors.get(val, (60, 58, 50) if val > 0 else (205, 193, 180))
                draw.rectangle([c*100+5, r*100+5, c*100+95, r*100+95], fill=color)
                if val != 0:
                    draw.text((c*100+30, r*100+30), str(val), fill=(0,0,0), font=font)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="2048.png")

    class ControlView(discord.ui.View):
        def __init__(self, cog, user_id):
            super().__init__(timeout=120)
            self.cog = cog
            self.user_id = user_id

        async def process_move(self, interaction, direction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("自分のゲームを遊んでね！", ephemeral=True)
            
            game = self.cog.games.get(self.user_id)
            if game.move(direction):
                file = self.cog.draw_board(game.board)
                embed = discord.Embed(title="2048", description=f"Score: {game.score}")
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.defer() # 変化なしなら無視

        @discord.ui.button(label="↑", style=discord.ButtonStyle.primary, row=0)
        async def up(self, interaction, button): await self.process_move(interaction, "up")
        @discord.ui.button(label="←", style=discord.ButtonStyle.primary, row=1)
        async def left(self, interaction, button): await self.process_move(interaction, "left")
        @discord.ui.button(label="↓", style=discord.ButtonStyle.primary, row=1)
        async def down(self, interaction, button): await self.process_move(interaction, "down")
        @discord.ui.button(label="→", style=discord.ButtonStyle.primary, row=1)
        async def right(self, interaction, button): await self.process_move(interaction, "right")

    @app_commands.command(name="2048", description="2048ゲームを開始します")
    async def start_2048(self, interaction: discord.Interaction):
        game = self.GameBoard()
        self.games[interaction.user.id] = game
        file = self.draw_board(game.board)
        view = self.ControlView(self, interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(title="2048"), file=file, view=view)

async def setup(bot):
    await bot.add_cog(Game2048(bot))
