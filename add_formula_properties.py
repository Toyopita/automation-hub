#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人DBにFormulaプロパティを段階的に追加
"""
import requests
import os
import sys
from pathlib import Path

env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

NOTION_TOKEN = os.environ.get('NOTION_TOKEN_ORDER')
DB_ID = "2b200160-1818-81f2-979a-c411d61f1af8"

def add_formula(name, expression):
    """Formulaプロパティを追加"""
    url = f"https://api.notion.com/v1/databases/{DB_ID}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "properties": {
            name: {
                "formula": {
                    "expression": expression
                }
            }
        }
    }

    response = requests.patch(url, headers=headers, json=data)
    if response.ok:
        print(f"✓ {name} 追加成功")
        return True
    else:
        print(f"✗ {name} 追加失敗: {response.status_code}")
        print(f"  {response.json().get('message', '')}")
        return False

if __name__ == '__main__':
    # 九星用_年を追加（シンプルバージョン）
    # Relationからの参照なしで、まずは生まれ年をそのまま使う
    print("九星用_年を追加中...")

    # バージョン1: 基本的な条件式
    expression = '''if(month(prop("生年月日")) < 2, prop("生まれ年（西暦）") - 1, if(and(month(prop("生年月日")) == 2, day(prop("生年月日")) < 4), prop("生まれ年（西暦）") - 1, prop("生まれ年（西暦）")))'''

    if add_formula("九星用_年", expression):
        print("\n注意: 簡易版を使用しています（2月4日で固定）")
        print("正確な立春日を使用するには、Notionで手動で式を更新してください")

    # 本命星番号を追加
    print("\n本命星番号を追加中...")

    # 本命星番号の計算
    expression2 = '''lets(y, prop("九星用_年"), d, lets(s, format(y), d1, toNumber(substring(s, 0, 1)), d2, toNumber(substring(s, 1, 2)), d3, toNumber(substring(s, 2, 3)), d4, toNumber(substring(s, 3, 4)), d1 + d2 + d3 + d4), ds, if(d > 9, lets(s2, format(d), d1, toNumber(substring(s2, 0, 1)), d2, toNumber(substring(s2, 1, 2)), d1 + d2), d), r, 11 - ds, if(r > 9, r - 9, if(r == 0, 9, r)))'''

    add_formula("本命星番号", expression2)

    # 本命星を追加
    print("\n本命星を追加中...")

    expression3 = '''lets(n, prop("本命星番号"), ifs(n == 1, "一白水星", n == 2, "二黒土星", n == 3, "三碧木星", n == 4, "四緑木星", n == 5, "五黄土星", n == 6, "六白金星", n == 7, "七赤金星", n == 8, "八白土星", n == 9, "九紫火星", "エラー"))'''

    add_formula("本命星", expression3)

    print("\n完了！")
