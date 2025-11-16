#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

payload = {
    "query": "菊和会",
    "page_size": 10
}

response = requests.post(
    'https://api.notion.com/v1/search',
    headers=headers,
    json=payload
)

if response.status_code == 200:
    results = response.json()['results']
    for item in results:
        if item['object'] == 'page':
            parent = item.get('parent', {})
            # データベース内のページではないものを探す
            if parent.get('type') == 'workspace':
                print(f"ページ: {item['id']}")
                if 'properties' in item and 'title' in item['properties']:
                    title = item['properties']['title']
                    if title.get('title'):
                        print(f"タイトル: {title['title'][0]['plain_text']}")
                print(f"URL: {item['url']}")
                print("---")
else:
    print(f"エラー: {response.status_code}")
    print(response.json())
