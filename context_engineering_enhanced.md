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
  .mermaid {
    background: white;
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

```mermaid
graph LR
    A[プロンプト<br/>エンジニアリング] -->|進化| B[コンテキスト<br/>エンジニアリング]
    A -->|特徴| C[離散的タスク]
    A -->|焦点| D[指示を書く]
    B -->|特徴| E[反復的キュレーション]
    B -->|焦点| F[トークンセット最適化]

    style A fill:#e74c3c,color:#fff
    style B fill:#2ecc71,color:#fff
```

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

## **Context Rotの可視化**

```mermaid
graph TD
    A[短いコンテキスト<br/>5K tokens] -->|性能| B[高性能 ✅<br/>95%精度]
    C[中程度<br/>50K tokens] -->|性能| D[良好 ⚠️<br/>85%精度]
    E[長いコンテキスト<br/>200K tokens] -->|性能| F[劣化 ❌<br/>65%精度]

    style B fill:#2ecc71,color:#fff
    style D fill:#f39c12,color:#fff
    style F fill:#e74c3c,color:#fff
```

**トークン数 ↑ = 性能 ↓**

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

## **システムプロンプト校正**

```mermaid
graph LR
    A[詳細すぎ] -->|脆弱| B[if-elseロジック<br/>メンテナンス負荷大]
    C[ゴルディロックス] -->|最適| D[適度に具体的<br/>適度に柔軟]
    E[曖昧すぎ] -->|不十分| F[誤解を招く<br/>一貫性なし]

    style A fill:#e74c3c,color:#fff
    style C fill:#2ecc71,color:#fff
    style E fill:#95a5a6,color:#fff
    style D fill:#f39c12,color:#000
```

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

## **ツール設計の良し悪し**

```mermaid
graph TD
    subgraph "❌ 悪い例"
    A1[get_file_content]
    A2[read_file]
    A3[load_file]
    A4[fetch_file_data]
    end

    subgraph "✅ 良い例"
    B1[read_file]
    end

    A1 -.混乱.-> C[どれ使う？]
    A2 -.混乱.-> C
    A3 -.混乱.-> C
    A4 -.混乱.-> C
    B1 -->|明確| D[1つだけ]

    style B1 fill:#2ecc71,color:#fff
```

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

## **情報取得フロー**

```mermaid
sequenceDiagram
    participant Agent as AIエージェント
    participant Meta as メタデータDB
    participant File as ファイルシステム

    Agent->>Meta: ファイル一覧取得
    Meta-->>Agent: [file1.py, file2.py]<br/>(軽量)
    Agent->>Agent: file1.py が必要と判断
    Agent->>File: file1.py 読み込み
    File-->>Agent: 内容返却

    Note over Agent,File: コンテキスト節約
```

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

```mermaid
graph TD
    A[長い会話<br/>150K tokens] -->|要約| B[短い要約<br/>10K tokens]
    B -->|新規コンテキスト| C[新しいセッション<br/>30K tokens]
    C -->|継続作業| D[効率的な推論]

    style A fill:#e74c3c,color:#fff
    style B fill:#f39c12,color:#fff
    style C fill:#2ecc71,color:#fff
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

## **3. Sub-agent アーキテクチャ**

```mermaid
graph TD
    Main[Main Agent<br/>統合・意思決定]

    Main -->|検索タスク| A[Sub-agent A<br/>検索専門]
    Main -->|分析タスク| B[Sub-agent B<br/>分析専門]
    Main -->|生成タスク| C[Sub-agent C<br/>生成専門]

    A -->|要約返却| Main
    B -->|要約返却| Main
    C -->|要約返却| Main

    style Main fill:#3498db,color:#fff
    style A fill:#2ecc71,color:#fff
    style B fill:#9b59b6,color:#fff
    style C fill:#e67e22,color:#fff
```

---

![bg right:40%](https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800)

## **Sub-agents のメリット**

- 焦点を絞ったタスク
- 小さなコンテキスト
- 並列処理可能
- 凝縮された要約

**分業で効率化**

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

## **Claude Code ツール構成**

```mermaid
graph LR
    subgraph "ツール群"
    A[Read<br/>ファイル読込]
    B[Write<br/>ファイル作成]
    C[Edit<br/>ファイル編集]
    D[Glob<br/>パターン検索]
    E[Grep<br/>コンテンツ検索]
    F[Bash<br/>動的調査]
    end

    G[Claude Code] --> A
    G --> B
    G --> C
    G --> D
    G --> E
    G --> F

    style G fill:#3498db,color:#fff
```

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

## **2. 反復的改善サイクル**

```mermaid
graph TD
    A[実装] -->|測定| B[パフォーマンス分析]
    B -->|分析| C[ボトルネック特定]
    C -->|改善| D[最適化実装]
    D -->|測定| B

    style A fill:#3498db,color:#fff
    style B fill:#f39c12,color:#fff
    style C fill:#e74c3c,color:#fff
    style D fill:#2ecc71,color:#fff
```

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

```mermaid
graph TD
    L1[Level 1<br/>プロンプト改善] --> L2[Level 2<br/>ツール整理]
    L2 --> L3[Level 3<br/>コンテキスト管理]
    L3 --> L4[Level 4<br/>長期タスク対応]

    L1 -.->|習得| S1[良い指示を書く]
    L2 -.->|習得| S2[最小限のツールセット]
    L3 -.->|習得| S3[動的情報取得]
    L4 -.->|習得| S4[Compaction/Notes/<br/>Sub-agents]

    style L4 fill:#2ecc71,color:#fff
```

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

```mermaid
graph LR
    subgraph "人間の作業環境"
    A[散らかった机] -.->|結果| B[集中できない]
    C[整理された机] -->|結果| D[効率的]
    end

    subgraph "AIのコンテキスト"
    E[肥大化] -.->|結果| F[性能低下]
    G[最適化] -->|結果| H[高性能]
    end

    style B fill:#e74c3c,color:#fff
    style D fill:#2ecc71,color:#fff
    style F fill:#e74c3c,color:#fff
    style H fill:#2ecc71,color:#fff
```

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
