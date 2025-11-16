#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"

# 全てのトークンを試す
tokens = {
    "NOTION_TOKEN": os.getenv("NOTION_TOKEN"),
    "NOTION_TOKEN_TASK": os.getenv("NOTION_TOKEN_TASK"),
    "NOTION_TOKEN_ORDER": os.getenv("NOTION_TOKEN_ORDER"),
    "NOTION_TOKEN_RICE": os.getenv("NOTION_TOKEN_RICE"),
    "NOTION_TOKEN_SAKE": os.getenv("NOTION_TOKEN_SAKE"),
}

for name, token in tokens.items():
    if not token:
        print(f"{name}: トークンなし")
        continue
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28'
    }
    
    response = requests.get(
        f'https://api.notion.com/v1/databases/{TRADITION_DB_ID}',
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ {name}: アクセス成功")
    else:
        print(f"❌ {name}: {response.status_code} - {response.json().get('code', 'unknown')}")
