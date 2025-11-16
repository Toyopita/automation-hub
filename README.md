# Discord MCP Server

**Python + FastAPI + discord.py** による **MCP プロトコル完全準拠** Discord サーバー

## 機能

- ✅ MCP プロトコル完全準拠
- ✅ Discord チャンネルへのメッセージ送信
- ✅ Discord チャンネルからのメッセージ取得
- ✅ Claude Desktop 連携対応

## セットアップ

### 1. 必要なパッケージをインストール

```bash
cd ~/discord-mcp-server
pip install -r requirements.txt
```

または仮想環境を使用する場合：

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリック
3. 「Bot」タブから Bot を作成
4. **Bot Token** をコピー
5. 「Privileged Gateway Intents」で以下を有効化：
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT
6. 「OAuth2」→「URL Generator」で以下を選択：
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Read Message History`
7. 生成された URL でサーバーに Bot を招待

### 3. 環境変数の設定

`.env` ファイルに Bot Token を設定：

```env
DISCORD_BOT_TOKEN=あなたのボットトークン
PORT=8000
```

### 4. サーバー起動

```bash
python main.py
```

起動成功すると以下のように表示されます：

```
Discord Bot logged in as YourBot#1234
INFO:     Uvicorn running on http://127.0.0.1:8000
```

## Claude Desktop との連携

### Claude Desktop の設定

`~/Library/Application Support/Claude/claude_desktop_config.json` に以下を追加：

```json
{
  "mcpServers": {
    "discord": {
      "url": "http://127.0.0.1:8000"
    }
  }
}
```

### 使用例

Claude に以下のように指示：

```
Discordの #general チャンネル (ID: 123456789) に「テストメッセージ」を送信して
```

```
Discordの #general チャンネル (ID: 123456789) の最新10件のメッセージを取得して
```

## API エンドポイント

### ツール一覧取得

```bash
GET http://127.0.0.1:8000/tools
```

### メッセージ送信

```bash
POST http://127.0.0.1:8000/tools/discord_send_message
Content-Type: application/json

{
  "channel_id": "123456789",
  "content": "Hello from MCP!"
}
```

### メッセージ取得

```bash
POST http://127.0.0.1:8000/tools/discord_read_messages
Content-Type: application/json

{
  "channel_id": "123456789",
  "limit": 10
}
```

## トラブルシューティング

### Bot が起動しない

- `.env` ファイルに `DISCORD_BOT_TOKEN` が正しく設定されているか確認
- Bot Token が有効か確認（Discord Developer Portal で再生成可能）

### チャンネルが見つからない

- Bot がサーバーに招待されているか確認
- Bot に適切な権限があるか確認
- チャンネル ID が正しいか確認（Discord で開発者モードを有効化して右クリック→「IDをコピー」）

### Claude Desktop で認識されない

- `claude_desktop_config.json` のパスが正しいか確認
- Claude Desktop を再起動
- サーバーが起動しているか確認 (`http://127.0.0.1:8000` にアクセス)

## ファイル構成

```
discord-mcp-server/
├── .venv/              # Python仮想環境
├── .env                # 環境変数（Gitには含まれない）
├── .env.template       # 環境変数のテンプレート
├── .gitignore          # Git除外設定
├── main.py             # MCPサーバーのメインファイル
├── requirements.txt    # 必要なパッケージ
└── README.md           # このファイル
```

## ライセンス

MIT
