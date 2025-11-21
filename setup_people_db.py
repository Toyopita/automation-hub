#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人DBにプロパティを追加するスクリプト
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

db_id = "2b200160-1818-81f2-979a-c411d61f1af8"
risshun_db_id = "2b200160-1818-815b-9bdb-ceed5e8ddc19"

url = f"https://api.notion.com/v1/databases/{db_id}"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Relationプロパティだけを追加（Formulaは手動設定）
data = {
    "properties": {
        "節入りカレンダー": {
            "relation": {
                "database_id": risshun_db_id,
                "type": "single_property",
                "single_property": {}
            }
        }
    }
}

response = requests.patch(url, headers=headers, json=data)
if response.ok:
    print("✓ プロパティ追加成功")
    print("\n次のステップ:")
    print("1. Notionで人DBを開く: https://www.notion.so/2b200160181881f2979ac411d61f1af8")
    print("2. 以下のFormulaを手動で設定:")
    print("\n【九星用_年】")
    print('lets(birthYear, year(prop("生年月日")), birthDate, prop("生年月日"), risshunRel, prop("節入りカレンダー"), risshunDate, first(risshunRel.prop("立春")), if(empty(risshunDate), birthYear, if(birthDate < risshunDate, birthYear - 1, birthYear)))')
    print("\n【本命星番号】")
    print('lets(kyuseiYear, prop("九星用_年"), digitSum, lets(y, format(kyuseiYear), d1, toNumber(substring(y, 0, 1)), d2, toNumber(substring(y, 1, 2)), d3, toNumber(substring(y, 2, 3)), d4, toNumber(substring(y, 3, 4)), sum, d1 + d2 + d3 + d4, if(sum > 9, lets(s, format(sum), d1_2, toNumber(substring(s, 0, 1)), d2_2, toNumber(substring(s, 1, 2)), d1_2 + d2_2), sum)), raw, 11 - digitSum, if(raw > 9, raw - 9, if(raw == 0, 9, raw)))')
    print("\n【本命星】")
    print('lets(num, prop("本命星番号"), ifs(num == 1, "一白水星", num == 2, "二黒土星", num == 3, "三碧木星", num == 4, "四緑木星", num == 5, "五黄土星", num == 6, "六白金星", num == 7, "七赤金星", num == 8, "八白土星", num == 9, "九紫火星", "エラー"))')
else:
    print(f"エラー: {response.status_code}")
    print(response.text)
