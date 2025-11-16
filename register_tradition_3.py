#!/usr/bin/env python3
import os
import requests
import asyncio
import discord
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"
TRADITION_CHANNEL_ID = 1438876441226903673

message_id = 1438902172527100049
name = "火葬場参列後の参拝禁忌"
overview = "火葬場まで行った場合は焼香の有無問わず丸1週間神社や自宅の神棚を参拝したり神祀りしてはいけない"
details = "火葬場に行った後、7日間は神社や神棚への参拝・神祀りを避ける"
tags = ["火葬場", "神社", "神棚", "参拝", "禁忌", "死の穢れ"]
taboo = "死の穢れに触れているため、一定期間（1週間）神聖な場所への接触を避ける"

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
else:
    print(f"✅ Notion登録成功: {name}")
    print(f"URL: {response.json()['url']}")

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
