# 献品自動化システム - 完全ガイド

Discord → MacBook → Notion の献品情報自動登録システム

---

## 📦 システム構成

本システムは以下の2つの独立したBotで構成されています：

### 1. 献米自動化Bot
- **監視チャンネル**: #🌾｜献米（献品カテゴリ）
- **登録先**: Notion「献米記録」データベース
- **プログラム**: `rice_monitor.py`
- **自動起動**: `com.user.rice-monitor.plist`

### 2. 献酒自動化Bot
- **監視チャンネル**: #🍶｜献酒（献品カテゴリ）
- **登録先**: Notion「献酒記録」データベース
- **プログラム**: `sake_monitor.py`
- **自動起動**: `com.user.sake-monitor.plist`

---

## ✅ 完了した作業

### 献米システム
1. ✅ GASの献米解析ロジックをPythonに移植
2. ✅ Discord「#🌾｜献米」チャンネル監視機能
3. ✅ Notion「献米記録」DBへの自動登録
4. ✅ MacBook起動時の自動起動設定
5. ✅ 動作確認済み

### 献酒システム
1. ✅ GASの献酒解析ロジックをPythonに移植
2. ✅ Discord「#🍶｜献酒」チャンネル監視機能
3. ✅ Notion「献酒記録」DBへの自動登録
4. ✅ MacBook起動時の自動起動設定
5. ✅ 動作確認済み

---

## 🎯 使い方

### 献米の登録

Discordの「#🌾｜献米」チャンネルに以下の形式で投稿：

```
2025年11月、本部
白30、600
黒20、400
モチ 10 200
```

**対応する米の種類:**
- 白
- 黒
- モチ
- その他

**登録される情報:**
- 奉納年、奉納月、分類（本部/祖霊社）
- 商品名、数量、キロ数

---

### 献酒の登録

Discordの「#🍶｜献酒」チャンネルに以下の形式で投稿：

```
2025年11月、本部
賀茂鶴1000
上撰2000
飛翔3000
```

**対応する酒の種類:**
- 賀茂鶴
- 樽酒
- 上撰
- 飛翔
- 典雅
- その他

**登録される情報:**
- 奉納年、奉納月、分類（本部/祖霊社）
- 商品名、数量

---

## 🔧 システム管理

### サービスの状態確認

```bash
# 献米Bot
launchctl list | grep rice-monitor

# 献酒Bot
launchctl list | grep sake-monitor
```

### サービスの停止

```bash
# 献米Bot
launchctl unload ~/Library/LaunchAgents/com.user.rice-monitor.plist

# 献酒Bot
launchctl unload ~/Library/LaunchAgents/com.user.sake-monitor.plist
```

### サービスの再起動

```bash
# 献米Bot
launchctl load ~/Library/LaunchAgents/com.user.rice-monitor.plist

# 献酒Bot
launchctl load ~/Library/LaunchAgents/com.user.sake-monitor.plist
```

### ログの確認

```bash
# 献米Bot
tail -f ~/discord-mcp-server/rice_monitor.log
tail -f ~/discord-mcp-server/rice_monitor_error.log

# 献酒Bot
tail -f ~/discord-mcp-server/sake_monitor.log
tail -f ~/discord-mcp-server/sake_monitor_error.log
```

---

## 📁 ファイル構成

```
~/discord-mcp-server/
├── rice_monitor.py              # 献米監視プログラム
├── sake_monitor.py              # 献酒監視プログラム
├── .env                         # 環境変数（トークン設定）
├── rice_monitor.log             # 献米Botログ
├── rice_monitor_error.log       # 献米Botエラーログ
├── sake_monitor.log             # 献酒Botログ
├── sake_monitor_error.log       # 献酒Botエラーログ
└── 献品自動化システム_README.md  # このファイル

~/Library/LaunchAgents/
├── com.user.rice-monitor.plist  # 献米Bot自動起動設定
└── com.user.sake-monitor.plist  # 献酒Bot自動起動設定
```

---

## 🔐 セキュリティ

### 環境変数（`.env`ファイル）

以下の情報は`.env`ファイルで管理されています：
- Discord Botトークン
- Notion統合トークン

**重要:**
- `.env`ファイルは絶対に公開・共有しないこと
- gitにコミットしないこと（`.gitignore`で除外済み）
- トークンが漏洩した場合は直ちに再発行すること

---

## 🚨 トラブルシューティング

### Botが起動しない

```bash
# ログを確認
tail -50 ~/discord-mcp-server/rice_monitor_error.log
tail -50 ~/discord-mcp-server/sake_monitor_error.log
```

### Notion登録エラー

- Notion統合トークンが正しく設定されているか確認
- NotionデータベースにBotの統合が接続されているか確認

### メッセージに反応しない

- Botが起動しているか確認（`launchctl list`）
- 正しいチャンネルに投稿しているか確認
- メッセージフォーマットが正しいか確認

---

## 📊 システム仕様

### 献米チャンネル
- ID: 1434159642912751696
- カテゴリ: ━━━ 献品 ━━━

### 献酒チャンネル
- ID: 1430362136726605876
- カテゴリ: ━━━ 献品 ━━━

### 処理フロー
1. Discordチャンネルでメッセージ投稿
2. Bot自動検知
3. メッセージ解析（年月・分類・商品名・数量）
4. Notion APIで自動登録
5. ✅リアクション + 完了メッセージ返信

---

## 📝 移行履歴

**旧システム:** Slack → GAS → Notion
**新システム:** Discord → MacBook → Notion

**移行日:** 2025年11月1日

**移行理由:**
- Slackの利用終了
- Discordへの一元化
- MacBookローカルでの完全自動化

---

## 🎉 システムの利点

1. **完全自動化** - MacBook起動時に自動でBot起動
2. **リアルタイム処理** - 投稿後数秒でNotion登録
3. **エラー通知** - 解析失敗時は❓リアクションで通知
4. **独立動作** - 献米と献酒は別プログラムで安定動作
5. **ログ保存** - 全ての処理履歴をログファイルに記録

---

作成日: 2025年11月1日
最終更新: 2025年11月1日
