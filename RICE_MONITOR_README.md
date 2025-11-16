# 献米自動化システム - セットアップガイド

Discord → MacBook → Notion の献米情報自動登録システム

---

## ✅ 完了した作業

1. **GASロジックのPython移植** (`rice_monitor.py`)
2. **Discord Bot監視機能**（フォーラム「献米」を監視）
3. **Notion API連携**（献米記録DBに自動登録）
4. **launchd自動起動設定**（MacBook起動時に自動起動）

---

## 📋 セットアップ手順

### 1. Notion統合トークンの取得と設定

#### ① Notion統合トークンを取得
1. https://www.notion.so/my-integrations にアクセス
2. 「新しい統合」をクリック
3. 名前を「献米Bot」などに設定
4. 「送信」をクリック
5. **Internal Integration Token** をコピー（`secret_` で始まる文字列）

#### ② .envファイルに設定
```bash
cd ~/discord-mcp-server
nano .env
```

以下の行を編集：
```env
NOTION_TOKEN=your_notion_integration_token_here
```

↓ 取得したトークンに置き換える

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

保存して終了（Ctrl+X → Y → Enter）

#### ③ 献米記録DBに統合を接続
1. Notionで「献米記録」データベースを開く
2. 右上の「...」→「接続を追加」
3. 作成した統合（「献米Bot」など）を選択
4. 「確認」をクリック

---

### 2. 自動起動サービスの有効化

```bash
# plistファイルをlaunchdに登録
launchctl load ~/Library/LaunchAgents/com.user.rice-monitor.plist

# サービス起動確認
launchctl list | grep rice-monitor
```

**期待される出力:**
```
12345   0   com.user.rice-monitor
```

---

### 3. 手動起動でテスト（推奨）

自動起動の前に、まず手動でテストすることを推奨します：

```bash
cd ~/discord-mcp-server
source .venv/bin/activate
python3 rice_monitor.py
```

**期待されるログ:**
```
[献米][INFO] 2025-11-01T... - 献米監視Bot起動中...
[献米][INFO] 2025-11-01T... - Bot起動: claude_code#3214
[献米][INFO] 2025-11-01T... - 献米フォーラム監視開始: 1434019588609277952
```

---

## 🧪 テスト方法

### 1. Discordフォーラムに投稿

Discordの「献米」フォーラムに以下のようなメッセージを投稿：

```
2025年11月、本部
白30、600
黒、20、400
モチ 10 200
```

### 2. Botの反応を確認

- メッセージに ✅ リアクションが付く
- Botから「✅ 献米登録完了: 3/3件」のような返信が来る

### 3. Notionデータベースを確認

献米記録DBに以下のようなエントリが追加されているか確認：

| 商品名 | 数量 | キロ数 | 奉納年 | 奉納月 | 分類 |
|--------|------|--------|--------|--------|------|
| 白     | 30   | 600    | 2025   | 11     | 本部 |
| 黒     | 20   | 400    | 2025   | 11     | 本部 |
| モチ   | 10   | 200    | 2025   | 11     | 本部 |

---

## 📝 対応する献米メッセージフォーマット

### カンマ区切り形式（推奨）
```
2025年1月、祖霊社
白30、600
黒、20、400
モチ 10 200
```

### スペース区切り形式
```
2025年1月、本部
白 30 600
黒 20 400
```

### 単位付き形式
```
2025年1月、本部
白 30袋 600kg
黒 20袋 400kg
```

### キロ数なし
```
2025年1月、本部
白30
黒、20
```

**対応する米の種類:** 白、黒、モチ、その他

---

## 🛠️ トラブルシューティング

### Bot が起動しない場合

```bash
# ログを確認
tail -f ~/discord-mcp-server/rice_monitor.log
tail -f ~/discord-mcp-server/rice_monitor_error.log
```

### Notion登録エラーの場合

```bash
# .envファイルのNOTION_TOKENを確認
cat ~/discord-mcp-server/.env | grep NOTION_TOKEN

# Notion統合が献米記録DBに接続されているか確認
```

### サービスを再起動する場合

```bash
# サービスを停止
launchctl unload ~/Library/LaunchAgents/com.user.rice-monitor.plist

# サービスを再起動
launchctl load ~/Library/LaunchAgents/com.user.rice-monitor.plist
```

---

## 🔧 システム構成

| コンポーネント | 詳細 |
|----------------|------|
| **Discord** | フォーラム「献米」(ID: 1434019588609277952) |
| **Bot** | claude_code (Discord Bot) |
| **監視プログラム** | `~/discord-mcp-server/rice_monitor.py` |
| **Notion DB** | 献米記録 (ID: 28000160-1818-80a1-94e3-f87262777dec) |
| **自動起動** | launchd (com.user.rice-monitor) |

---

## 📌 重要な注意事項

1. **NOTION_TOKENは絶対に公開しないこと**
2. **.envファイルはgitにコミットしないこと**（.gitignoreに含まれています）
3. **MacBookがスリープ中はBotが動作しません**
4. **インターネット接続が必要です**

---

## 📚 参考リンク

- Notion API: https://developers.notion.com/
- Discord Bot設定: https://discord.com/developers/applications
- launchd入門: `man launchd.plist`

---

作成日: 2025-11-01
