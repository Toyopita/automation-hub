#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"

name = "災難に対する感謝の気持ち"
overview = "神仏に手を合わせていても災難に出あったら、その程度の災難でまぬがれさせていただいたと感謝の気持ちをもつ"
details = "感謝の気持ちで神仏に手を合わせていれば、災難はもっと小さくなっていく"
tags = ["感謝", "災難", "神仏"]

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
    "出典": {
        "multi_select": [{"name": "神道"}]
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
