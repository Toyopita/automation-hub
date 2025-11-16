---
marp: true
theme: uncover
paginate: true
style: |
  section {
    font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
    font-size: 26px;
    padding: 60px;
  }
  h1 {
    font-size: 56px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 25px;
    line-height: 1.2;
  }
  h2 {
    font-size: 44px;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 20px;
    line-height: 1.3;
  }
  h3 {
    font-size: 32px;
    color: #34495e;
    margin-bottom: 18px;
  }
  p {
    font-size: 24px;
    line-height: 1.6;
    margin-bottom: 18px;
  }
  ul, ol {
    font-size: 23px;
    line-height: 1.7;
  }
  code {
    background: #f8f9fa;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 20px;
  }
  strong {
    color: #e74c3c;
    font-weight: 700;
  }
  blockquote {
    border-left: 5px solid #3498db;
    padding-left: 20px;
    font-style: italic;
    color: #555;
  }
---

<!-- _class: lead -->
<!-- _paginate: false -->

![bg brightness:0.3](https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600)

# 🧠 コンテキスト
# エンジニアリング

**AIエージェントの新しいパラダイム**

*出典: Anthropic Engineering Blog*

---

<!-- _class: lead -->

# 🤔 問題提起

プロンプトだけでは
足りない時代へ

---

![bg right:45%](https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800)

## **従来のアプローチ**

### プロンプトエンジニアリング
「良い指示を書く」

**しかし...**
- 長期タスクで破綻
- コンテキストが肥大化
- 性能が劣化

---

<!-- _class: lead -->
<!-- _backgroundColor: #3498db -->
<!-- _color: white -->

# 🔄 パラダイムシフト

プロンプト → コンテキスト

---

## **定義の違い**

### プロンプトエンジニアリング
**離散的なタスク**
効果的な指示を書く

### コンテキストエンジニアリング
**反復的なキュレーション**
最適なトークンセットを維持

---

![bg left:40%](https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800)

## **コンテキストとは？**

> 「LLMから推論するときに
> 含まれるトークンのセット」

- システムプロンプト
- ツール定義
- メッセージ履歴
- 例・サンプル

**すべてが「コンテキスト」**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600)

# ⚠️ Context Rot

コンテキスト枯渇

---

![bg right:50%](https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800)

## **Context Rotとは？**

トークン数が増えると
**性能が低下する現象**

### 原因
- 訓練データは短いシーケンスが多い
- Transformerは n² の関係性
- 注意予算が分散

---

## **具体例**

### 200Kトークンのコンテキスト
- 情報検索能力が低下
- 重要な情報を見落とす
- 応答が曖昧になる

### 対策
**コンテキストを厳選する**

---

<!-- _class: lead -->
<!-- _backgroundColor: #f39c12 -->
<!-- _color: white -->

# 🎯 Goldilocks Zone

ゴルディロックスゾーン

---

![bg left:45%](https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=800)

## **ちょうど良い**
## **システムプロンプト**

### ❌ 詳細すぎる
脆弱・if-elseロジック

### ❌ 曖昧すぎる
具体性不足・誤解

### ✅ ゴルディロックス
**適度に具体的**
**適度に柔軟**

---

## **校正スペクトラム**

```
詳細すぎ ←────────→ 曖昧すぎ
  (脆弱)    ✅最適    (不十分)
           Goldilocks
```

**強力なヒューリスティック**
+
**柔軟な適応力**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=1600)

# 🛠️ 実装戦略

---

![bg right:40%](https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800)

## **1. ツール最小化**

### 原則
「人間が判断できないなら
AIも判断できない」

### 実践
- 明確な役割分担
- 重複を排除
- シンプルなインターフェース

---

## **悪い例 vs 良い例**

### ❌ 悪い例
```python
get_file_content(path)
read_file(path)
load_file(path)
fetch_file_data(path)
```
**どれを使う？混乱する**

### ✅ 良い例
```python
read_file(path)
```
**1つだけ。明確。**

---

![bg left:40%](https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800)

## **2. Just-in-Time**
## **情報取得**

### Claude Codeの例

❌ 全ファイルをロード
✅ 軽量な識別子のみ

**必要なときだけ
必要な情報を取得**

---

## **実装パターン**

```python
# ❌ 全部読み込む
files = [read_file(f) for f in all_files]

# ✅ メタデータだけ
file_list = [{"name": f, "size": s}
             for f, s in get_file_metadata()]

# 必要なときだけ読む
content = read_file(selected_file)
```

**コンテキスト節約**

---

<!-- _class: lead -->
<!-- _backgroundColor: #9b59b6 -->
<!-- _color: white -->

# 📝 長期タスク対応

---

![bg right:45%](https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=800)

## **3つの戦略**

### 1️⃣ Compaction
圧縮・要約

### 2️⃣ Structured Notes
構造化メモ

### 3️⃣ Sub-agents
サブエージェント

---

## **1. Compaction**

