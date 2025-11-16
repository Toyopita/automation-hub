import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot: {client.user}')
    print('全てのメッセージを監視します（5秒間）...')

@client.event
async def on_message(message):
    if message.author.bot:
        return
    print(f'\n受信: {message.content}')
    print(f'  チャンネル: {message.channel.name} (ID: {message.channel.id})')
    print(f'  サーバー: {message.guild.name}')

client.run(TOKEN)
