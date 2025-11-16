#!/usr/bin/env python3
import os
import sys
import requests
import asyncio
import discord
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_TASK")
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"
TRADITION_CHANNEL_ID = 1438876441226903673

# コマンドライン引数から情報を取得
message_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
name = sys.argv[2] if len(sys.argv) > 2 else "妊婦の焼香禁忌"
overview = sys.argv[3] if len(sys.argv) > 3 else "妊婦は通夜や告別式の際には、参列してもいいが焼香してはいけない"
details = sys.argv[4] if len(sys.argv) > 4 else "お腹の子供に障りがあるため、妊婦は焼香を避ける"
tags_str = sys.argv[5] if len(sys.argv) > 5 else "妊婦,焼香,通夜,告別式,禁忌"
taboo = sys.argv[6] if len(sys.argv) > 6 else "妊婦が焼香すると、お腹の子供に障りがある"

tags = [tag.strip() for tag in tags_str.split(',')]

# Notion登録
properties = {
    "名称": {
        "title": [{
            "type": "text",
            "text": {"content": name}
        }]
    },
    "概要": {
        "rich_text": [{
            "type": "text",
            "text": {"content": overview}
        }]
    },
    "詳細・手順": {
        "rich_text": [{
            "type": "text",
            "text": {"content": details}
        }]
    },
    "タグ": {
        "multi_select": [{"name": tag} for tag in tags]
    },
    "禁忌詳細": {
        "rich_text": [{
            "type": "text",
            "text": {"content": taboo}
        }]
    },
    "出典": {
        "multi_select": [{"name": "口伝"}]
    }
}

payload = {
    "parent": {"database_id": TRADITION_DB_ID},
    "properties": properties
}

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

response = requests.post(
    'https://api.notion.com/v1/pages',
    headers=headers,
    json=payload
)

if response.status_code >= 400:
    print(f"❌ Notion登録失敗: {response.status_code}")
    print(response.json())
    sys.exit(1)
else:
    print(f"✅ Notion登録成功: {name}")

# Discord ✅リアクション追加
if message_id:
    async def add_reaction():
        client = discord.Client(intents=discord.Intents.default())
        
        @client.event
        async def on_ready():
            try:
                channel = await client.fetch_channel(TRADITION_CHANNEL_ID)
                message = await channel.fetch_message(message_id)
                await message.add_reaction('✅')
                print(f"✅ Discord リアクション追加完了")
            except Exception as e:
                print(f"❌ リアクション追加失敗: {e}")
            finally:
                await client.close()
        
        await client.start(DISCORD_TOKEN)
    
    asyncio.run(add_reaction())
