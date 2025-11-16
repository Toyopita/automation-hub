#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_TASK")
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"

properties = {
    "名称": {
        "title": [{
            "type": "text",
            "text": {"content": "妊婦の焼香禁忌"}
        }]
    },
    "概要": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "妊婦は通夜や告別式の際には、参列してもいいが焼香してはいけない"}
        }]
    },
    "詳細・手順": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "お腹の子供に障りがあるため、妊婦は焼香を避ける"}
        }]
    },
    "タグ": {
        "multi_select": [
            {"name": "妊婦"},
            {"name": "焼香"},
            {"name": "通夜"},
            {"name": "告別式"},
            {"name": "禁忌"}
        ]
    },
    "禁忌詳細": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "妊婦が焼香すると、お腹の子供に障りがある"}
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

print(f"Status: {response.status_code}")
print(response.json())
