# Discord チャンネル管理システム

## 概要

`channels.py` を使用することで、Discordのチャンネル・フォーラムIDをハードコードせずに、
名前で簡単にアクセスできます。

## ファイル構成

```
discord-mcp-server/
├── channels.py                    # 自動生成されたチャンネル定数ファイル
├── generate_channels_config.py    # channels.pyを生成するスクリプト
└── example_use_channels.py        # 使用例
```

## 基本的な使い方

### 1. channels.py の生成

チャンネル情報を最新の状態に更新します：

```bash
cd ~/discord-mcp-server
source .venv/bin/activate
python generate_channels_config.py
```

### 2. スクリプトでの使用

```python
from channels import CHANNELS, FORUMS, CATEGORIES

# テキストチャンネルIDを取得
rule_channel_id = CHANNELS["ルール"]

# フォーラムIDを取得
forum_id = FORUMS["朝刊太郎のチュートリアル"]

# カテゴリIDを取得
category_id = CATEGORIES["DX"]
```

### 3. 実際の使用例

```python
import asyncio
import discord
from channels import CHANNELS, FORUMS

async def post_to_channel():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        # ルールチャンネルにメッセージを投稿
        channel = await client.fetch_channel(CHANNELS["ルール"])
        await channel.send("こんにちは！")

        # フォーラムにスレッドを作成
        forum = await client.fetch_channel(FORUMS["朝刊太郎のチュートリアル"])
        await forum.create_thread(
            name="新しいスレッド",
            content="内容"
        )

        await client.close()

    await client.start(TOKEN)
```

## 利用可能な定数

### CHANNELS（テキストチャンネル）
- `CHANNELS["ルール"]` - ルールチャンネル
- `CHANNELS["お知らせ"]` - お知らせチャンネル
- `CHANNELS["システム通知"]` - システム通知チャンネル
- `CHANNELS["ひふみ"]` - ひふみチャンネル
- `CHANNELS["生成ai"]` - 生成AIチャンネル
- その他多数...

### FORUMS（フォーラムチャンネル）
- `FORUMS["朝刊太郎のチュートリアル"]` - 朝刊太郎のチュートリアルフォーラム
- `FORUMS["claudeとcodexの部屋"]` - ClaudeとCodexの部屋フォーラム
- `FORUMS["knowledge"]` - ナレッジフォーラム
- `FORUMS["連絡"]` - 連絡フォーラム

### CATEGORIES（カテゴリ）
- `CATEGORIES["DX"]` - DXカテゴリ
- `CATEGORIES["広報"]` - 広報カテゴリ
- `CATEGORIES["事務"]` - 事務カテゴリ
- その他多数...

## メンテナンス

### チャンネルの更新

新しいチャンネルが追加されたり、名前が変更された場合：

```bash
python generate_channels_config.py
```

これで `channels.py` が最新の状態に更新されます。

### 既存スクリプトの移行

既存のスクリプトでハードコードされたIDを使っている場合：

**Before:**
```python
FORUM_CHANNEL_ID = 1430855994761805874  # 朝刊太郎のチュートリアル
```

**After:**
```python
from channels import FORUMS
FORUM_CHANNEL_ID = FORUMS["朝刊太郎のチュートリアル"]
```

## 利点

1. **可読性**: IDではなく名前でチャンネルを指定できる
2. **保守性**: チャンネルIDが変更されても、再生成するだけでOK
3. **一元管理**: すべてのチャンネル情報が1ファイルに集約
4. **エラー防止**: タイポや古いIDの使用を防げる

## トラブルシューティング

### channels.pyが見つからない
```bash
python generate_channels_config.py
```
を実行して生成してください。

### チャンネルが見つからない
Discord側で新しいチャンネルが追加された場合、`channels.py` を再生成してください。

### インポートエラー
`channels.py` がスクリプトと同じディレクトリにあることを確認してください。

## 更新履歴

- 2025-10-29: 初版作成
