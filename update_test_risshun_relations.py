#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のテストデータに節入りカレンダーRelationを自動設定
"""
import requests
import os
from pathlib import Path

# .envファイルから環境変数を読み込む
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

NOTION_TOKEN = os.environ.get('NOTION_TOKEN_ORDER')
PEOPLE_DB_ID = "2b200160-1818-81f2-979a-c411d61f1af8"
RISSHUN_DB_ID = "2b200160-1818-815b-9bdb-ceed5e8ddc19"


def find_risshun_page(year: int) -> str:
    """節入りカレンダーDBから指定年のページIDを検索"""
    url = f"https://api.notion.com/v1/databases/{RISSHUN_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "filter": {
            "property": "西暦",
            "select": {"equals": str(year)}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        results = response.json().get('results', [])
        if results:
            return results[0]['id']
    return None


def get_all_people():
    """人DBから全ての人を取得"""
    url = f"https://api.notion.com/v1/databases/{PEOPLE_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json={})
    if response.ok:
        return response.json().get('results', [])
    return []


def update_person_relation(page_id: str, risshun_page_id: str):
    """人のページに節入りカレンダーRelationを設定"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "properties": {
            "節入りカレンダー": {"relation": [{"id": risshun_page_id}]}
        }
    }

    response = requests.patch(url, headers=headers, json=data)
    return response.ok


if __name__ == '__main__':
    print("テストデータのRelation自動設定中...")

    people = get_all_people()
    updated_count = 0

    for person in people:
        props = person['properties']
        name = props['名前']['title'][0]['text']['content'] if props['名前']['title'] else "名無し"
        birth_date = props['生年月日']['date']

        if not birth_date:
            print(f"  {name}: スキップ（生年月日なし）")
            continue

        birth_year = int(birth_date['start'].split('-')[0])

        # 既にRelationがある場合はスキップ
        existing_relation = props.get('節入りカレンダー', {}).get('relation', [])
        if existing_relation:
            print(f"  {name}: スキップ（既にRelation設定済み）")
            continue

        # 節入りカレンダーを検索
        risshun_page_id = find_risshun_page(birth_year)
        if not risshun_page_id:
            print(f"  {name}: エラー（{birth_year}年の節入りカレンダーが見つかりません）")
            continue

        # Relationを設定
        if update_person_relation(person['id'], risshun_page_id):
            print(f"  {name} ({birth_date['start']}): ✓ {birth_year}年にリンク")
            updated_count += 1
        else:
            print(f"  {name}: エラー（更新失敗）")

    print(f"\n✓ {updated_count}件のRelationを設定しました")
