---
marp: true
theme: uncover
paginate: true
style: |
  section {
    font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
    font-size: 32px;
    padding: 70px;
    line-height: 1.8;
    background-color: #ffffff;
    color: #2c3e50;
  }
  h1 {
    font-size: 72px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 40px;
    line-height: 1.3;
  }
  h2 {
    font-size: 56px;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 30px;
    line-height: 1.4;
  }
  h3 {
    font-size: 40px;
    color: #34495e;
    margin-bottom: 25px;
    font-weight: 600;
  }
  p {
    font-size: 32px;
    line-height: 1.8;
    margin-bottom: 25px;
    color: #2c3e50;
  }
  ul, ol {
    font-size: 30px;
    line-height: 2.0;
    margin-bottom: 20px;
  }
  li {
    margin-bottom: 15px;
    color: #2c3e50;
  }
  code {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 26px;
    font-weight: 600;
  }
  pre {
    background: #2c3e50;
    color: #ecf0f1;
    padding: 20px;
    border-radius: 10px;
    font-size: 24px;
    line-height: 1.6;
  }
  pre code {
    background: transparent;
    padding: 0;
  }
  strong {
    color: #e74c3c;
    font-weight: 700;
  }
  blockquote {
    border-left: 8px solid #3498db;
    padding-left: 30px;
    font-style: italic;
    color: #2c3e50;
    font-size: 30px;
    background: #ecf0f1;
    padding: 25px;
    border-radius: 10px;
  }
  table {
    font-size: 26px;
    line-height: 1.8;
  }
  th {
    background: #3498db;
    color: white;
    padding: 15px;
    font-size: 28px;
  }
  td {
    padding: 12px;
  }
  /* 色付き背景用の文字色調整 */
  section[data-marpit-theme="uncover"][data-color="invert"],
  section[class~="lead"] {
    color: #2c3e50;
  }
  section[class~="lead"] h1,
  section[class~="lead"] h2,
  section[class~="lead"] p {
    color: inherit;
  }
  /* 背景色指定時の文字色を白に */
  section[style*="background"] h1,
  section[style*="background"] h2,
  section[style*="background"] h3,
  section[style*="background"] p,
  section[style*="background"] li {
    color: white !important;
  }
---

<!-- _class: lead -->
<!-- _paginate: false -->

![bg brightness:0.3](https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600)

# 🧠 コンテキスト
# エンジニアリング

**AIエージェントの新しいパラダイム**

出典: Anthropic Engineering Blog

---

<!-- _class: lead -->

# 🤔 問題提起

プロンプトだけでは
足りない時代へ

---

![bg right:45%](https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800)

## 従来のアプローチ

### プロンプトエンジニアリング
良い指示を書く

**しかし...**

- 長期タスクで破綻
- コンテキストが肥大化
- 性能が劣化

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1600)

# 🔄 パラダイム
# シフト

プロンプト → コンテキスト

---

## 定義の違い

**プロンプトエンジニアリング**
離散的タスク
効果的な指示を書く

↓ 進化

**コンテキストエンジニアリング**
反復的キュレーション
トークンセット最適化

---

![bg left:40%](https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800)

## コンテキストとは？

> LLMから推論するときに
> 含まれるトークンのセット

- システムプロンプト
- ツール定義
- メッセージ履歴
- 例・サンプル

**すべてがコンテキスト**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600)

# ⚠️ Context Rot

コンテキスト枯渇

---

## Context Rotの可視化

**短いコンテキスト（5K tokens）**
✅ 高性能（95%精度）

↓

**中程度（50K tokens）**
⚠️ 良好（85%精度）

↓

**長いコンテキスト（200K tokens）**
❌ 劣化（65%精度）

**トークン数 ↑ = 性能 ↓**

---

![bg right:50%](https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800)

## 原因

### Transformerの特性

- 訓練データは短いシーケンスが多い

- n² の関係性

- 注意予算が分散

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1600)

# 🎯 Goldilocks
# Zone

ゴルディロックスゾーン

---

## システムプロンプト校正

❌ **詳細すぎ**
脆弱・if-elseロジック
メンテナンス負荷大

↓

✅ **ゴルディロックス**
適度に具体的
適度に柔軟

↓

❌ **曖昧すぎ**
誤解を招く
一貫性なし

---

![bg left:45%](https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=800)

## バランス

### ❌ 詳細すぎる
脆弱・if-elseロジック

### ❌ 曖昧すぎる
具体性不足・誤解

### ✅ ゴルディロックス
**適度に具体的**
**適度に柔軟**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=1600)

# 🛠️ 実装戦略

---

![bg right:40%](https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800)

## 1. ツール最小化

### 原則

人間が判断できないなら
AIも判断できない

### 実践

- 明確な役割分担
- 重複を排除
- シンプルなIF

---

## ツール設計の良し悪し

### ❌ 悪い例
- get_file_content
- read_file
- load_file
- fetch_file_data

**どれを使う？混乱する**

### ✅ 良い例
- read_file

**1つだけ・明確**

---

![bg left:40%](https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800)

