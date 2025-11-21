#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九星気学用 節入りカレンダー（立春）Notion登録スクリプト

国立天文台の暦計算に基づく立春日データを
Notionデータベースに一括登録します。
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.environ.get('NOTION_TOKEN_ORDER')

# 立春日データ（国立天文台暦計算室の情報に基づく）
# 参考: https://eco.mtk.nao.ac.jp/koyomi/
RISSHUN_DATA = {
    # 1900年代
    1900: "1900-02-04", 1901: "1901-02-04", 1902: "1902-02-05", 1903: "1903-02-05",
    1904: "1904-02-05", 1905: "1905-02-04", 1906: "1906-02-04", 1907: "1907-02-05",
    1908: "1908-02-05", 1909: "1909-02-04", 1910: "1910-02-04", 1911: "1911-02-05",
    1912: "1912-02-05", 1913: "1913-02-04", 1914: "1914-02-04", 1915: "1915-02-05",
    1916: "1916-02-05", 1917: "1917-02-04", 1918: "1918-02-04", 1919: "1919-02-05",
    1920: "1920-02-05", 1921: "1921-02-04", 1922: "1922-02-04", 1923: "1923-02-05",
    1924: "1924-02-05", 1925: "1925-02-04", 1926: "1926-02-04", 1927: "1927-02-05",
    1928: "1928-02-05", 1929: "1929-02-04", 1930: "1930-02-04", 1931: "1931-02-05",
    1932: "1932-02-05", 1933: "1933-02-04", 1934: "1934-02-04", 1935: "1935-02-05",
    1936: "1936-02-05", 1937: "1937-02-04", 1938: "1938-02-04", 1939: "1939-02-05",
    1940: "1940-02-05", 1941: "1941-02-04", 1942: "1942-02-04", 1943: "1943-02-05",
    1944: "1944-02-05", 1945: "1945-02-04", 1946: "1946-02-04", 1947: "1947-02-05",
    1948: "1948-02-05", 1949: "1949-02-04", 1950: "1950-02-04", 1951: "1951-02-05",
    1952: "1952-02-05", 1953: "1953-02-04", 1954: "1954-02-04", 1955: "1955-02-05",
    1956: "1956-02-05", 1957: "1957-02-04", 1958: "1958-02-04", 1959: "1959-02-04",
    1960: "1960-02-05", 1961: "1961-02-04", 1962: "1962-02-04", 1963: "1963-02-04",
    1964: "1964-02-05", 1965: "1965-02-04", 1966: "1966-02-04", 1967: "1967-02-04",
    1968: "1968-02-05", 1969: "1969-02-04", 1970: "1970-02-04", 1971: "1971-02-04",
    1972: "1972-02-05", 1973: "1973-02-04", 1974: "1974-02-04", 1975: "1975-02-04",
    1976: "1976-02-05", 1977: "1977-02-04", 1978: "1978-02-04", 1979: "1979-02-04",
    1980: "1980-02-05", 1981: "1981-02-04", 1982: "1982-02-04", 1983: "1983-02-04",
    1984: "1984-02-04", 1985: "1985-02-04", 1986: "1986-02-04", 1987: "1987-02-04",
    1988: "1988-02-04", 1989: "1989-02-04", 1990: "1990-02-04", 1991: "1991-02-04",
    1992: "1992-02-04", 1993: "1993-02-04", 1994: "1994-02-04", 1995: "1995-02-04",
    1996: "1996-02-04", 1997: "1997-02-04", 1998: "1998-02-04", 1999: "1999-02-04",
    # 2000年代
    2000: "2000-02-04", 2001: "2001-02-04", 2002: "2002-02-04", 2003: "2003-02-04",
    2004: "2004-02-04", 2005: "2005-02-04", 2006: "2006-02-04", 2007: "2007-02-04",
    2008: "2008-02-04", 2009: "2009-02-04", 2010: "2010-02-04", 2011: "2011-02-04",
    2012: "2012-02-04", 2013: "2013-02-04", 2014: "2014-02-04", 2015: "2015-02-04",
    2016: "2016-02-04", 2017: "2017-02-04", 2018: "2018-02-04", 2019: "2019-02-04",
    2020: "2020-02-04", 2021: "2021-02-03", 2022: "2022-02-04", 2023: "2023-02-04",
    2024: "2024-02-04", 2025: "2025-02-03", 2026: "2026-02-04", 2027: "2027-02-04",
    2028: "2028-02-04", 2029: "2029-02-03", 2030: "2030-02-04", 2031: "2031-02-04",
    2032: "2032-02-04", 2033: "2033-02-03", 2034: "2034-02-04", 2035: "2035-02-04",
    2036: "2036-02-04", 2037: "2037-02-03", 2038: "2038-02-04", 2039: "2039-02-04",
    2040: "2040-02-04", 2041: "2041-02-03", 2042: "2042-02-04", 2043: "2043-02-04",
    2044: "2044-02-04", 2045: "2045-02-03", 2046: "2046-02-04", 2047: "2047-02-04",
    2048: "2048-02-04", 2049: "2049-02-03", 2050: "2050-02-04",
    # 2050年以降（予測値）
    2051: "2051-02-04", 2052: "2052-02-04", 2053: "2053-02-03", 2054: "2054-02-04",
    2055: "2055-02-04", 2056: "2056-02-04", 2057: "2057-02-03", 2058: "2058-02-04",
    2059: "2059-02-04", 2060: "2060-02-04", 2061: "2061-02-03", 2062: "2062-02-04",
    2063: "2063-02-04", 2064: "2064-02-04", 2065: "2065-02-03", 2066: "2066-02-04",
    2067: "2067-02-04", 2068: "2068-02-04", 2069: "2069-02-03", 2070: "2070-02-04",
}


