import os
import discord
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot起動: {client.user}')
    for guild in client.guilds:
        print(f'\nサーバー: {guild.name}')
        for channel in guild.text_channels:
            if 'タスクメモテスト' in channel.name or 'task' in channel.name.lower():
                print(f'  - {channel.name} (ID: {channel.id})')
    await client.close()

client.run(DISCORD_TOKEN)
