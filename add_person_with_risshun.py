#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人DBに人を追加（節入りカレンダーRelationを自動設定）

使い方:
  python add_person_with_risshun.py "名前" "YYYY-MM-DD"

例:
  python add_person_with_risshun.py "田中太郎" "1985-03-15"
"""
import sys
import requests
import os
from pathlib import Path
from datetime import datetime

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

    # 西暦プロパティはselectタイプなので、文字列で検索
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


def add_person(name: str, birth_date: str):
    """人DBに人を追加（節入りカレンダーRelationを自動設定）"""
    # 生年から対応する節入りカレンダーページを検索
    birth_year = int(birth_date.split('-')[0])
    risshun_page_id = find_risshun_page(birth_year)

    if not risshun_page_id:
        print(f"エラー: {birth_year}年の節入りカレンダーが見つかりません")
        return None

    # 人DBにページを作成
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "parent": {"database_id": PEOPLE_DB_ID},
        "properties": {
            "名前": {"title": [{"text": {"content": name}}]},
            "生年月日": {"date": {"start": birth_date}},
            "節入りカレンダー": {"relation": [{"id": risshun_page_id}]}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        page_id = response.json()['id']
        print(f"✓ {name} ({birth_date}) を追加しました")
        print(f"  → {birth_year}年の節入りカレンダーを自動リンク")
        print(f"  ページID: {page_id}")
        return page_id
    else:
        print(f"エラー: {response.status_code}")
        print(response.text)
        return None


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("使い方: python add_person_with_risshun.py '名前' 'YYYY-MM-DD'")
        print("例: python add_person_with_risshun.py '田中太郎' '1985-03-15'")
        sys.exit(1)

    name = sys.argv[1]
    birth_date = sys.argv[2]

    # 日付フォーマット検証
    try:
        datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        print("エラー: 日付は YYYY-MM-DD 形式で指定してください")
        sys.exit(1)

    add_person(name, birth_date)
