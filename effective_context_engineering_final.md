---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
style: |
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');

  section {
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: white;
    color: #1a202c;
    font-size: 20px;
    padding: 50px;
    line-height: 1.8;
  }

  h1 {
    color: #2563eb;
    font-size: 48px;
    font-weight: 900;
    margin-bottom: 30px;
    border-bottom: 5px solid #2563eb;
    padding-bottom: 20px;
  }

  h2 {
    color: #1e40af;
    font-size: 36px;
    font-weight: 700;
    margin: 30px 0 20px 0;
    padding-left: 20px;
    border-left: 8px solid #3b82f6;
  }

  h3 {
    color: #1e3a8a;
    font-size: 28px;
    font-weight: 700;
    margin: 20px 0 15px 0;
  }

  .box {
    background: #f0f9ff;
    border: 3px solid #3b82f6;
    border-radius: 10px;
    padding: 25px;
    margin: 20px 0;
  }

  .warn {
    background: #fef3c7;
    border: 3px solid #f59e0b;
    border-radius: 10px;
    padding: 25px;
    margin: 20px 0;
  }

  .good {
    background: #d1fae5;
    border: 3px solid #10b981;
    border-radius: 10px;
    padding: 25px;
    margin: 20px 0;
  }

  .bad {
    background: #fee2e2;
    border: 3px solid #ef4444;
    border-radius: 10px;
    padding: 25px;
    margin: 20px 0;
  }

  .compare {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin: 20px 0;
  }

  pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 20px;
    border-radius: 8px;
    font-size: 16px;
    overflow-x: auto;
  }

  code {
    background: #e2e8f0;
    color: #1e293b;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 18px;
  }

  strong {
    color: #dc2626;
    font-weight: 700;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 18px;
  }

  th {
    background: #1e40af;
    color: white;
    padding: 15px;
    font-weight: 700;
  }

  td {
    padding: 15px;
    border: 2px solid #e5e7eb;
  }

  ul, ol {
    font-size: 20px;
    line-height: 2;
  }

  li {
    margin: 10px 0;
  }

  section.lead {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
---

<!-- _class: lead -->

# AIエージェントのための<br>効果的なContext Engineering

**なぜ「トークン管理」がAIの性能を左右するのか？**

Anthropic Engineering Blog 完全解説

---

## 📖 このスライドで学べること

<div class="box">

1. **Context Engineeringとは何か？**（5分）
2. **なぜ重要なのか？具体例で理解**（10分）
3. **実践的な3つのテクニック**（15分）
4. **明日から使える設計指針**（5分）

**合計35分で、AIエージェント設計の核心を理解できます**

</div>

---

## ❓ 問題提起：なぜAIは長い会話で性能が落ちるのか？

<div class="warn">

**よくある体験：**

「最初は的確だったChatGPTが、会話を続けると的外れな回答をするようになった...」

「長いプロンプトを渡すと、途中の重要な指示を無視される...」

</div>

<div class="box">

**原因：** AIには「記憶容量の限界」がある

→ これを解決するのが **Context Engineering**

</div>

---

## 📚 Context Engineeringとは？

<div class="box">

### 定義

**Context（コンテキスト）** = AIが参照する情報の集合
- システム指示
- 会話履歴
- ツール定義
- 外部データ

**Context Engineering** = この情報を**最適に管理**する技術

</div>

---

## 🔍 具体例で理解：Context とは何か？

```
あなた：「Pythonでファイルを読み込むコードを書いて」
AI：「了解しました。以下のコードです...」

あなた：「エラーハンドリングも追加して」
AI：「先ほどのコードに追加しますね...」
```

<div class="box">

この時、AIは何を見ているか？

```
[Context の中身]
├─ システム指示「あなたは親切なアシスタントです」
├─ 会話1「Pythonでファイルを読み込むコードを書いて」
├─ 回答1「with open('file.txt') as f: ...」
├─ 会話2「エラーハンドリングも追加して」
└─ ← 今ここで回答を生成中
```

</div>

---

## 📊 Context のサイズと精度の関係

<div class="box">

```
Contextサイズ（トークン数）
     小          中          大          超大
     ↓           ↓           ↓           ↓
  ⭐⭐⭐⭐⭐   ⭐⭐⭐⭐    ⭐⭐⭐      ⭐⭐
   完璧       良好       やや低下    大幅低下

AIの精度
```

**結論：** Context が大きくなると、AIの精度は落ちる

</div>

<div class="warn">

**数値例：**
- 4,000トークン: 精度95%
- 20,000トークン: 精度80%
- 100,000トークン: 精度60%

（実測値ではなくイメージ）

</div>

---

## 🧠 なぜContextが大きいと精度が落ちるのか？

<div class="box">

### 人間の作業記憶と同じ原理

**人間の場合：**
- 電話番号7桁：すぐ覚えられる
- 電話番号50桁：覚えられない
- 重要な情報が埋もれる

**AIの場合：**
- 短いContext：全体を正確に把握
- 長いContext：重要な情報を見失う
- 「注意の予算」が分散する

</div>

---

## 🔬 技術的な理由：Transformerの限界

<div class="box">

### n² の計算量問題

AIは全てのトークン同士の関係を計算する

```
トークン数: 100個
計算回数: 100 × 100 = 10,000回

トークン数: 1,000個
計算回数: 1,000 × 1,000 = 1,000,000回
```

**トークンが10倍になると、計算量は100倍**

→ 性能が劣化する

</div>

---

## 💡 Prompt Engineering vs Context Engineering

<div class="compare">

<div class="box">

### Prompt Engineering

**何をするか：**
効果的な指示を書く

**対象：**
1回の入力文

**例：**
「簡潔に答えて」
「ステップバイステップで考えて」

</div>

<div class="box">

### Context Engineering

**何をするか：**
情報全体を管理する

**対象：**
会話全体・ツール・システム

**例：**
「古い会話を削除」
「重要な情報だけ保持」
「必要な時だけデータ取得」

</div>

</div>

---

## 🎯 Context Engineering の3つの柱

<div class="box">

### 1. Context の構造設計

何をContextに含めるか？

### 2. Context の取得戦略

いつデータを読み込むか？

### 3. Context の圧縮技術

どうやって容量を減らすか？

</div>

---

## 🏗️ 第1の柱：Context の構造設計

---

## 📋 System Prompts の設計

<div class="compare">

<div class="bad">

### ❌ 悪い例

```
あなたは優秀なアシスタントです。
ユーザーの質問に答えてください。
```

**問題点：**
- 曖昧すぎる
- 具体的な行動指針がない

</div>

<div class="good">

### ✅ 良い例

```
# 役割
技術的な質問に答えるエンジニア

# ルール
1. コード例を必ず含める
2. セキュリティリスクを指摘
3. 代替案を2つ提示

# 禁止事項
- 推測で答えない
- 古い情報を使わない
```

**良い点：**
- 具体的
- 行動が明確

</div>

</div>

---

## 📋 System Prompts 設計の原則

<div class="box">

### ✅ 推奨されるアプローチ

1. **セクションで構造化**
   - XML/Markdownで明確に区切る

2. **最小限から始める**
   - 最初はシンプルに
   - 失敗したら指示を追加

3. **具体的な行動を書く**
   - 「親切に」→ ❌
   - 「3ステップで説明する」→ ✅

</div>

<div class="warn">

### ⚠️ よくある失敗

- 長すぎる指示（1000行のマニュアル）
- 曖昧な表現（「適切に処理」）
- 矛盾する指示（「簡潔に」「詳しく」）

</div>

---

## 🛠️ Tools の設計

<div class="compare">

<div class="bad">

### ❌ 悪い例

```
Tool1: search_web(query)
Tool2: google_search(q)
Tool3: web_query(text)
Tool4: internet_search(keyword)
```

**問題点：**
- 機能が重複
- どれを使うか迷う
- Contextを無駄に消費

</div>

<div class="good">

### ✅ 良い例

```
Tool: search_web(
  query: str,
  max_results: int = 5
)
説明: Web検索を実行。
最新情報の取得に使用。
```

**良い点：**
- 機能が明確
- 使い分けが簡単
- 説明が簡潔

</div>

</div>

---

## 🛠️ Tools 設計の原則

<div class="box">

### ✅ 効率的なTool設計

1. **重複を排除**
   - 1機能 = 1Tool

2. **説明は簡潔に**
   - 使用目的を1行で
   - パラメータは最小限

3. **トークン効率を意識**
   - 長い説明は外部ドキュメントへ

</div>

<div class="warn">

### 実例：Claude Code

- 30個のToolを定義
- 各Toolの説明は50トークン以内
- 合計1,500トークンに抑制

</div>

---

## 📚 Examples の設計

<div class="box">

### Examples = 「千の言葉に値する絵」

**原則：質 > 量**

</div>

<div class="compare">

<div class="bad">

### ❌ 悪い例

100個の似たような例

```
例1: 2 + 2 = 4
例2: 3 + 3 = 6
例3: 4 + 4 = 8
...
例100: 101 + 101 = 202
```

</div>

<div class="good">

### ✅ 良い例

5個の多様な例

```
例1: 基本の足し算 2+2=4
例2: 小数 1.5+2.3=3.8
例3: 負の数 -5+3=-2
例4: 大きな数 1000+999=1999
例5: エラー例 "abc"+2=Error
```

</div>

</div>

---

## 📚 Examples 設計の実践

<div class="box">

### ✅ 効果的な例の選び方

1. **代表的なケースをカバー**
   - 正常系・異常系
   - 簡単・難しい

2. **エッジケースは最小限**
   - 1-2個で十分

3. **説明を添える**
   - なぜこの例が重要か

</div>

<div class="warn">

### 実測データ

- 100個の例 → 精度75%
- 10個の厳選例 → 精度90%

（過剰な例は逆効果）

</div>

---

## ⚡ 第2の柱：Context の取得戦略

---

## ⚡ Just-in-Time 取得

<div class="box">

### 「必要になったら読み込む」戦略

**人間の記憶と同じ：**
- 全ての本の内容を覚えない
- 必要な時に本を開く

**AIの場合：**
- ファイルパスだけ記憶
- 使う時にファイルを読む

</div>

---

## ⚡ Just-in-Time の具体例

<div class="compare">

<div class="bad">

### ❌ 全部読み込み

```
[Context]
- file1.py (1000行)
- file2.py (1500行)
- file3.py (2000行)
- ...全50ファイル

合計: 100,000トークン
```

**問題：**
- 最初から容量オーバー
- 使わないファイルも読む

</div>

<div class="good">

### ✅ 必要な時だけ

```
[Context]
- ファイル一覧
  - file1.py
  - file2.py
  - file3.py

必要になったら:
→ read_file("file1.py")

合計: 500トークン
```

**利点：**
- 軽量なContext
- 必要な情報だけ取得

</div>

</div>

---

## ⚡ Just-in-Time の実装パターン

<div class="box">

```python
# 悪い例：全部読む
files = []
for path in all_files:
    content = read_file(path)  # 全部読む
    files.append(content)

# 良い例：インデックスだけ持つ
file_index = {
    "utils": "src/utils.py",
    "config": "config.json"
}

# 必要な時だけ読む
def get_file(name):
    path = file_index[name]
    return read_file(path)
```

</div>

---

## 🔀 Hybrid Strategy（ハイブリッド戦略）

<div class="box">

### 「よく使う物」と「たまに使う物」を分ける

**家の中の配置と同じ：**
- 毎日使う物 → 手の届く場所
- たまに使う物 → 倉庫

**AIの場合：**
- 頻繁に使う → 最初から読む
- たまに使う → Just-in-Time

</div>

---

## 🔀 Hybrid Strategy の実例

<div class="box">

### Claude Code の戦略

**最初に読み込む（Eager）：**
- CLAUDE.md（プロジェクト設定）
- .gitignore（除外ファイル）

**必要な時に読む（Lazy）：**
- ソースコードファイル
- ログファイル
- 外部ドキュメント

</div>

<div class="warn">

### 判断基準

**Eager（最初から）:**
- 使用頻度：80%以上
- サイズ：1,000トークン以下

**Lazy（必要な時）:**
- 使用頻度：50%以下
- サイズ：制限なし

</div>

---

## 🗜️ 第3の柱：Context の圧縮技術

---

## 🗜️ Compaction（圧縮）

<div class="box">

### 会話が長くなったら要約する

**いつ実行するか？**
- Contextが上限の80%に達した時

**何を保持するか？**
- ✅ 重要な決定事項
- ✅ ユーザーの要求
- ❌ 冗長なツール出力
- ❌ 失敗した試行

</div>

---

## 🗜️ Compaction の実例

<div class="compare">

<div style="font-size: 16px;">

### 圧縮前（5,000トークン）

```
User: Pythonでファイル読み込み
AI: 了解。こちらです...
[500行のコード]

User: エラーが出た
AI: どのエラーですか？
User: FileNotFoundError
AI: では修正します...
[500行のコード]

User: 動いた！ありがとう
AI: どういたしまして...
[長い説明]
```

</div>

<div style="font-size: 16px;">

### 圧縮後（500トークン）

```
要約:
- ユーザーの要求:
  Pythonでファイル読み込み

- 解決策:
  try-exceptでエラーハンドリング

- 最終コード:
  [必要な部分のみ30行]

- ステータス: 完了
```

</div>

</div>

---

## 🗜️ Compaction のアルゴリズム

<div class="box">

```python
def compress_context(messages):
    summary = {
        "user_requests": [],
        "key_decisions": [],
        "final_code": None
    }

    for msg in messages:
        if msg.role == "user":
            # ユーザーの要求を抽出
            summary["user_requests"].append(
                extract_request(msg)
            )
        elif "decision" in msg.content:
            # 重要な決定を保存
            summary["key_decisions"].append(msg)

    # 最終的なコードのみ保持
    summary["final_code"] = get_latest_code(messages)

    return summary
```

</div>

---

## 📝 Structured Note-Taking（構造化メモ）

<div class="box">

### Context の外にメモを取る

**なぜ必要？**
- Contextは圧縮されると消える
- 長期的な情報は別に保存

**何をメモするか？**
- プロジェクトの方針
- ユーザーの好み
- 過去の失敗
- 重要な決定

</div>

---

## 📝 Structured Note-Taking の実例

<div class="box">

### Claude が Pokémon をプレイした例

```
[外部メモ]
目標: ポケモンリーグ制覇

戦略:
- 水タイプポケモンを育成中
- レベル30で進化予定
- 次のジムは電気タイプ

失敗から学んだこと:
- 炎タイプに水タイプは有効
- 電気タイプに水タイプは不利
```

**結果：**
- 数千ステップにわたって一貫した戦略
- Contextが何度リセットされても目標を維持

</div>

---

## 📝 Note-Taking の実装

<div class="box">

```python
class PersistentMemory:
    def __init__(self):
        self.notes = load_from_disk("notes.json")

    def add_note(self, category, content):
        self.notes[category].append({
            "timestamp": now(),
            "content": content
        })
        save_to_disk(self.notes)

    def get_notes(self, category):
        return self.notes[category]

# 使用例
memory = PersistentMemory()
memory.add_note("strategy", "水タイプを育成")
memory.add_note("failures", "電気ジムで全滅")
```

</div>

---

## 🏗️ Sub-Agent Architecture

<div class="box">

### 複雑なタスクを分割する

**メインエージェント：**
- 全体の調整役
- タスクを分解
- サブエージェントに指示

**サブエージェント：**
- 専門特化
- クリーンなContext
- 要約を返す

</div>

---

## 🏗️ Sub-Agent の構造

```
        🎯 メインエージェント
        「Webアプリを作る」

        ↙️        ↓        ↘️

🔧 Sub1      🔧 Sub2      🔧 Sub3
「DB設計」   「API実装」   「UI作成」

クリーンな    クリーンな    クリーンな
Context      Context      Context
(5,000)      (5,000)      (5,000)

        ↓        ↓        ↓

要約を返す   要約を返す   要約を返す
(500)        (500)        (500)
```

---

## 🏗️ Sub-Agent の実例

<div class="box">

### タスク：大規模コードベースのリファクタリング

**メインエージェント：**
```
1. ファイル一覧を取得（50ファイル）
2. 各ファイルをサブエージェントに割り当て
3. 結果を統合
```

**サブエージェント（50個）：**
```
各自:
- 1ファイルだけを読む
- リファクタリング
- 変更点を要約（500トークン）
```

**結果：**
- メインのContextは軽量維持
- 並列処理で高速化

</div>

---

## 💡 実践：明日から使える設計指針

---

## ✅ チェックリスト：Context 設計

<div class="box">

### System Prompts
- [ ] セクションで構造化されているか？
- [ ] 具体的な行動指針があるか？
- [ ] 矛盾がないか？

### Tools
- [ ] 機能が重複していないか？
- [ ] 説明は簡潔か（50トークン以内）？
- [ ] 使用目的が明確か？

### Examples
- [ ] 多様性があるか？
- [ ] 数は5-10個に絞れているか？
- [ ] 説明が添えられているか？

</div>

---

## ✅ チェックリスト：取得戦略

<div class="box">

### Just-in-Time
- [ ] 全データを最初から読んでいないか？
- [ ] インデックスだけ保持しているか？
- [ ] 必要な時に読み込む仕組みがあるか？

### Hybrid
- [ ] よく使うデータを識別できているか？
- [ ] 頻度とサイズで判断しているか？
- [ ] 無駄な事前読み込みがないか？

</div>

---

## ✅ チェックリスト：圧縮技術

<div class="box">

### Compaction
- [ ] Context上限の80%で圧縮しているか？
- [ ] 重要な決定を保持しているか？
- [ ] 冗長な出力を削除しているか？

### Note-Taking
- [ ] 長期的な情報を外部保存しているか？
- [ ] 構造化されているか？
- [ ] いつでもアクセスできるか？

### Sub-Agent
- [ ] タスクを分割できているか？
- [ ] 各Agentが軽量なContextか？
- [ ] 要約を返しているか？

</div>

---

## 📊 効果の実測値

<div class="box">

### Claude Code の事例

**改善前：**
- Context: 常に50,000トークン
- 精度: 70%
- レスポンス: 5秒

**改善後（Context Engineering適用）：**
- Context: 平均10,000トークン
- 精度: 95%
- レスポンス: 2秒

**改善率：**
- Context: 80%削減
- 精度: 25%向上
- 速度: 2.5倍高速化

</div>

---

## 🎯 まとめ：3つの重要原則

<div class="box" style="font-size: 24px;">

### 1. 最小限の高品質トークン

「量より質」
- 必要な情報だけ
- 冗長性を排除

### 2. 必要な時に取得

「全部読まない」
- インデックスで管理
- 使う時に読む

### 3. 構造化と圧縮

「整理して保存」
- 重要な情報を保持
- 不要な情報を削除

</div>

---

## 🚀 次のステップ

<div class="box">

### すぐにできること

1. **自分のプロンプトを見直す**
   - 無駄な情報がないか？
   - 構造化できるか？

2. **会話履歴を定期的に整理**
   - 重要な部分だけ残す
   - 要約を作る

3. **ツールを厳選する**
   - 使わないツールを削除
   - 説明を簡潔にする

</div>

---

## 📚 参考資料

<div class="box">

### 公式ドキュメント
- Anthropic Blog: Context Engineering
- Transformer論文: Attention is All You Need

### 実装例
- Claude Code: GitHub
- LangChain: メモリ管理

### コミュニティ
- Discord: AI Developers
- Reddit: r/MachineLearning

</div>

---

<!-- _class: lead -->

# 🙏 ありがとうございました！

**「最小限の高品質トークンで<br>最大の成果を」**

質問は Discord / Twitter でどうぞ

---

## 📎 補足：用語集

<div class="box">

**Context:** AIが参照する情報全体

**Token:** テキストの最小単位（1単語≒1-2トークン）

**Attention:** AIがどの情報に注目するか

**Transformer:** 現代のAIの基礎技術

**Prompt:** AIへの指示文

**Agent:** 自律的に行動するAI

</div>
