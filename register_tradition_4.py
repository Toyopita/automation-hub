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

message_id = 1439121121508069437
name = "身内の不幸時の帰幽報告と言動の禁忌"
overview = "身内の不幸があった場合、忍び手で神棚と氏神様に帰幽報告を行い、故人の前では不要な発言を避ける"
details = """1. 忍び手で神棚に帰幽報告し、速やかに半紙を神棚の前に取り付ける
2. 親族の誰かが氏神様に帰幽報告（鳥居の外側から忍び手で拝礼）
3. 故人の前では相続の話、「すぐあとを追う」「極楽浄土へ」などの発言を避ける"""
tags = ["帰幽報告", "神棚", "氏神様", "忍び手", "不幸", "禁忌", "言動", "因縁"]
taboo = "故人の前で不要な発言（相続の話、あとを追う発言など）をすると要らぬ因縁を作り、命を落とすこともある。故人は死後もしばらく耳が聞こえているため注意が必要"

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
