#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")
TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"

traditions = [
    {
        "name": "猫が家に迷い込んだ時の対処法",
        "overview": "猫が家に迷い込んで出て行かない時は、力づくで追い出さず、何日か飼って言葉をかける",
        "details": "神様、御先祖様の御力を載くこと。力づくで追い出すと猫の祟りを受ける。何日か飼ってやり、「出て行って下さい」と何回も言葉をかける",
        "tags": ["猫", "迷い込み", "祟り", "禁忌"],
        "taboo": "力づくで追い出すと猫の祟りを受ける"
    },
    {
        "name": "夜9時以後の禁忌",
        "overview": "夜9時以後は魔物が出歩く時間であるから外へあまり出ない、窓もあまり開けない",
        "details": "夜9時以後は魔物が出歩く時間帯。外出を控え、家の窓もあまり開けないようにする",
        "tags": ["夜", "魔物", "禁忌", "窓"],
        "taboo": "夜9時以後は魔物が出歩く時間"
    },
    {
        "name": "6月から9月の米洗い禁忌",
        "overview": "6月から9月まで夜に米を洗って寝ない。朝まで腐る。朝起きて洗うこと",
        "details": "夏場（6月〜9月）は夜に米を洗って放置すると朝まで腐ってしまう。朝起きてから洗うこと",
        "tags": ["米", "夏", "禁忌", "腐敗"],
        "taboo": "6月から9月は夜に米を洗って寝ない"
    },
    {
        "name": "パンの食べ方",
        "overview": "パンはイースト菌があるから焼いて食べる",
        "details": "パンにはイースト菌が含まれているため、焼いて食べること",
        "tags": ["パン", "イースト菌", "食べ方"],
        "taboo": ""
    },
    {
        "name": "酒を飲む前の刺身",
        "overview": "酒を飲む前に醤油を付けずに刺身を一切れ食べると胃に良い",
        "details": "酒を飲む前に醤油を付けずに刺身を一切れ食べて飲むと、胃に刺身の油が付くので胃に良い。アルコールから胃を守る",
        "tags": ["刺身", "酒", "胃", "健康"],
        "taboo": ""
    },
    {
        "name": "ウィスキーを飲む前の油物",
        "overview": "ウィスキーを飲む前にチーズ類や油物を食べると胃に良い",
        "details": "ウィスキーを飲む前にチーズ類、油物を食べて飲むとアルコールから胃を守る",
        "tags": ["ウィスキー", "チーズ", "油物", "胃", "健康"],
        "taboo": ""
    },
    {
        "name": "刺身や寿司の食べ方",
        "overview": "刺身や寿司を食べる時、ワサビを始めから平均に付けて食べないと脳充血になる",
        "details": "刺身や寿司を食べる時、ワサビを始めから平均に付けて食べないと脳充血になる",
        "tags": ["刺身", "寿司", "ワサビ", "脳充血", "禁忌"],
        "taboo": "ワサビを始めから平均に付けて食べないと脳充血になる"
    },
    {
        "name": "悩みごとの考え方",
        "overview": "悩みごとを考える時間を9から1に減らし、他のことで気をまぎらわす",
        "details": "一時間思い悩むところを50分以下にして、他の10分以上を何かで気をまぎらわすようにして自分を励ます。そうすれば少しずつ気が楽になってくる",
        "tags": ["悩み", "心得", "教え", "気晴らし"],
        "taboo": ""
    },
    {
        "name": "誠の心で祈れば願いがかなう",
        "overview": "誠の心で心念を持って神様に祈れば必ず願いがかなう",
        "details": "誠実で偽りのない心、素直で嘘のない心で神様に祈れば必ず願いがかなう",
        "tags": ["祈り", "誠", "心念", "願い", "教え"],
        "taboo": ""
    }
]

def register_tradition(tradition):
    properties = {
        "名称": {
            "title": [{
                "type": "text",
                "text": {"content": tradition["name"]}
            }]
        },
        "概要": {
            "rich_text": [{
                "type": "text",
                "text": {"content": tradition["overview"]}
            }]
        },
        "詳細・手順": {
            "rich_text": [{
                "type": "text",
                "text": {"content": tradition["details"]}
            }]
        },
        "タグ": {
            "multi_select": [{"name": tag} for tag in tradition["tags"]]
        },
        "出典": {
            "multi_select": [{"name": "茶谷"}]
        }
    }
    
    if tradition["taboo"]:
        properties["禁忌詳細"] = {
            "rich_text": [{
                "type": "text",
                "text": {"content": tradition["taboo"]}
            }]
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
        print(f"❌ 登録失敗: {tradition['name']}")
        print(response.json())
        return False
    else:
        print(f"✅ 登録成功: {tradition['name']}")
        return True

# 全て登録
success_count = 0
for tradition in traditions:
    if register_tradition(tradition):
        success_count += 1

print(f"\n合計 {success_count}/{len(traditions)} 件の伝承を登録しました")
