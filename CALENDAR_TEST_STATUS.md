# 📅 カレンダー自動登録テスト状況

## ⏸️ 現在のステータス: テスト保留中

**最終更新**: 2025-11-17 16:08

## 📊 実装済み機能

### ✅ 完了している部分
1. **Discord Bot起動** - expo_reaction_calendar.py が正常に動作
2. **リアクション検知** - 📅リアクションを正しく検知
3. **フォーラム判定** - 🎡大阪関西万博、🎪イベント両方に対応
4. **メッセージ取得** - スレッドの最初のメッセージとURLを取得
5. **Google Calendar API認証** - サービスアカウント設定完了

### 監視対象フォーラム
- 🎡｜大阪関西万博（IZUMOサーバー）: `1439846883504689193`
- 🎪イベント（Minamiサーバー）: `1434499089420128317`

### Google Calendar
- カレンダー名: 関西イベント情報
- カレンダーID: `ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com`
- サービスアカウント: `discord-expo-calendar@ninth-incentive-463505-h9.iam.gserviceaccount.com`

## ⚠️ 現在の問題

### Gemini API レート制限エラー (429)
- **症状**: 📅リアクションを付けると自動的に消えて❌が付く
- **原因**: Gemini APIのレート制限（複数回のテストで制限に到達）
- **影響**: イベント情報抽出ができず、カレンダー登録まで到達しない

### ログ出力例
```
📅 リアクション検知: メッセージID 1439864116436144270
メッセージ取得: 大阪・関西万博開催記念 古墳サミット開催！
URL: https://news.google.com/rss/articles/...
記事タイトル: 大阪・関西万博開催記念 古墳サミット開催！
Gemini APIでイベント情報を抽出中...
Gemini APIエラー: 429
ℹ️  イベント情報が見つかりませんでした
```

### 現在の動作
- 📅リアクション検知 → Gemini API呼び出し
- 429エラー → `has_event: false`と判定
- 📅リアクションを削除 + ❌リアクションを追加

## 🔧 改善案（未実装）

### オプション1: エラー時の挙動変更
- 429エラー時は📅を削除せず⏰リアクションを付ける
- ユーザーに「後で再試行してください」を伝える

### オプション2: リトライロジック
- 30秒後に自動リトライ（最大3回）
- 指数バックオフ（30秒 → 60秒 → 120秒）

### オプション3: キューイングシステム
- 429エラー時は処理をキューに保存
- 1時間後に自動的に再実行

## 📝 次回テスト時の手順

1. **レート制限リセット待ち** - 前回テストから1時間以上経過していることを確認
2. **処理済み履歴クリア** - `expo_calendar_processed.json`を削除またはリセット
3. **📅リアクションを付ける** - イベント記事のスレッドに付ける
4. **ログ確認** - 以下を確認:
   - ✅ イベント検出: {イベント名}
   - ✅ カレンダー登録成功
   - イベントURL表示

## 🗂️ 関連ファイル

- **Botスクリプト**: `/Users/minamitakeshi/discord-mcp-server/expo_reaction_calendar.py`
- **認証情報**: `/Users/minamitakeshi/discord-mcp-server/google-calendar-service-account.json`
- **処理済み履歴**: `/Users/minamitakeshi/discord-mcp-server/expo_calendar_processed.json`
- **起動設定**: `/Users/minamitakeshi/Library/LaunchAgents/com.discord.expo_reaction_calendar.plist`
- **ログファイル**: `/Users/minamitakeshi/discord-mcp-server/expo_reaction_calendar.log`
- **ログ履歴**: `/Users/minamitakeshi/discord-mcp-server/logs/calendar_test_history/`

## 🔄 Bot起動状態

launchdで自動起動・常駐監視中：
```bash
launchctl list | grep expo_reaction_calendar
```

手動再起動が必要な場合：
```bash
launchctl unload ~/Library/LaunchAgents/com.discord.expo_reaction_calendar.plist
launchctl load ~/Library/LaunchAgents/com.discord.expo_reaction_calendar.plist
```

---

**保留理由**: Gemini API レート制限のため、時間を置いてから再テスト予定
