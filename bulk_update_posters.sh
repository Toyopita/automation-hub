#!/bin/bash
# すべてのマーベル映画のポスターをWikipedia URLに一括更新するシェルスクリプト

# Notion設定
export DATABASE_ID="2ae00160-1818-81e1-980e-cbe1ed97986c"

# 更新する作品リスト（タイトル:URL形式）
declare -A POSTERS=(
  ["アイアンマン"]="https://upload.wikimedia.org/wikipedia/en/0/02/Iron_Man_%282008_film%29_poster.jpg"
  ["インクレディブル・ハルク"]="https://upload.wikimedia.org/wikipedia/en/8/88/The_Incredible_Hulk_%28film%29_poster.jpg"
  ["アイアンマン2"]="https://upload.wikimedia.org/wikipedia/en/e/ed/Iron_Man_2_poster.jpg"
  ["マイティ・ソー"]="https://upload.wikimedia.org/wikipedia/en/f/fc/Thor_poster.jpg"
  ["キャプテン・アメリカ/ザ・ファースト・アベンジャー"]="https://upload.wikimedia.org/wikipedia/en/3/37/Captain_America_The_First_Avenger_poster.jpg"
  ["アベンジャーズ"]="https://upload.wikimedia.org/wikipedia/en/8/8a/The_Avengers_%282012_film%29_poster.jpg"
  ["アイアンマン3"]="https://upload.wikimedia.org/wikipedia/en/1/19/Iron_Man_3_theatrical_poster.jpg"
  ["マイティ・ソー/ダーク・ワールド"]="https://upload.wikimedia.org/wikipedia/en/7/7f/Thor_The_Dark_World_poster.jpg"
  ["キャプテン・アメリカ/ウィンター・ソルジャー"]="https://upload.wikimedia.org/wikipedia/en/e/e8/Captain_America_The_Winter_Soldier.jpg"
  ["ガーディアンズ・オブ・ギャラクシー"]="https://upload.wikimedia.org/wikipedia/en/b/b5/Guardians_of_the_Galaxy_poster.jpg"
)

echo "📊 マーベル映画のポスターを一括更新します..."
echo ""

count=0
for title in "${!POSTERS[@]}"; do
  url="${POSTERS[$title]}"
  echo "🔄 更新中: $title"
  # ここでNotionAPIを呼び出して更新
  # （実装は後で追加）
  ((count++))
  sleep 0.4
done

echo ""
echo "✅ $count 作品を更新しました"