### 会話を要約して再開

```
長い会話
    ↓ 要約
短い要約 + 新規コンテキスト
    ↓ 再開
新しいセッション
```

**コンテキストをリセット**

---

![bg left:40%](https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800)

## **2. Structured Notes**

### 外部記憶を維持

Pokémon プレイの例:
- 数千ステップを記録
- 構造化されたメモ
- 永続的な記憶

**エージェントが自己管理**

---

## **メモの例**

```markdown
# 探索状況
- ハナダシティ到着
- ジムリーダー カスミと対戦予定
- 手持ち: ピカチュウ Lv.12, ゼニガメ Lv.10

# 次のステップ
1. ポケモンセンターで回復
2. カスミに挑戦
3. 勝利後、次の町へ
```

**構造化で検索しやすく**

---

![bg right:40%](https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800)

## **3. Sub-agents**

### 専門エージェント

- 焦点を絞ったタスク
- 凝縮された要約を返す
- メインエージェントに統合

**分業で効率化**

---

## **Sub-agent アーキテクチャ**

```
Main Agent
    ↓ タスク委譲
Sub-agent A (検索専門)
Sub-agent B (分析専門)
Sub-agent C (生成専門)
    ↓ 要約を返す
Main Agent (統合)
```

**各エージェントは小さなコンテキスト**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1600)

# 💡 実例

Claude Code

---

![bg left:45%](https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800)

## **Claude Codeの設計**

### コンテキスト最適化

- ファイルリストは軽量
- bashツールで動的分析
- 必要な情報だけロード

**200K枠を有効活用**

---

## **ツールの使い分け**

### Read
ファイル内容を取得

### Glob
パターンでファイル検索

### Grep
コンテンツ検索

### Bash
動的な調査

**明確な役割分担**

---

<!-- _class: lead -->
<!-- _backgroundColor: #2ecc71 -->
<!-- _color: white -->

# 📊 ベストプラクティス

---

![bg right:40%](https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800)

## **1. コンテキスト予算**

### 意識すべきこと
- トークン数を常に監視
- 不要な情報を削除
- 優先順位をつける

**貴重な資源として扱う**

---

## **2. 反復的改善**

```
実装 → 測定 → 分析 → 改善
  ↑                    ↓
  └────────────────────┘
```

**一度で完璧にしない**
**継続的に最適化**

---

![bg left:40%](https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800)

## **3. シンプルさ優先**

### 原則
- 複雑 → シンプル
- 多数 → 少数
- 曖昧 → 明確

**Occamの剃刀**

---

<!-- _class: lead -->

# 🎓 学習曲線

---

## **段階的アプローチ**

### Level 1: プロンプト改善
良い指示を書く

### Level 2: ツール整理
最小限のツールセット

### Level 3: コンテキスト管理
動的な情報取得

### Level 4: 長期タスク
Compaction / Notes / Sub-agents

---

<!-- _class: lead -->
<!-- _backgroundColor: #e74c3c -->
<!-- _color: white -->

# ⚡ 重要な教訓

---

![bg right:45%](https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=800)

## **思考はコンテキストの**
## **中で起こる**

### Thinking in Context

すべての推論は
コンテキストに依存

**だからこそ
コンテキスト設計が重要**

---

## **アナロジー**

### 人間の作業環境

散らかった机 → 集中できない
整理された机 → 効率的

### AIのコンテキスト

肥大化 → 性能低下
最適化 → 高性能

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600)

# 📚 まとめ

---

## **Key Takeaways**

### 1. パラダイムシフト
プロンプト → コンテキスト

### 2. Context Rot対策
トークン数を厳選

### 3. Goldilocks Zone
適度な具体性と柔軟性

### 4. ツール最小化
明確・シンプル・少数

---

![bg left:40%](https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800)

## **5. 長期タスク**

- Compaction
- Structured Notes
- Sub-agents

### 6. 反復的改善
継続的な最適化

---

<!-- _class: lead -->
<!-- _backgroundColor: #3498db -->
<!-- _color: white -->

# 🚀 実践へ

---

![bg right:45%](https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800)

## **今日から始める**

### Step 1
システムプロンプトを見直す
→ Goldilocks Zone?

### Step 2
ツールを整理
→ 重複を削除

### Step 3
コンテキスト監視
→ トークン数を確認

---

## **リソース**

### 📖 Original Article
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 💻 Claude Code
実例として参考に

### 🐙 GitHub
コミュニティのベストプラクティス

---

<!-- _class: lead -->
<!-- _paginate: false -->

![bg brightness:0.3](https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600)

# 🎉 ありがとう
# ございました

**Context is everything.**

---

<!-- _class: lead -->
<!-- _backgroundColor: #2c3e50 -->
<!-- _color: white -->
<!-- _paginate: false -->

# 🧠 Think in Context

**コンテキストエンジニアリングで**
**AIエージェントを最適化しよう**

*Happy Engineering! 🚀*

---