def create_database(parent_page_id: str) -> str:
    """節入りカレンダーDBを作成"""
    url = 'https://api.notion.com/v1/databases'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {
        'parent': {'type': 'page_id', 'page_id': parent_page_id},
        'title': [{'type': 'text', 'text': {'content': '節入りカレンダー'}}],
        'properties': {
            '年': {'title': {}},
            '西暦': {'number': {}},
            '立春': {'date': {}}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    db_id = response.json()['id']
    print(f"[INFO] データベース作成完了: {db_id}")
    return db_id


def add_risshun_entry(db_id: str, year: int, risshun_date: str):
    """節入りカレンダーにエントリを追加"""
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {
        'parent': {'database_id': db_id},
        'properties': {
            '年': {'title': [{'text': {'content': str(year)}}]},
            '西暦': {'number': year},
            '立春': {'date': {'start': risshun_date}}
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        print(f"  {year}年: {risshun_date} ✓")
    else:
        print(f"  {year}年: エラー - {response.status_code}")


def populate_database(db_id: str, start_year: int = 1900, end_year: int = 2070):
    """データベースに立春データを一括登録"""
    print(f"[INFO] {start_year}〜{end_year}年のデータを登録中...")

    for year in range(start_year, end_year + 1):
        if year in RISSHUN_DATA:
            add_risshun_entry(db_id, year, RISSHUN_DATA[year])
        else:
            # データがない年は2/4を仮設定
            add_risshun_entry(db_id, year, f"{year}-02-04")

    print(f"[INFO] 登録完了: {end_year - start_year + 1}件")


def verify_calculation():
    """本命星計算ロジックの検証"""
    print("\n=== 本命星計算検証 ===")

    test_cases = [
        (1980, 2, 3, "1980-02-05", "三碧木星"),  # 立春前
        (1980, 2, 5, "1980-02-05", "二黒土星"),  # 立春当日
        (1984, 8, 15, "1984-02-04", "七赤金星"),
        (1990, 1, 15, "1990-02-04", "二黒土星"),  # 立春前
        (2000, 2, 4, "2000-02-04", "九紫火星"),
        (2000, 2, 3, "2000-02-04", "一白水星"),  # 立春前
        (2024, 2, 4, "2024-02-04", "三碧木星"),
    ]

    for year, month, day, risshun, expected in test_cases:
        birth_date = datetime(year, month, day)
        risshun_date = datetime.strptime(risshun, "%Y-%m-%d")

        # 九星用_年を計算
        if birth_date < risshun_date:
            kyusei_year = year - 1
        else:
            kyusei_year = year

        # 各桁の和
        digit_sum = sum(int(d) for d in str(kyusei_year))
        while digit_sum > 9:
            digit_sum = sum(int(d) for d in str(digit_sum))

        # 本命星番号
        raw = 11 - digit_sum
        if raw > 9:
            honmyousei_num = raw - 9
        elif raw == 0:
            honmyousei_num = 9
        else:
            honmyousei_num = raw

        # 本命星名
        names = {
            1: "一白水星", 2: "二黒土星", 3: "三碧木星",
            4: "四緑木星", 5: "五黄土星", 6: "六白金星",
            7: "七赤金星", 8: "八白土星", 9: "九紫火星"
        }
        result = names[honmyousei_num]

        status = "✓" if result == expected else "✗"
        print(f"{birth_date.date()} → 九星用年:{kyusei_year} → {result} {status}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("使い方:")
        print("  python create_risshun_calendar.py verify     - 計算ロジック検証")
        print("  python create_risshun_calendar.py create <parent_page_id>  - DB作成")
        print("  python create_risshun_calendar.py populate <db_id>         - データ登録")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'verify':
        verify_calculation()
    elif command == 'create' and len(sys.argv) >= 3:
        parent_page_id = sys.argv[2]
        db_id = create_database(parent_page_id)
        print(f"作成されたDB ID: {db_id}")
    elif command == 'populate' and len(sys.argv) >= 3:
        db_id = sys.argv[2]
        populate_database(db_id)
    else:
        print("引数が不正です")
