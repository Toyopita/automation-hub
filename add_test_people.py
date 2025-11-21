#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人DBにテストデータを追加
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

# テストデータ（前回の設計書より）
test_data = [
    ("テストA", "1980-02-03"),  # 立春前 → 三碧木星
    ("テストB", "1980-02-05"),  # 立春当日 → 二黒土星
    ("テストC", "1984-08-15"),  # → 七赤金星
    ("テストD", "1990-01-15"),  # 立春前 → 二黒土星
    ("テストE", "2000-02-04"),  # 立春当日 → 九紫火星
    ("テストF", "2000-02-03"),  # 立春前 → 一白水星
    ("テストG", "2024-02-04"),  # → 三碧木星
]

def add_person(name, birth_date):
    """人DBにエントリを追加"""
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
            "生年月日": {"date": {"start": birth_date}}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        print(f"  {name} ({birth_date}) ✓")
        return response.json()['id']
    else:
        print(f"  {name}: エラー - {response.status_code}")
        return None

if __name__ == '__main__':
    print("テストデータ追加中...")
    page_ids = []
    for name, birth_date in test_data:
        page_id = add_person(name, birth_date)
        if page_id:
            page_ids.append((name, birth_date, page_id))

    print(f"\n✓ {len(page_ids)}件追加完了")
    print("\n次のステップ:")
    print("1. Notionで人DBを開く: https://www.notion.so/2b200160181881f2979ac411d61f1af8")
    print("2. 以下のプロパティを追加（Formulaタイプ）:")
    print("   - 生まれ年（西暦）")
    print("   - 九星用_年")
    print("   - 本命星番号")
    print("   - 本命星")
    print("3. 各Formulaの式を設定")
    print("4. 各人の「節入りカレンダー」Relationを手動設定:")
    for name, birth_date, page_id in page_ids:
        year = birth_date.split('-')[0]
        print(f"   - {name} → {year}年")
