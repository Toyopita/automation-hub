#!/usr/bin/env python3
"""
全マーベル映画をNotionデータベースに一括登録するスクリプト
"""
import os
import sys
import time
import json
from notion_client import Client

# 環境変数から Notion トークンを取得
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
    return env

env = load_env()
NOTION_TOKEN = env.get('NOTION_TOKEN')
DATABASE_ID = '2ae00160-1818-81e1-980e-cbe1ed97986c'

notion = Client(auth=NOTION_TOKEN)

# 全マーベル映画リスト (1986-2024)
MOVIES = [
    {"title_ja": "ハワード・ザ・ダック/暗黒魔王の陰謀", "director": "ウィラード・ハイク", "year": 1986, "series": "Standalone"},
    {"title_ja": "パニッシャー", "director": "マーク・ゴールドブラット", "year": 1989, "series": "Punisher"},
    {"title_ja": "キャプテン・アメリカ 卍帝国の野望", "director": "アルバート・ピュン", "year": 1990, "series": "Standalone"},
    {"title_ja": "ザ・ファンタスティック・フォー", "director": "オレイ・サッソン", "year": 1994, "series": "Fantastic Four"},
    {"title_ja": "ブレイド", "director": "スティーヴン・ノリントン", "year": 1998, "series": "Blade"},
    {"title_ja": "X-メン", "director": "ブライアン・シンガー", "year": 2000, "series": "X-Men"},
    {"title_ja": "ブレイド2", "director": "ギレルモ・デル・トロ", "year": 2002, "series": "Blade"},
    {"title_ja": "スパイダーマン", "director": "サム・ライミ", "year": 2002, "series": "Spider-Man (Raimi)"},
    {"title_ja": "デアデビル", "director": "マーク・スティーヴン・ジョンソン", "year": 2003, "series": "Standalone"},
    {"title_ja": "X-MEN2", "director": "ブライアン・シンガー", "year": 2003, "series": "X-Men"},
    {"title_ja": "ハルク", "director": "アン・リー", "year": 2003, "series": "Standalone"},
    {"title_ja": "パニッシャー", "director": "ジョナサン・ヘンズリー", "year": 2004, "series": "Punisher"},
    {"title_ja": "スパイダーマン2", "director": "サム・ライミ", "year": 2004, "series": "Spider-Man (Raimi)"},
    {"title_ja": "ブレイド3", "director": "デヴィッド・S・ゴイヤー", "year": 2004, "series": "Blade"},
    {"title_ja": "エレクトラ", "director": "ロブ・ボウマン", "year": 2005, "series": "Standalone"},
    {"title_ja": "ファンタスティック・フォー ［超能力ユニット］", "director": "ティム・ストーリー", "year": 2005, "series": "Fantastic Four"},
    {"title_ja": "X-MEN: ファイナル ディシジョン", "director": "ブレット・ラトナー", "year": 2006, "series": "X-Men"},
    {"title_ja": "ゴーストライダー", "director": "マーク・スティーヴン・ジョンソン", "year": 2007, "series": "Ghost Rider"},
    {"title_ja": "スパイダーマン3", "director": "サム・ライミ", "year": 2007, "series": "Spider-Man (Raimi)"},
    {"title_ja": "ファンタスティック・フォー:銀河の危機", "director": "ティム・ストーリー", "year": 2007, "series": "Fantastic Four"},
    # {"title_ja": "アイアンマン", "director": "ジョン・ファヴロー", "year": 2008, "series": "MCU"}, # Already registered
    {"title_ja": "インクレディブル・ハルク", "director": "ルイ・レテリエ", "year": 2008, "series": "MCU"},
    {"title_ja": "パニッシャー: ウォー・ゾーン", "director": "レクシー・アレクサンダー", "year": 2008, "series": "Punisher"},
    {"title_ja": "ウルヴァリン: X-MEN ZERO", "director": "ギャヴィン・フッド", "year": 2009, "series": "X-Men"},
    {"title_ja": "アイアンマン2", "director": "ジョン・ファヴロー", "year": 2010, "series": "MCU"},
    {"title_ja": "マイティ・ソー", "director": "ケネス・ブラナー", "year": 2011, "series": "MCU"},
    {"title_ja": "X-MEN: ファースト・ジェネレーション", "director": "マシュー・ヴォーン", "year": 2011, "series": "X-Men"},
    {"title_ja": "キャプテン・アメリカ/ザ・ファースト・アベンジャー", "director": "ジョー・ジョンストン", "year": 2011, "series": "MCU"},
    {"title_ja": "ゴーストライダー2", "director": "ネヴェルダイン/テイラー", "year": 2012, "series": "Ghost Rider"},
    {"title_ja": "アベンジャーズ", "director": "ジョス・ウェドン", "year": 2012, "series": "MCU"},
    {"title_ja": "アメイジング・スパイダーマン", "director": "マーク・ウェブ", "year": 2012, "series": "Spider-Man (Webb)"},
    {"title_ja": "アイアンマン3", "director": "シェーン・ブラック", "year": 2013, "series": "MCU"},
    {"title_ja": "ウルヴァリン: SAMURAI", "director": "ジェームズ・マンゴールド", "year": 2013, "series": "X-Men"},
    {"title_ja": "マイティ・ソー/ダーク・ワールド", "director": "アラン・テイラー", "year": 2013, "series": "MCU"},
    {"title_ja": "キャプテン・アメリカ/ウィンター・ソルジャー", "director": "アンソニー・ルッソ、ジョー・ルッソ", "year": 2014, "series": "MCU"},
    {"title_ja": "アメイジング・スパイダーマン2", "director": "マーク・ウェブ", "year": 2014, "series": "Spider-Man (Webb)"},
    {"title_ja": "X-MEN: フューチャー&パスト", "director": "ブライアン・シンガー", "year": 2014, "series": "X-Men"},
    {"title_ja": "ガーディアンズ・オブ・ギャラクシー", "director": "ジェームズ・ガン", "year": 2014, "series": "MCU"},
    {"title_ja": "アベンジャーズ/エイジ・オブ・ウルトロン", "director": "ジョス・ウェドン", "year": 2015, "series": "MCU"},
    {"title_ja": "アントマン", "director": "ペイトン・リード", "year": 2015, "series": "MCU"},
    {"title_ja": "ファンタスティック・フォー", "director": "ジョシュ・トランク", "year": 2015, "series": "Fantastic Four"},
    {"title_ja": "デッドプール", "director": "ティム・ミラー", "year": 2016, "series": "Deadpool"},
    {"title_ja": "シビル・ウォー/キャプテン・アメリカ", "director": "アンソニー・ルッソ、ジョー・ルッソ", "year": 2016, "series": "MCU"},
    {"title_ja": "X-MEN: アポカリプス", "director": "ブライアン・シンガー", "year": 2016, "series": "X-Men"},
    {"title_ja": "ドクター・ストレンジ", "director": "スコット・デリクソン", "year": 2016, "series": "MCU"},
    {"title_ja": "LOGAN/ローガン", "director": "ジェームズ・マンゴールド", "year": 2017, "series": "X-Men"},
    {"title_ja": "ガーディアンズ・オブ・ギャラクシー:リミックス", "director": "ジェームズ・ガン", "year": 2017, "series": "MCU"},
    {"title_ja": "スパイダーマン:ホームカミング", "director": "ジョン・ワッツ", "year": 2017, "series": "MCU"},
    {"title_ja": "マイティ・ソー バトルロイヤル", "director": "タイカ・ワイティティ", "year": 2017, "series": "MCU"},
    # {"title_ja": "ブラックパンサー", "director": "ライアン・クーグラー", "year": 2018, "series": "MCU"}, # Already registered
    {"title_ja": "アベンジャーズ/インフィニティ・ウォー", "director": "アンソニー・ルッソ、ジョー・ルッソ", "year": 2018, "series": "MCU"},
    {"title_ja": "デッドプール2", "director": "デヴィッド・リーチ", "year": 2018, "series": "Deadpool"},
    {"title_ja": "アントマン&ワスプ", "director": "ペイトン・リード", "year": 2018, "series": "MCU"},
    {"title_ja": "ヴェノム", "director": "ルーベン・フライシャー", "year": 2018, "series": "Sony's Spider-Man Universe"},
    {"title_ja": "キャプテン・マーベル", "director": "アンナ・ボーデン、ライアン・フレック", "year": 2019, "series": "MCU"},
    {"title_ja": "アベンジャーズ/エンドゲーム", "director": "アンソニー・ルッソ、ジョー・ルッソ", "year": 2019, "series": "MCU"},
    {"title_ja": "スパイダーマン:ファー・フロム・ホーム", "director": "ジョン・ワッツ", "year": 2019, "series": "MCU"},
    {"title_ja": "X-MEN:ダーク・フェニックス", "director": "サイモン・キンバーグ", "year": 2019, "series": "X-Men"},
    {"title_ja": "ニュー・ミュータンツ", "director": "ジョシュ・ブーン", "year": 2020, "series": "X-Men"},
    {"title_ja": "ブラック・ウィドウ", "director": "ケイト・ショートランド", "year": 2021, "series": "MCU"},
    {"title_ja": "シャン・チー/テン・リングスの伝説", "director": "デスティン・ダニエル・クレットン", "year": 2021, "series": "MCU"},
    {"title_ja": "エターナルズ", "director": "クロエ・ジャオ", "year": 2021, "series": "MCU"},
    {"title_ja": "スパイダーマン:ノー・ウェイ・ホーム", "director": "ジョン・ワッツ", "year": 2021, "series": "MCU"},
    {"title_ja": "ヴェノム:レット・ゼア・ビー・カーネイジ", "director": "アンディ・サーキス", "year": 2021, "series": "Sony's Spider-Man Universe"},
    {"title_ja": "モービウス", "director": "ダニエル・エスピノーサ", "year": 2022, "series": "Sony's Spider-Man Universe"},
    {"title_ja": "ドクター・ストレンジ/マルチバース・オブ・マッドネス", "director": "サム・ライミ", "year": 2022, "series": "MCU"},
    {"title_ja": "ソー:ラブ&サンダー", "director": "タイカ・ワイティティ", "year": 2022, "series": "MCU"},
    {"title_ja": "ブラックパンサー/ワカンダ・フォーエバー", "director": "ライアン・クーグラー", "year": 2022, "series": "MCU"},
    {"title_ja": "アントマン&ワスプ:クアントマニア", "director": "ペイトン・リード", "year": 2023, "series": "MCU"},
    {"title_ja": "ガーディアンズ・オブ・ギャラクシー:VOLUME 3", "director": "ジェームズ・ガン", "year": 2023, "series": "MCU"},
    {"title_ja": "スパイダーマン:アクロス・ザ・スパイダーバース", "director": "ホアキン・ドス・サントス、ケンプ・パワーズ、ジャスティン・K・トンプソン", "year": 2023, "series": "Spider-Verse"},
    {"title_ja": "マーベルズ", "director": "ニア・ダコスタ", "year": 2023, "series": "MCU"},
    {"title_ja": "マダム・ウェブ", "director": "S・J・クラークソン", "year": 2024, "series": "Sony's Spider-Man Universe"},
    {"title_ja": "デッドプール&ウルヴァリン", "director": "ショーン・レヴィ", "year": 2024, "series": "MCU"},
    {"title_ja": "ヴェノム:ザ・ラストダンス", "director": "ケリー・マーセル", "year": 2024, "series": "Sony's Spider-Man Universe"},
    {"title_ja": "クレイヴン・ザ・ハンター", "director": "J・C・チャンダー", "year": 2024, "series": "Sony's Spider-Man Universe"}
]

