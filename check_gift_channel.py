import os
import sys
import discord

sys.path.insert(0, '/Users/minamitakeshi/discord-mcp-server')
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    with open('/Users/minamitakeshi/discord-mcp-server/.env') as f:
        for line in f:
            if line.startswith('DISCORD_TOKEN='):
                TOKEN = line.strip().split('=', 1)[1]

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot: {client.user}')
    for guild in client.guilds:
        print(f'\nサーバー: {guild.name}')
        for channel in guild.channels:
            if '記念品' in channel.name or '発注' in channel.name:
                print(f'  - {channel.name} (ID: {channel.id}) [タイプ: {channel.type}]')
    await client.close()

client.run(TOKEN)
