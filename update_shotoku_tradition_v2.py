#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")
PAGE_ID = "2ac00160-1818-8106-a1c4-d0f20308103b"

properties = {
    "名称": {
        "title": [{
            "type": "text",
            "text": {"content": "聖徳太子が印刷された紙幣の扱い方"}
        }]
    },
    "概要": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "聖徳太子（神様）が印刷された紙幣を粗末に扱わない。布団の下に敷いて寝ない、足元より30cm以上上に置く"}
        }]
    },
    "詳細・手順": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "聖徳太子は神様であるから、聖徳太子が印刷された紙幣を粗末に扱ってはいけない。布団の下に敷いて寝ない事。足元より30cm以上上に置く。お金は皆んな神様であるから大事にすること"}
        }]
    },
    "タグ": {
        "multi_select": [
            {"name": "聖徳太子"},
            {"name": "紙幣"},
            {"name": "お金"},
            {"name": "神様"},
            {"name": "禁忌"},
            {"name": "粗末"}
        ]
    },
    "禁忌詳細": {
        "rich_text": [{
            "type": "text",
            "text": {"content": "神様が印刷された紙幣を布団の下に敷いて寝ない。足元より30cm以上上に置く"}
        }]
    }
}

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

response = requests.patch(
    f'https://api.notion.com/v1/pages/{PAGE_ID}',
    headers=headers,
    json={"properties": properties}
)

if response.status_code >= 400:
    print(f"❌ 更新失敗: {response.status_code}")
    print(response.json())
else:
    print(f"✅ 更新成功: 聖徳太子が印刷された紙幣の扱い方")
    print(f"URL: {response.json()['url']}")
