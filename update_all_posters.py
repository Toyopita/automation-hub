#!/usr/bin/env python3
"""
すべてのマーベル映画のポスター画像をWikipedia URLに一括更新するスクリプト
"""
import os
import json
import time
from notion_client import Client

# Notion設定
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "2ae00160-1818-81e1-980e-cbe1ed97986c"

# Wikipedia画像URLマッピング（既に取得済みの分）
POSTER_URLS = {
    "ハワード・ザ・ダック/暗黒魔王の陰謀": "https://upload.wikimedia.org/wikipedia/en/8/8a/Howard-the-duck-poster.jpg",
    "パニッシャー": "https://upload.wikimedia.org/wikipedia/en/8/88/The_Punisher_1989_film_poster.jpg",
    "キャプテン・アメリカ": "https://upload.wikimedia.org/wikipedia/en/7/7c/Captain_America_1990_film_poster.jpg",
    "ファンタスティック・フォー": "https://upload.wikimedia.org/wikipedia/en/2/23/The_Fantastic_Four_poster.jpg",
    "ブレイド": "https://upload.wikimedia.org/wikipedia/en/1/19/Blade_movie_poster.jpg",
    "X-MEN": "https://upload.wikimedia.org/wikipedia/en/8/81/X-Men_poster.jpg",
    "ブレイド2": "https://upload.wikimedia.org/wikipedia/en/f/f3/Blade_II_poster.jpg",
    "スパイダーマン": "https://upload.wikimedia.org/wikipedia/en/f/f3/Spider-Man2002Poster.jpg",
    "デアデビル": "https://upload.wikimedia.org/wikipedia/en/8/87/Daredevil_movie_poster.jpg",
    "X-MEN2": "https://upload.wikimedia.org/wikipedia/en/3/39/X2_poster.jpg",
    "ハルク": "https://upload.wikimedia.org/wikipedia/en/a/a4/Hulk_poster.jpg",
    "ブレイド3": "https://upload.wikimedia.org/wikipedia/en/b/b2/Blade_Trinity_poster.JPG",
    "エレクトラ": "https://upload.wikimedia.org/wikipedia/en/b/b2/Elektra_%282005_film%29_poster.jpg",
    "X-MEN:ファイナル ディシジョン": "https://upload.wikimedia.org/wikipedia/en/5/55/X-Men_The_Last_Stand_theatrical_poster.jpg",
    "ゴースト・ライダー": "https://upload.wikimedia.org/wikipedia/en/3/33/Ghost_Rider_2007_film_poster.jpg",
    "スパイダーマン3": "https://upload.wikimedia.org/wikipedia/en/b/b4/Spider-Man_3_theatrical_poster.jpg",
    "ファンタスティック・フォー:銀河の危機": "https://upload.wikimedia.org/wikipedia/en/2/24/Fantastic_Four_Rise_of_the_Silver_Surfer_poster.jpg",
    "アイアンマン": "https://upload.wikimedia.org/wikipedia/en/0/02/Iron_Man_%282008_film%29_poster.jpg",
    "インクレディブル・ハルク": "https://upload.wikimedia.org/wikipedia/en/8/88/The_Incredible_Hulk_%28film%29_poster.jpg",
    "パニッシャー:ウォー・ゾーン": "https://upload.wikimedia.org/wikipedia/en/a/a2/Punisher_war_zone.jpg",
    "X-MEN ZERO": "https://upload.wikimedia.org/wikipedia/en/a/ae/X-Men_Origins_Wolverine_theatrical_poster.jpg",
    "アイアンマン2": "https://upload.wikimedia.org/wikipedia/en/e/ed/Iron_Man_2_poster.jpg",
    "マイティ・ソー": "https://upload.wikimedia.org/wikipedia/en/f/fc/Thor_poster.jpg",
    "X-MEN:ファースト・ジェネレーション": "https://upload.wikimedia.org/wikipedia/en/a/a9/X_men_first_class_poster.jpg",
    "キャプテン・アメリカ/ザ・ファースト・アベンジャー": "https://upload.wikimedia.org/wikipedia/en/3/37/Captain_America_The_First_Avenger_poster.jpg",
    "ゴースト・ライダー2": "https://upload.wikimedia.org/wikipedia/en/c/c5/Ghost_Rider_2_Poster.jpg",
    "アベンジャーズ": "https://upload.wikimedia.org/wikipedia/en/8/8a/The_Avengers_%282012_film%29_poster.jpg",
    "アメイジング・スパイダーマン": "https://upload.wikimedia.org/wikipedia/en/5/5d/The_Amazing_Spider-Man_theatrical_poster.jpeg",
    "アイアンマン3": "https://upload.wikimedia.org/wikipedia/en/1/19/Iron_Man_3_theatrical_poster.jpg",
    "ウルヴァリン:SAMURAI": "https://upload.wikimedia.org/wikipedia/en/7/74/The_Wolverine_poster.jpg",
    "マイティ・ソー/ダーク・ワールド": "https://upload.wikimedia.org/wikipedia/en/7/7f/Thor_The_Dark_World_poster.jpg",
    "キャプテン・アメリカ/ウィンター・ソルジャー": "https://upload.wikimedia.org/wikipedia/en/e/e8/Captain_America_The_Winter_Soldier.jpg",
    "アメイジング・スパイダーマン2": "https://upload.wikimedia.org/wikipedia/en/0/02/The_Amazing_Spider-Man_2_poster.jpg",
    "ガーディアンズ・オブ・ギャラクシー": "https://upload.wikimedia.org/wikipedia/en/b/b5/Guardians_of_the_Galaxy_poster.jpg",
    "X-MEN:フューチャー&パスト": "https://upload.wikimedia.org/wikipedia/en/0/0c/X-Men_Days_of_Future_Past_poster.jpg",
    "アベンジャーズ/エイジ・オブ・ウルトロン": "https://upload.wikimedia.org/wikipedia/en/f/ff/Avengers_Age_of_Ultron_poster.jpg",
    "アントマン": "https://upload.wikimedia.org/wikipedia/en/1/12/Ant-Man_%28film%29_poster.jpg",
    "デッドプール": "https://upload.wikimedia.org/wikipedia/en/2/23/Deadpool_%282016_poster%29.png",
    "シビル・ウォー/キャプテン・アメリカ": "https://upload.wikimedia.org/wikipedia/en/5/53/Captain_America_Civil_War_poster.jpg",
    "X-MEN: アポカリプス": "https://upload.wikimedia.org/wikipedia/en/0/04/X-Men_-_Apocalypse.jpg",
    "ドクター・ストレンジ": "https://upload.wikimedia.org/wikipedia/en/c/c7/Doctor_Strange_poster.jpg",
    "LOGAN/ローガン": "https://upload.wikimedia.org/wikipedia/en/3/37/Logan_2017_poster.jpg",
    "ガーディアンズ・オブ・ギャラクシー:リミックス": "https://upload.wikimedia.org/wikipedia/en/a/ab/Guardians_of_the_Galaxy_Vol_2_poster.jpg",
    "スパイダーマン:ホームカミング": "https://upload.wikimedia.org/wikipedia/en/f/f9/Spider-Man_Homecoming_poster.jpg",
    "マイティ・ソー バトルロイヤル": "https://upload.wikimedia.org/wikipedia/en/7/7d/Thor_Ragnarok_poster.jpg",
    "ブラックパンサー": "https://upload.wikimedia.org/wikipedia/en/d/d6/Black_Panther_%28film%29_poster.jpg",
    "アベンジャーズ/インフィニティ・ウォー": "https://upload.wikimedia.org/wikipedia/en/4/4d/Avengers_Infinity_War_poster.jpg",
    "デッドプール2": "https://upload.wikimedia.org/wikipedia/en/4/41/Deadpool_2_poster.jpg",
    "アントマン&ワスプ": "https://upload.wikimedia.org/wikipedia/en/2/2c/Ant-Man_and_the_Wasp_poster.jpg",
    "ヴェノム": "https://upload.wikimedia.org/wikipedia/en/2/21/Venom_%282018_film%29_poster.png",
    "キャプテン・マーベル": "https://upload.wikimedia.org/wikipedia/en/4/4e/Captain_Marvel_%28film%29_poster.jpg",
    "アベンジャーズ/エンドゲーム": "https://upload.wikimedia.org/wikipedia/en/0/0d/Avengers_Endgame_poster.jpg",
    "スパイダーマン:ファー・フロム・ホーム": "https://upload.wikimedia.org/wikipedia/en/b/bd/Spider-Man_Far_From_Home_poster.jpg",
    "X-MEN:ダーク・フェニックス": "https://upload.wikimedia.org/wikipedia/en/6/6d/X-Men_Dark_Phoenix_poster.jpg",
    "ニュー・ミュータンツ": "https://upload.wikimedia.org/wikipedia/en/c/ca/The_New_Mutants_%28film%29_poster.jpg",
    "ブラック・ウィドウ": "https://upload.wikimedia.org/wikipedia/en/e/e9/Black_Widow_%282021_film%29_poster.jpg",
    "シャン・チー/テン・リングスの伝説": "https://upload.wikimedia.org/wikipedia/en/7/74/Shang-Chi_and_the_Legend_of_the_Ten_Rings_poster.jpeg",
    "エターナルズ": "https://upload.wikimedia.org/wikipedia/en/9/9b/Eternals_poster.jpeg",
    "スパイダーマン:ノー・ウェイ・ホーム": "https://upload.wikimedia.org/wikipedia/en/0/00/Spider-Man_No_Way_Home_poster.jpg",
    "ヴェノム:レット・ゼア・ビー・カーネイジ": "https://upload.wikimedia.org/wikipedia/en/f/f7/Venom_Let_There_Be_Carnage_poster.jpg",
    "モービウス": "https://upload.wikimedia.org/wikipedia/en/1/10/Morbius_%28film%29_poster.jpg",
    "ドクター・ストレンジ/マルチバース・オブ・マッドネス": "https://upload.wikimedia.org/wikipedia/en/1/17/Doctor_Strange_in_the_Multiverse_of_Madness_poster.jpg",
    "ソー:ラブ&サンダー": "https://upload.wikimedia.org/wikipedia/en/8/89/Thor_Love_and_Thunder_poster.jpg",
    "ブラックパンサー/ワカンダ・フォーエバー": "https://upload.wikimedia.org/wikipedia/en/3/3b/Black_Panther_Wakanda_Forever_poster.jpg",
    "アントマン&ワスプ:クアントマニア": "https://upload.wikimedia.org/wikipedia/en/1/1c/Ant-Man_and_the_Wasp_Quantumania_poster.jpg",
    "ガーディアンズ・オブ・ギャラクシー:VOLUME 3": "https://upload.wikimedia.org/wikipedia/en/1/14/Guardians_of_the_Galaxy_Vol._3_poster.jpg",
    "ザ・マーベルズ": "https://upload.wikimedia.org/wikipedia/en/3/35/The_Marvels_poster.jpg",
    "マダム・ウェブ": "https://upload.wikimedia.org/wikipedia/en/0/01/Madame_Web_%28film%29_poster.jpg",
    "デッドプール&ウルヴァリン": "https://upload.wikimedia.org/wikipedia/en/4/4c/Deadpool_%26_Wolverine_poster.jpg",
    "ヴェノム:ザ・ラストダンス": "https://upload.wikimedia.org/wikipedia/en/c/cf/Venom_The_Last_Dance_poster.jpg",
    "クレイヴン・ザ・ハンター": "https://upload.wikimedia.org/wikipedia/en/d/dc/Kraven_the_Hunter_%28film%29_poster.jpg"
}

