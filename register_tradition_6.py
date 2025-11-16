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

message_id = 1439108153936576613
name = "火葬後の胴骨の取り扱い禁忌"
overview = "火葬後の胴骨は穢れているので家の敷地に持ち込んではいけない"
details = "胴骨は火葬後すぐにお墓に納めるのが望ましい。すぐに納められない場合は、家には持ち帰らずお寺に預かってもらう"
tags = ["火葬", "胴骨", "遺骨", "禁忌", "穢れ", "お寺"]
taboo = "火葬後の胴骨は穢れているため、家の敷地に持ち込むことは避ける。お寺に預かってもらうのが適切"

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
        "multi_select": [{"name": "親族"}]
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
