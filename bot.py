# /goroku
@bot.tree.command(name="goroku", description="淫夢語録を送信します")
@app_commands.describe(
    channel="対象チャンネル（#チャンネル形式）",
    percentage="メッセージに応じて出す割合（%）"
)
async def send_goroku(interaction: discord.Interaction, channel: discord.TextChannel, percentage: int):
    if not goroku_list:
        await interaction.response.send_message("❌ goroku.csv が読み込まれていません。", ephemeral=True)
        return

    if percentage < 1 or percentage > 100:
        await interaction.response.send_message("❌ 有効な整数（1〜100）を入力してください。", ephemeral=True)
        return

    count = 0
    async for _ in channel.history(limit=None):
        count += 1

    if str(channel.id) not in ratio_data:
        ratio_data[str(channel.id)] = 0
    ratio_data[str(channel.id)] += count

    if random.randint(1, 100) <= percentage:
        entry = random.choice(goroku_list)
        embed = discord.Embed(
            title=entry["言葉"],
            description=f"{entry['意味']}",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
    else:
        await channel.send("今回は語録を送信しませんでした。")

    with open(RATIO_JSON, "w", encoding="utf-8") as f:
        json.dump(ratio_data, f, ensure_ascii=False, indent=4)

    await interaction.response.send_message(f"✅ {channel.mention} に処理を実行しました。", ephemeral=True)


# /goroku辞典
@bot.tree.command(name="goroku辞典", description="淫夢語録の辞典を表示します")
async def goroku_dictionary(interaction: discord.Interaction):
    if not goroku_list:
        await interaction.response.send_message("❌ goroku.csv が読み込まれていません。", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    for entry in goroku_list:
        embed = discord.Embed(
            title=entry["言葉"],
            description=f"{entry['意味']}",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