def main():
    notion = Client(auth=NOTION_TOKEN)

    print(f"📊 データベースから全作品を取得中...")

    # 全ページを取得
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        if start_cursor:
            response = notion.databases.query(
                **{"database_id": DATABASE_ID,
                "start_cursor": start_cursor,
                "page_size": 100}
            )
        else:
            response = notion.databases.query(
                **{"database_id": DATABASE_ID,
                "page_size": 100}
            )

        all_pages.extend(response["results"])
        has_more = response["has_more"]
        start_cursor = response.get("next_cursor")

    print(f"✅ {len(all_pages)}作品を取得しました")

    # 各ページを更新
    updated_count = 0
    skipped_count = 0

    for page in all_pages:
        page_id = page["id"]
        title_prop = page["properties"]["タイトル"]["title"]
        if not title_prop:
            continue

        title = title_prop[0]["plain_text"]

        # URLマッピングから検索
        url = None
        for key, value in POSTER_URLS.items():
            if key in title or title in key:
                url = value
                break

        if not url:
            print(f"⏭️  スキップ: {title} (URLマッピングなし)")
            skipped_count += 1
            continue

        # 画像URLを更新
        try:
            notion.pages.update(
                page_id=page_id,
                properties={
                    "ジャケット": {
                        "files": [{
                            "name": f"{title} ポスター",
                            "type": "external",
                            "external": {"url": url}
                        }]
                    }
                }
            )
            print(f"✅ 更新: {title}")
            updated_count += 1
            time.sleep(0.35)  # Notion APIレート制限対策
        except Exception as e:
            print(f"❌ エラー: {title} - {e}")

    print(f"\n🎉 完了!")
    print(f"   更新: {updated_count}作品")
    print(f"   スキップ: {skipped_count}作品")

if __name__ == "__main__":
    main()
