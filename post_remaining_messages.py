import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 残りの投稿内容（messages[1]〜[4]）
messages = [
    """## 3. 基本的な使い方

### ステップ1：起動
```bash
claude
```

### ステップ2：普通に話しかける
```
あなた: 「現在のディレクトリにあるPythonファイルを全部教えて」
Claude: 「探しています...」
→ 結果を表示
```

### ステップ3：確認しながら作業
```
あなた: 「main.pyを修正してバグを直して」
Claude: 「以下の修正を行います：[計画を表示] よろしいですか？(y/n)」
あなた: 「y」
Claude: 「修正しました！」
```

---

## 4. 仕事での実践的な活用例

### 🎯 ケース1：毎日の定型作業
**Before（手作業）：**
1. ログファイルを開く（5分）
2. エラーを探す（10分）
3. Excelにまとめる（15分）
**合計：30分**

**After（Claude Code）：**
```
「今日のエラーログを分析してCSVで出力して」
```
**合計：2分**

### 🎯 ケース2：トラブルシューティング
**シナリオ：** 「サーバーが動かない！」

**Before：**
1. Google検索（10分）
2. Stack Overflowを読む（20分）
3. 試行錯誤（30分）

**After：**
```
「このエラーメッセージの原因を調べて解決策を提案して」
→ コードを分析して具体的な修正案を提示
```

### 🎯 ケース3：ドキュメント作成
```
「このプロジェクトのREADME.mdを作成して。
セットアップ手順とAPI仕様を含めて」

→ コードを読んで自動でドキュメント生成
```""",

    """## 5. 初心者が知っておくべき重要ポイント

### ✅ DO（推奨）

**1. 必ず確認を取る文化**
- Claude は勝手に実行しません
- 「y」と答えるまで待ちます
- 不安なら「n」で断ってOK

**2. 具体的に指示する**
```
❌ 悪い例：「ファイルを修正して」
✅ 良い例：「config.jsonのポート番号を8080に変更して」
```

**3. 段階的に進める**
```
ステップ1: 「まず現状を調査して」
ステップ2: 「じゃあこの部分を修正して」
ステップ3: 「テストして動作確認して」
```

### ❌ DON'T（注意）

**1. 重要ファイルは事前にバックアップ**
```bash
# 作業前にバックアップを取る習慣
cp important.conf important.conf.backup
```

**2. 本番環境での実験は避ける**
- まずテスト環境で試す
- 動作確認してから本番適用

**3. パスワードや機密情報は渡さない**
- APIキーは環境変数で管理
- `.env`ファイルは`.gitignore`に追加""",

    """## 6. 便利な連携機能

### 🔗 他のAIとの使い分け（AI三銃士）

| AI | 得意分野 | 使い分け例 |
|----|---------|-----------|
| **Claude** | ファイル操作、コード作成、複雑な分析 | 「このバグを修正して」 |
| **Gemini** | Web検索、最新情報 | 「2025年の最新技術トレンドは？」 |
| **Codex** | コード生成に特化 | 「APIのCRUD操作を実装して」 |

```bash
# 使い方
ask_gemini "最新のReact 19の機能について"
ask_codex "React 19でコンポーネントを書いて"
```

---

## 7. よくある質問（FAQ）

**Q: 間違った指示をしたらどうなる？**
A: 実行前に確認が入るので、「n」で止められます。

**Q: ファイルを壊したら？**
A: バックアップから復元できます。重要な作業前はバックアップを！

**Q: 無料で使える？**
A: Claude Code CLIの使用にはAnthropicのAPIキーが必要です（有料）。

**Q: プログラミング知識がなくても使える？**
A: 基本的なターミナル操作ができれば使えます。日本語で話しかけるだけ。

**Q: どんな言語に対応してる？**
A: Python, JavaScript, TypeScript, Go, Rust, Java など主要言語全て。""",

    """## 8. 実践：最初の一歩

### 初心者向け練習タスク

**Level 1: 情報収集**
```
「このディレクトリの構造を教えて」
「README.mdを読んで要約して」
```

**Level 2: 簡単な作成**
```
「Hello Worldを表示するPythonスクリプトを作って」
「今日の日付をファイル名にしたテキストファイルを作って」
```

**Level 3: ファイル操作**
```
「config.jsonのタイムアウト値を30秒に変更して」
「全てのログファイルを一つにまとめて」
```

**Level 4: 自動化**
```
「毎日のバックアップスクリプトを作って」
「エラーログを監視して異常があれば通知して」
```

---

## まとめ：Claude Code CLIの本質

**従来の開発：**
人間 → 調べる → 考える → コード書く → テスト → デバッグ

**Claude Codeを使った開発：**
人間 → Claudeに指示 → Claude が調査・実装・テスト → 人間が確認

**時間短縮：** 70-80%
**エラー削減：** 大幅に減少
**学習効果：** Claudeの提案から学べる

---

📝 この説明資料は Claude Code CLI (claude-sonnet-4-5-20250929) によって作成されました。"""
]

@client.event
async def on_ready():
    print('=== Discord Bot Connected ===')
    print(f'Bot User: {client.user}\n')

    try:
        # 既存のスレッドを取得
        thread = await client.fetch_channel(1432626305819738135)
        print(f'Thread: {thread.name}')
        print(f'Thread ID: {thread.id}\n')

        # 残りのメッセージを投稿
        for i, msg in enumerate(messages, start=2):
            await asyncio.sleep(1.5)  # レート制限対策
            await thread.send(msg)
            print(f'✅ Message {i}/{len(messages)+1} sent')

        print('\n🎉 All messages posted successfully!')
        print(f'Thread URL: https://discord.com/channels/1430359607905222658/{thread.id}')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

    finally:
        await client.close()

asyncio.run(client.start(TOKEN))
