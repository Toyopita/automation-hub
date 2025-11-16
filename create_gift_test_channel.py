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
        
        # 既存の「記念品発注テスト」チャンネルを探す
        existing_channel = None
        for channel in guild.channels:
            if channel.name == '記念品発注テスト':
                print(f'  既存チャンネル発見: {channel.name} (ID: {channel.id})')
                existing_channel = channel
                break
        
        if not existing_channel:
            # テキストチャンネルを作成
            try:
                new_channel = await guild.create_text_channel('記念品発注テスト')
                print(f'  新規チャンネル作成: {new_channel.name} (ID: {new_channel.id})')
            except Exception as e:
                print(f'  エラー: {e}')
        
    await client.close()

client.run(TOKEN)