# ジャンル判定
def get_genre(series):
    if series == "MCU":
        return ["アクション", "SF"]
    elif "X-Men" in series:
        return ["アクション", "SF"]
    elif "Spider-Man" in series or "Spider-Verse" in series:
        return ["アクション", "SF"]
    elif series == "Deadpool":
        return ["アクション", "コメディ"]
    elif series == "Blade":
        return ["アクション", "ホラー"]
    else:
        return ["アクション"]

# メモ作成
def create_memo(movie):
    series_name = movie["series"]
    if series_name == "MCU":
        return f"マーベル・シネマティック・ユニバース（MCU）作品。"
    elif "Spider-Man" in series_name:
        return f"{series_name}シリーズ。"
    elif series_name == "Spider-Verse":
        return "アニメーション作品。スパイダーバースシリーズ。"
    else:
        return f"{series_name}シリーズ。"

# 映画登録
def register_movie(movie):
    try:
        genres = get_genre(movie["series"])
        memo = create_memo(movie)

        properties = {
            "タイトル": {"title": [{"text": {"content": movie["title_ja"]}}]},
            "監督": {"rich_text": [{"text": {"content": movie["director"]}}]},
            "公開年": {"number": movie["year"]},
            "評価": {"select": {"name": "★★★★☆"}},  # デフォルト評価
            "ジャンル": {"multi_select": [{"name": g} for g in genres]},
            "メモ": {"rich_text": [{"text": {"content": memo}}]}
        }

        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=properties
        )

        print(f"✅ {movie['title_ja']} ({movie['year']})")
        return True

    except Exception as e:
        print(f"❌ {movie['title_ja']} ({movie['year']}): {str(e)}")
        return False

# メイン処理
def main():
    print(f"📽️  全マーベル映画をNotion DB に登録します（{len(MOVIES)}作品）\n")

    success_count = 0
    error_count = 0

    for i, movie in enumerate(MOVIES, 1):
        print(f"[{i}/{len(MOVIES)}] ", end="")

        if register_movie(movie):
            success_count += 1
        else:
            error_count += 1

        # API rate limit対策
        time.sleep(0.3)

    print(f"\n✅ 登録完了: {success_count}作品")
    print(f"❌ エラー: {error_count}作品")

if __name__ == "__main__":
    main()
