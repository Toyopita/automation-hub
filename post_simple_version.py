import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 簡潔版の内容
content = """# Claude Code CLI 超入門（簡潔版）

## ✨ Claude Code CLIとは？

**ターミナルで使える、ファイル操作・コード作成ができるAIアシスタント**
ChatGPTと違い、直接ファイルを読み書きしてコードを実行できます。

---

## 🎯 できること（ベスト3）

### 1. ファイル操作
```
「config.jsonのポート番号を8080に変更して」
「このエラーログを分析して」
```
→ ファイルを自動で読み書き・分析

### 2. コード作成・修正
```
「Pythonでファイル一覧スクリプトを作って」
「このバグを修正して」
```
→ コード生成から修正まで自動

### 3. タスク自動化
```
「全ファイルをバックアップして」
「テストを実行して結果を報告して」
```
→ コマンド実行から結果分析まで一貫対応

---

## 📖 基本の使い方

**1. 起動**
```bash
claude
```

**2. 話しかける**
```
「現在のディレクトリ構造を教えて」
```

**3. 確認して実行**
```
Claude: 「以下を実行します：[計画] よろしいですか？(y/n)」
あなた: 「y」
```

---

## 💡 実践例

### Before（手作業30分）
1. ログを開く（5分）
2. エラー検索（10分）
3. Excelにまとめ（15分）

### After（Claude 2分）
```
「今日のエラーログをCSVで出力して」
```

### トラブル時も即解決
```
「このエラーメッセージの原因と解決策を教えて」
→ コード分析して具体的な修正案を提示
```

---

## ⚠️ 重要な注意点

### ✅ DO
- **必ず確認する**: Claudeは勝手に実行しない。「y」で承認必須
- **具体的に指示**: ❌「修正して」 ✅「config.jsonのタイムアウトを30秒に変更」
- **段階的に進める**: 調査→修正→テストの順で指示

### ❌ DON'T
- **重要ファイルはバックアップ**: 作業前に必ずバックアップ
- **本番環境で実験しない**: テスト環境で動作確認してから本番適用
- **機密情報を渡さない**: パスワードやAPIキーは環境変数で管理

---

## 🚀 最初の一歩

### Level 1: 試してみよう
```
「このディレクトリの構造を教えて」
「README.mdを読んで要約して」
```

### Level 2: 作ってみよう
```
「Hello Worldスクリプトを作って」
「今日の日付のテキストファイルを作って」
```

### Level 3: 自動化しよう
```
「全ログファイルを1つにまとめて」
「バックアップスクリプトを作って」
```

---

## 📊 効果

**時間短縮**: 70-80%削減
**エラー**: 大幅に減少
**学習**: Claudeの提案から学べる

**開発の流れ:**
従来: 人間が調べる→考える→コード書く→テスト→デバッグ
Claude Code: 人間が指示→Claudeが実装→人間が確認

---

📝 Claude Code CLI (claude-sonnet-4-5-20250929) 作成"""

@client.event
async def on_ready():
    print('=== Discord Bot Connected ===')
    print(f'Bot User: {client.user}\n')

    try:
        # フォーラムチャンネルを取得
        forum_channel = await client.fetch_channel(1432625860917198928)
        print(f'Forum channel: {forum_channel.name}')

        if isinstance(forum_channel, discord.ForumChannel):
            # 新しいスレッドを作成
            thread_with_message = await forum_channel.create_thread(
                name="【超簡潔版】Claude Code CLI 超入門",
                content=content
            )

            thread = thread_with_message.thread

            print(f'✅ Thread created: {thread.name}')
            print(f'Thread ID: {thread.id}')
            print(f'\n🎉 Post completed successfully!')
            print(f'Thread URL: https://discord.com/channels/1430359607905222658/{thread.id}')
        else:
            print('❌ Not a forum channel')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

    finally:
        await client.close()

asyncio.run(client.start(TOKEN))
