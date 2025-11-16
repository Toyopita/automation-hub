---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
style: |
  /* グローバル設定 */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');

  section {
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #2d3748;
    font-size: clamp(14px, 3vw, 24px);
    padding: 40px;
    line-height: 1.8;
  }

  section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: white;
    opacity: 0.95;
    z-index: -1;
  }

  /* ヘッダー */
  h1 {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: clamp(24px, 6vw, 56px);
    font-weight: 900;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 4px solid;
    border-image: linear-gradient(90deg, #667eea, #764ba2) 1;
    text-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
  }

  h2 {
    color: #667eea;
    font-size: clamp(20px, 4.5vw, 40px);
    font-weight: 700;
    margin-top: 30px;
    margin-bottom: 15px;
    padding-left: 15px;
    border-left: 6px solid #667eea;
  }

  h3 {
    color: #764ba2;
    font-size: clamp(18px, 4vw, 32px);
    font-weight: 700;
    margin-top: 20px;
  }

  /* テキスト */
  p {
    font-size: clamp(14px, 3vw, 24px);
    line-height: 1.8;
    margin: 15px 0;
  }

  strong {
    color: #e53e3e;
    font-weight: 700;
  }

  /* リスト */
  ul, ol {
    margin: 20px 0;
    padding-left: 30px;
  }

  li {
    margin: 10px 0;
    line-height: 1.8;
  }

  /* ハイライトボックス */
  .highlight {
    background: linear-gradient(135deg, #fef5e7 0%, #fdebd0 100%);
    padding: 25px;
    border-radius: 12px;
    border-left: 6px solid #f39c12;
    margin: 20px 0;
    box-shadow: 0 4px 15px rgba(243, 156, 18, 0.2);
    font-size: clamp(14px, 3vw, 22px);
  }

  /* カードボックス */
  .card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    margin: 20px 0;
    border: 2px solid #e2e8f0;
    transition: transform 0.3s ease;
  }

  /* コードブロック */
  pre {
    background: #2d3748;
    color: #e2e8f0;
    padding: 20px;
    border-radius: 10px;
    overflow-x: auto;
    font-size: clamp(12px, 2.5vw, 18px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    margin: 20px 0;
  }

  code {
    background: #2d3748;
    color: #e2e8f0;
    padding: 3px 8px;
    border-radius: 5px;
    font-family: 'Courier New', monospace;
  }

  /* テーブル */
  table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 25px 0;
    font-size: clamp(13px, 2.8vw, 20px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    border-radius: 10px;
    overflow: hidden;
  }

  thead {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  th {
    padding: 15px;
    font-weight: 700;
  }

  td {
    padding: 15px;
    border-bottom: 1px solid #e2e8f0;
  }

  tbody tr {
    background: white;
    transition: background 0.3s ease;
  }

  tbody tr:hover {
    background: #f7fafc;
  }

  /* ページネーション */
  section::after {
    color: #667eea;
    font-weight: 700;
    font-size: 18px;
  }

  /* リードページ */
  section.lead {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  section.lead h1 {
    font-size: clamp(28px, 7vw, 72px);
    margin-bottom: 30px;
  }

  /* グラデーション背景バリエーション */
  section[data-bg="blue"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  section[data-bg="green"] {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  }

  section[data-bg="orange"] {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  }

  section[data-bg="purple"] {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  }

  /* アイコンボックス */
  .icon-box {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 25px;
    border-radius: 50px;
    font-weight: 700;
    margin: 10px 5px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  }

  /* バッジ */
  .badge {
    display: inline-block;
    background: #e53e3e;
    color: white;
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 700;
    margin: 0 5px;
  }

  /* スマホ対応 */
  @media screen and (max-width: 768px) {
    section {
      padding: 20px;
    }
    .highlight, .card {
      padding: 15px;
    }
  }
---

<!-- _class: lead -->

# 🤖 AIエージェントのための<br>効果的なContext Engineering

<div class="icon-box">Anthropic Engineering Blog</div>

---

## 📚 Context Engineeringとは？

<div class="card">

**Context（コンテキスト）** <span class="badge">重要</span>
= LLMからサンプリングする際に含まれる**トークンの集合**

**Context Engineering** <span class="badge">重要</span>
= LLMの制約に対してトークンの有用性を**最適化**し、望ましい結果を一貫して達成すること

</div>

<div class="highlight">

🎯 **目的：** 最小限のトークンで最大の成果を出す

</div>

---

## 🔄 Prompt Engineering との違い

| 項目 | Prompt Engineering | Context Engineering |
|:---:|:---|:---|
| 📝 **焦点** | 効果的な指示を書く | トークン全体をキュレーション |
| 🔢 **ターン数** | 1回のやり取り | 複数ターンの会話 |
| 🎯 **重要点** | 指示の質 | Context全体の管理 |
| 🛠️ **対象** | プロンプト文 | システム指示・ツール・履歴 |

---

## 🧠 Context Engineeringの管理対象

<div class="card">

```
📦 Context State（コンテキストの状態）

├─ 📋 System Instructions（システム指示）
│   └─ AIの振る舞いを定義
│
├─ 🛠️  Tools（ツール定義）
│   └─ 使用可能な機能
│
├─ 📊 External Data（外部データ）
│   └─ ファイル・API・データベース
│
└─ 💬 Message History（会話履歴）
    └─ 過去のやり取り
```

</div>

---

## ⚠️ なぜContext Engineeringが重要なのか？

### 🔻 Context Rot（コンテキストの劣化）

<div class="highlight">

**トークン数が増えると精度が低下する現象**

```
トークン数:  少ない ───────→ 多い
      精度:  ⭐⭐⭐⭐⭐ ───→ ⭐⭐
```

</div>

<div class="card">

**問題点：**
- 有限な「注意の予算（attention budget）」
- Transformer構造は**n²のペア関係**を作る
- スケール時にパフォーマンスが劣化

</div>

---

## 🧠 人間の作業記憶との類似性

<div class="card" style="background: linear-gradient(135deg, #fef5e7 0%, #fdebd0 100%);">

### 👤 人間の作業記憶

- 容量が限られている
- 情報過多で混乱する
- 重要な情報を優先する

</div>

<div style="text-align: center; font-size: 32px; margin: 20px 0;">
↕️  **非常に似ている**  ↕️
</div>

<div class="card" style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);">

### 🤖 LLMの注意予算

- トークン数に限界がある
- 多すぎると劣化する
- 高品質トークンを優先する

</div>

---

## 📐 効果的なContextの構造 (1/3)

### 📋 System Prompts（システムプロンプト）

<div class="card">

**❌ 避けるべき**
- 過度に硬直化したロジック
- 曖昧すぎるガイダンス

**✅ 推奨**
- XML/Markdownで明確なセクション分け
- 最小限から始める
- 失敗モードに基づいて指示を追加

</div>

<div class="highlight">

**🎯 バランスが鍵：** 具体的すぎず、曖昧すぎず

</div>

---

## 📐 効果的なContextの構造 (2/3)

### 🛠️ Tools（ツール）

<div class="card">

**❌ 避けるべき**
- 機能が重複する肥大化したツールセット
- ツール選択に曖昧性がある

**✅ 推奨**
- トークン効率的な設計
- 最小限で焦点を絞った説明
- 各ツールの目的が明確

</div>

---

## 📐 効果的なContextの構造 (3/3)

### 📚 Examples（例）

<div class="highlight" style="text-align: center; font-size: 32px; padding: 40px;">

**質 > 量**

</div>

<div class="card">

**多様な標準例をキュレーション**
- ❌ 網羅的なエッジケース集
- ✅ 代表的で多様な使用例

💡 **「例は千の言葉に値する絵」**

</div>

---

## 🔍 Context取得戦略 (1/2)

### ⚡ Just-in-Time（必要な時に取得）

<div class="card">

```
💾 軽量な識別子を保持
   ├─ ファイルパス
   ├─ URL
   └─ データベースID

        ⬇️ 必要になったら

🛠️  ツールを使って動的に読み込み
   └─ 実行時にデータ取得
```

</div>

<div class="highlight">

**人間の認知と同じ：** 全て記憶せず、外部システムを活用

</div>

---

## 🔍 Context取得戦略 (2/2)

### 🔀 Hybrid Strategy（ハイブリッド戦略）

<div class="card">

**⚡ 事前取得（速度優先）**
- よく使うデータ
- 重要な設定ファイル

**＋**

**🔍 自律的探索（必要に応じて）**
- 詳細な調査が必要な時
- 動的にツールで取得

</div>

<div class="highlight">

**例：** Claude Code は CLAUDE.md を最初に読み込み、その後 glob/grep で必要な時に取得

</div>

---

## ⏱️ 長期タスクのテクニック (1/4)

### 🗜️ Compaction（圧縮）

<div class="card">

```
📝 会話がContext限界に近づく

        ⬇️

📦 要約・圧縮
   ├─ アーキテクチャの決定を保持
   ├─ 重要な詳細を保持
   └─ 冗長なツール出力を削除

        ⬇️

🔄 圧縮された要約で再開
```

</div>

---

## ⏱️ 長期タスクのテクニック (2/4)

### 📝 Structured Note-Taking（構造化メモ）

<div class="card">

**💭 Contextウィンドウ（揮発性）**
- 限界に達すると失われる

**⬇️ 永続化**

**📔 外部メモ（永続的）**
- 戦略的な情報を記録
- 要約をまたいで保持
- 数時間の一貫性を実現

</div>

<div class="highlight">

**例：** Claudeがポケモンをプレイし、何千ステップにもわたって戦略メモを維持

</div>

---

## ⏱️ 長期タスクのテクニック (3/4)

### 🏗️ Sub-Agent Architecture（サブエージェント構造）

<div class="card">

```
        🎯 Main Agent
           (調整役)

    ↙️      ↓      ↘️

🔧       🔧       🔧
Sub      Sub      Sub
Agent    Agent    Agent

専門特化  専門特化  専門特化
```

</div>

---

## ⏱️ 長期タスクのテクニック (4/4)

### 🏗️ Sub-Agent Architectureの利点

<div class="card" style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);">

**🎯 メインエージェント：**
- ワークフロー全体を調整
- タスクを分解して割り当て

</div>

<div class="card" style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);">

**🔧 サブエージェント：**
- クリーンなContextウィンドウで作業
- 焦点を絞ったタスクを処理
- 圧縮された要約を返す（1,000-2,000トークン）

</div>

---

## 💡 最終的なガイダンス

<div class="highlight" style="font-size: 1.5em; text-align: center; padding: 50px;">

**「望ましい結果の可能性を最大化する、<br>最小限の高品質トークンセットを見つける」**

</div>

<div class="card">

```
Context = 貴重で有限なリソース

    ↓

思慮深いキュレーションが必要

    ↓

モデルが改善しても、Context管理は重要
```

</div>

---

## 🎯 重要なポイント

<div class="card">

1. <span class="icon-box">✅</span> **Context Engineering ≠ Prompt Engineering**

2. <span class="icon-box">✅</span> **「注意の予算」を慎重に管理**

3. <span class="icon-box">✅</span> **System Prompts、Tools、Examplesのバランス**

4. <span class="icon-box">✅</span> **Just-in-Time取得戦略を使用**

5. <span class="icon-box">✅</span> **長期タスクには圧縮・メモ・サブエージェント**

6. <span class="icon-box">✅</span> **品質重視：トークンの質 > トークンの量**

</div>

---

## 📊 まとめ：効果的なContext Engineering

<div class="card">

```
🎯 目標：最小限で最大の成果

📋 明確なSystem Prompts
🛠️  効率的なTools
📚 厳選されたExamples
⚡ Just-in-Time取得
🗜️  適切な圧縮
📝 外部メモの活用
🏗️  Sub-Agent構造

        ⬇️

  🎉 高品質なAIエージェント
```

</div>

---

<!-- _class: lead -->

# 🙏 ありがとうございました！

<div class="icon-box" style="font-size: 20px;">Anthropic Engineering Blog</div>

🔗 [元記事を読む](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## 🔖 参考資料

<div class="card">

**📚 関連トピック：**
- Prompt Engineering のベストプラクティス
- LLMのTransformer構造
- 注意機構（Attention Mechanism）
- トークン化（Tokenization）

**💡 実装例：**
- Claude Code: Just-in-Time + Hybrid戦略
- Claude × ポケモン: 構造化メモの活用
- Sub-Agent: 複雑タスクの分割実行

</div>

---

<!-- _class: lead -->

# 💬 Q&A

<div class="highlight" style="font-size: 24px;">
ご質問がありましたら<br>お気軽にどうぞ！
</div>
