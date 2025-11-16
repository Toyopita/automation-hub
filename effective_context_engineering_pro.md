---
marp: true
theme: default
paginate: true
backgroundColor: #0a0a0a
color: #ffffff
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

  section {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    font-size: 22px;
    padding: 60px 80px;
    line-height: 1.6;
    position: relative;
  }

  section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
      radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.3) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.3) 0%, transparent 50%);
    z-index: 0;
  }

  section > * {
    position: relative;
    z-index: 1;
  }

  h1 {
    font-size: 64px;
    font-weight: 900;
    margin-bottom: 40px;
    background: linear-gradient(135deg, #ffffff 0%, #e0e0ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    letter-spacing: -2px;
  }

  h2 {
    font-size: 42px;
    font-weight: 700;
    margin: 40px 0 30px 0;
    color: #ffffff;
    position: relative;
    padding-left: 30px;
    letter-spacing: -1px;
  }

  h2::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 8px;
    height: 80%;
    background: linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.3) 100%);
    border-radius: 4px;
  }

  h3 {
    font-size: 32px;
    font-weight: 600;
    margin: 30px 0 20px 0;
    color: #e0e0ff;
  }

  p, li {
    font-size: 22px;
    line-height: 1.8;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.95);
  }

  strong {
    font-weight: 700;
    color: #ffd700;
  }

  .card {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 20px;
    padding: 40px;
    margin: 30px 0;
    box-shadow:
      0 20px 60px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }

  .highlight {
    background: linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(255, 165, 0, 0.15) 100%);
    border-left: 4px solid #ffd700;
    padding: 30px;
    margin: 30px 0;
    border-radius: 12px;
    backdrop-filter: blur(10px);
  }

  .compare {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    margin: 30px 0;
  }

  .good {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.15) 100%);
    border: 2px solid rgba(16, 185, 129, 0.4);
    border-radius: 20px;
    padding: 30px;
  }

  .bad {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%);
    border: 2px solid rgba(239, 68, 68, 0.4);
    border-radius: 20px;
    padding: 30px;
  }

  pre {
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 30px;
    border-radius: 16px;
    font-size: 18px;
    overflow-x: auto;
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  }

  code {
    font-family: 'Fira Code', 'Courier New', monospace;
    background: rgba(255, 255, 255, 0.1);
    color: #ffd700;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 20px;
  }

  table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 30px 0;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    overflow: hidden;
    backdrop-filter: blur(10px);
  }

  thead {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
  }

  th {
    padding: 20px;
    font-weight: 700;
    font-size: 20px;
    text-align: left;
  }

  td {
    padding: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 20px;
  }

  ul, ol {
    padding-left: 40px;
  }

  li {
    margin: 15px 0;
    position: relative;
  }

  li::marker {
    color: #ffd700;
  }

  section.lead {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  section.lead h1 {
    font-size: 80px;
    margin-bottom: 40px;
  }

  .badge {
    display: inline-block;
    background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
    color: #000;
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 16px;
    font-weight: 700;
    margin: 0 8px;
    box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
  }

  .stat {
    text-align: center;
    padding: 30px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    margin: 20px 0;
    backdrop-filter: blur(10px);
  }

  .stat-value {
    font-size: 72px;
    font-weight: 900;
    background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    display: block;
    margin: 10px 0;
  }

  .stat-label {
    font-size: 20px;
    color: rgba(255, 255, 255, 0.8);
    font-weight: 400;
  }

  section::after {
    color: rgba(255, 255, 255, 0.5);
    font-weight: 600;
    font-size: 16px;
  }

  blockquote {
    border-left: 4px solid #ffd700;
    padding-left: 30px;
    margin: 30px 0;
    font-size: 28px;
    font-style: italic;
    color: #e0e0ff;
  }
---

<!-- _class: lead -->

# Context Engineering

**AIエージェントの性能を決める<br>トークン管理の技術**

---

## 📖 35分で学ぶこと

<div class="card">

<div class="compare">

<div>

### 理論
- Context の本質
- なぜ重要なのか
- 技術的背景

</div>

<div>

### 実践
- 3つのテクニック
- 実装パターン
- 設計チェックリスト

</div>

</div>

</div>

---

## ❓ 問題

<div class="card">

**経験ありませんか？**

- 長い会話でAIが的外れになる
- 重要な指示を無視される
- 同じ質問を何度も聞かれる

</div>

<div class="highlight">

**原因：** AIの記憶容量には限界がある

**解決：** Context Engineering

</div>

---

## 📚 Contextとは

<div class="card">

AIが参照する情報の全体

```
Context
├─ システム指示
├─ 会話履歴
├─ ツール定義
└─ 外部データ
```

</div>

---

## 📊 サイズと精度

<div class="stat">
<span class="stat-value">95%</span>
<span class="stat-label">4,000トークン</span>
</div>

<div class="stat">
<span class="stat-value">80%</span>
<span class="stat-label">20,000トークン</span>
</div>

<div class="stat">
<span class="stat-value">60%</span>
<span class="stat-label">100,000トークン</span>
</div>

---

## 🧠 なぜ劣化するのか

<div class="card">

### 人間の作業記憶と同じ

**人間：** 電話番号7桁は覚えられる、50桁は無理

**AI：** 短いContextは正確、長いと見失う

</div>

<div class="highlight">

**技術的理由：** n²の計算量

トークンが10倍 → 計算量100倍

</div>

---

## 💡 2つのEngineering

<div class="compare">

<div class="card">

### Prompt

効果的な指示を書く

**対象：** 1回の入力

**例：**
「簡潔に」
「ステップで」

</div>

<div class="card">

### Context

情報全体を管理

**対象：** 会話全体

**例：**
「古い会話削除」
「必要時取得」

</div>

</div>

---

## 🎯 3つの柱

<div class="card">

### 1. 構造設計
何を含めるか

### 2. 取得戦略
いつ読むか

### 3. 圧縮技術
どう減らすか

</div>

---

<!-- _class: lead -->

# 第1の柱
## 構造設計

---

## 📋 System Prompts

<div class="compare">

<div class="bad">

### ❌ 悪い例

```
優秀なアシスタントです
質問に答えてください
```

曖昧すぎる

</div>

<div class="good">

### ✅ 良い例

```
# 役割
技術Q&A

# ルール
1. コード例必須
2. リスク指摘
3. 代替案2つ

# 禁止
- 推測NG
- 古い情報NG
```

具体的

</div>

</div>

---

## 🛠️ Tools

<div class="compare">

<div class="bad">

### ❌ 重複

```
search_web()
google_search()
web_query()
internet_search()
```

どれを使う？

</div>

<div class="good">

### ✅ 明確

```
search_web(
  query: str,
  max: int = 5
)

Web検索実行
最新情報取得用
```

1機能=1Tool

</div>

</div>

---

## 📚 Examples

<div class="card">

### 質 > 量

</div>

<div class="compare">

<div class="bad">

**100個の類似例**

```
2+2=4
3+3=6
4+4=8
...
```

</div>

<div class="good">

**5個の多様例**

```
基本: 2+2=4
小数: 1.5+2.3
負数: -5+3=-2
大数: 1000+999
エラー: "a"+2
```

</div>

</div>

---

<!-- _class: lead -->

# 第2の柱
## 取得戦略

---

## ⚡ Just-in-Time

<div class="card">

### 必要な時に読む

**人間：** 本の内容を全部覚えない

**AI：** ファイルパスだけ記憶

</div>

---

## ⚡ 実装比較

<div class="compare">

<div class="bad">

### ❌ 全部読む

```
50ファイル全読込

100,000
トークン
```

重い

</div>

<div class="good">

### ✅ 必要時

```
一覧だけ保持
↓
read_file()

500
トークン
```

軽い

</div>

</div>

---

## 🔀 Hybrid Strategy

<div class="card">

### よく使う物を分ける

**Eager（最初）：**
- 頻度80%以上
- 1,000トークン以下

**Lazy（必要時）：**
- 頻度50%以下
- サイズ問わず

</div>

---

<!-- _class: lead -->

# 第3の柱
## 圧縮技術

---

## 🗜️ Compaction

<div class="card">

### 会話を要約

**いつ：** 上限80%到達

**保持：**
- ✅ 重要な決定
- ✅ ユーザー要求

**削除：**
- ❌ 冗長な出力
- ❌ 失敗した試行

</div>

---

## 🗜️ 圧縮例

<div class="compare">

<div style="font-size: 16px;">

### Before
5,000トークン

```
User: ファイル読込
AI: [500行コード]

User: エラー
AI: どのエラー？
User: FileNotFound
AI: [500行コード]

User: 動いた！
AI: [長い説明]
```

</div>

<div style="font-size: 16px;">

### After
500トークン

```
要約:
- 要求: ファイル読込
- 解決: try-except
- コード: [30行]
- 完了
```

</div>

</div>

---

## 📝 Note-Taking

<div class="card">

### Contextの外にメモ

**なぜ：** 圧縮で消えるから

**何を：**
- プロジェクト方針
- ユーザー好み
- 過去の失敗
- 重要な決定

</div>

---

## 📝 実例: Pokémon

<div class="card">

```
[外部メモ]
目標: リーグ制覇

戦略:
- 水タイプ育成
- レベル30進化
- 次は電気ジム

学び:
- 炎に水は有効
- 電気に水は不利
```

**結果：** 数千ステップで一貫性維持

</div>

---

## 🏗️ Sub-Agent

<div class="card">

```
    🎯 Main
    調整役

   ↙  ↓  ↘

🔧  🔧  🔧
Sub Sub Sub

専門 専門 専門
```

各自クリーンなContext

</div>

---

## 🏗️ 実例

<div class="card">

### タスク: 50ファイル処理

**Main：**
- 一覧取得
- 50個のSubに割当
- 結果統合

**Sub（×50）：**
- 1ファイル処理
- 要約返却（500トークン）

</div>

---

<!-- _class: lead -->

# 実践

---

## ✅ チェックリスト

<div class="card">

### Prompts
- [ ] 構造化？
- [ ] 具体的？
- [ ] 矛盾なし？

### Tools
- [ ] 重複なし？
- [ ] 簡潔（50トークン）？
- [ ] 目的明確？

</div>

---

## ✅ チェックリスト

<div class="card">

### 取得
- [ ] 全読込してない？
- [ ] インデックス？
- [ ] 必要時読込？

### 圧縮
- [ ] 80%で圧縮？
- [ ] 重要保持？
- [ ] 冗長削除？

</div>

---

## 📊 効果実測

<div class="card">

### Claude Code

<div class="compare">

<div>

**Before**
- 50,000トークン
- 精度70%
- 5秒

</div>

<div>

**After**
- 10,000トークン
- 精度95%
- 2秒

</div>

</div>

<div class="highlight">

**改善：** 80%削減・25%向上・2.5倍高速

</div>

</div>

---

## 🎯 3原則

<div class="card">

### 1. 最小限の高品質

量より質

### 2. 必要時取得

全部読まない

### 3. 構造化と圧縮

整理して保存

</div>

---

## 🚀 次のステップ

<div class="card">

### 今日から

1. **プロンプト見直し**
   無駄な情報削除

2. **履歴整理**
   重要部分だけ残す

3. **ツール厳選**
   使わないツール削除

</div>

---

<!-- _class: lead -->

> 最小限の高品質トークンで<br>最大の成果を

---

<!-- _class: lead -->

# Thank you

Context Engineering