## 2. Just-in-Time
## 情報取得

### Claude Codeの例

❌ 全ファイルをロード

✅ 軽量な識別子のみ

**必要なときだけ
必要な情報を取得**

---

## 情報取得フロー

**1. AIエージェント → メタデータDB**
ファイル一覧取得

**2. メタデータDB → AIエージェント**
[file1.py, file2.py]（軽量）

**3. AIエージェント**
file1.py が必要と判断

**4. AIエージェント → ファイルシステム**
file1.py 読み込み

**5. ファイルシステム → AIエージェント**
内容返却

**コンテキスト節約**

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600)

# 📝 長期タスク
# 対応

---

![bg right:45%](https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=800)

## 3つの戦略

### 1️⃣ Compaction
圧縮・要約

### 2️⃣ Structured Notes
構造化メモ

### 3️⃣ Sub-agents
サブエージェント

---

## 1. Compaction

**長い会話（150K tokens）**

↓ 要約

**短い要約（10K tokens）**

↓ 新規コンテキスト

**新しいセッション（30K tokens）**

↓ 継続作業

**効率的な推論**

---

![bg left:40%](https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800)

## 2. Structured
## Notes

### 外部記憶を維持

Pokémon プレイの例:

- 数千ステップを記録
- 構造化されたメモ
- 永続的な記憶

**エージェントが自己管理**

---

## 3. Sub-agent アーキテクチャ

**Main Agent（統合・意思決定）**

↓ タスク委譲

**Sub-agent A（検索専門）**
**Sub-agent B（分析専門）**
**Sub-agent C（生成専門）**

↓ 要約返却

**Main Agent（統合）**

**分業で効率化**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1600)

# 💡 実例

Claude Code

---

![bg left:45%](https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800)

## Claude Code
## の設計

### コンテキスト最適化

- ファイルリストは軽量
- bashツールで動的分析
- 必要な情報だけロード

**200K枠を有効活用**

---

## Claude Code ツール構成

**Claude Code**

↓

- **Read** - ファイル読込
- **Write** - ファイル作成
- **Edit** - ファイル編集
- **Glob** - パターン検索
- **Grep** - コンテンツ検索
- **Bash** - 動的調査

**明確な役割分担**

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1600)

# 📊 ベスト
# プラクティス

---

![bg right:40%](https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800)

## 1. コンテキスト
## 予算

### 意識すべきこと

- トークン数を監視
- 不要な情報を削除
- 優先順位をつける

**貴重な資源として扱う**

---

## 2. 反復的改善サイクル

**実装**

↓ 測定

**パフォーマンス分析**

↓ 分析

**ボトルネック特定**

↓ 改善

**最適化実装**

↓ 測定（戻る）

**継続的に最適化**

---

![bg left:40%](https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800)

## 3. シンプルさ
## 優先

### 原則

- 複雑 → シンプル
- 多数 → 少数
- 曖昧 → 明確

**Occamの剃刀**

---

<!-- _class: lead -->

# 🎓 学習曲線

---

## 段階的アプローチ

**Level 1: プロンプト改善**
良い指示を書く

↓

**Level 2: ツール整理**
最小限のツールセット

↓

**Level 3: コンテキスト管理**
動的情報取得

↓

**Level 4: 長期タスク対応**
Compaction / Notes / Sub-agents

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=1600)

# ⚡ 重要な教訓

---

![bg right:45%](https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=800)

## 思考は
## コンテキストの
## 中で起こる

### Thinking in Context

すべての推論は
コンテキストに依存

---

## アナロジー

### 人間の作業環境

**散らかった机** → 集中できない

**整理された机** → 効率的

### AIのコンテキスト

**肥大化** → 性能低下

**最適化** → 高性能

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600)

# 📚 まとめ

---

## Key Takeaways

### 1. パラダイムシフト
プロンプト → コンテキスト

### 2. Context Rot対策
トークン数を厳選

### 3. Goldilocks Zone
適度な具体性と柔軟性

---

![bg left:40%](https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800)

## 続き

### 4. ツール最小化
明確・シンプル・少数

### 5. 長期タスク
Compaction / Notes / Sub-agents

### 6. 反復的改善
継続的な最適化

---

<!-- _class: lead -->
<!-- _color: white -->

![bg](https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=1600)

# 🚀 実践へ

---

![bg right:45%](https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800)

## 今日から始める

### Step 1
システムプロンプトを見直す

### Step 2
ツールを整理

### Step 3
コンテキスト監視

---

## リソース

### 📖 Original Article
https://www.anthropic.com/
engineering/effective-context-
engineering-for-ai-agents

### 💻 Claude Code
実例として参考に

### 🐙 GitHub
コミュニティのベストプラクティス

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _color: white -->

![bg brightness:0.3](https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600)

# 🎉 ありがとう
# ございました

Context is everything.

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _color: white -->

![bg brightness:0.2](https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1600)

# 🧠 Think in Context

コンテキストエンジニアリングで
AIエージェントを最適化しよう

Happy Engineering! 🚀

---
