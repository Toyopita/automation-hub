import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    channel = bot.get_channel(1430450848701349908)
    if channel:
        await channel.send('Hello from Claude via Discord MCP!')
        print('Message sent successfully!')
    else:
        print('Channel not found')
    await bot.close()

bot.run(TOKEN)
