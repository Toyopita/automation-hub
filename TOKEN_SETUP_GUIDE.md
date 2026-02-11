# LINE Bot & Discord Bot トークン取得ガイド

新しい人用のLINE Botを立てるたびに必要な手順。

---

## 1. LINE Messaging API チャネル作成

### 1-1. LINE Developersにログイン
- URL: https://developers.line.biz/
- LINEアカウントでログイン

### 1-2. Providerを選択（または新規作成）
- 既存のProvider（例: 「Minami」）を選択
- なければ「Create」で新規作成

### 1-3. 新しいチャネルを作成
1. 「Create a new channel」をクリック
2. **「Messaging API」を選択**（⚠️ LINE Loginではない）
3. 必要事項を入力:
   - Channel name: Bot名（例: 「Toyo2」「ChatBot」等、相手に見える名前）
   - Channel description: 適当でOK
   - Category: 適当（「個人」等）
   - Subcategory: 適当
4. 利用規約に同意して「Create」

### 1-4. Channel Secret を取得
1. 作成したチャネルを開く
2. **「Basic settings」** タブ
3. 「Channel secret」の値をコピー
   - 例: `df7676ab54512036d5a7b894f83d0aea`
   - 32文字の英数字

### 1-5. Channel Access Token を取得
1. **「Messaging API」** タブ（⚠️ Basic settingsではない）
2. 一番下までスクロール
3. 「Channel access token (long-lived)」セクション
4. **「Issue」** ボタンをクリック
5. 表示されたトークンをコピー
   - 例: `TwNzmbmIBp7zUO4NB0Doz...（長い文字列）`

### 1-6. Webhook設定（Bot起動後に行う）
1. 「Messaging API」タブ
2. 「Webhook URL」にCloudflare TunnelのURLを設定
   - 例: `https://xxxx.trycloudflare.com/callback`
3. 「Use webhook」をONにする
4. 「Auto-reply messages」→ **Disabled**（自動応答はClaude側で行うため）
5. 「Greeting messages」→ 必要に応じてON/OFF

### 1-7. 友だち追加用QRコード
1. 「Messaging API」タブ
2. 「QR code」セクションにQRコードがある
3. これを相手に送って友だち追加してもらう
4. Bot ID（@xxx）も同じセクションにある

---

## 2. Discord Bot Application 作成

### 2-1. Discord Developer Portalにログイン
- URL: https://discord.com/developers/applications
- Discordアカウントでログイン

### 2-2. 新しいApplicationを作成
1. 右上「New Application」をクリック
2. 名前を入力（例: 「Aljela Bot」）
3. 「Create」

### 2-3. Bot Token を取得
1. 左メニュー → **「Bot」**
2. 「TOKEN」セクション → **「Reset Token」** をクリック
3. 表示されたトークンをコピー
   - 例: `MTQ3MTAwMTc1NTIwMTU3Mjk3Nw.GhU0f3.CvJozje...`
   - ⚠️ 一度しか表示されない。なくしたらReset Tokenで再発行

### 2-4. Intentsを有効化（重要）
1. 同じ「Bot」ページ
2. 「Privileged Gateway Intents」セクション
3. 以下をONにする:
   - **MESSAGE CONTENT INTENT** ✅（必須）
   - **SERVER MEMBERS INTENT** → 不要
   - **PRESENCE INTENT** → 不要
4. 「Save Changes」

### 2-5. Application ID（Client ID）を確認
1. 左メニュー → **「General Information」**
2. 「APPLICATION ID」をコピー
   - 例: `1471001755201572977`
   - 招待URL作成に使う

### 2-6. Botをサーバーに招待
以下のURLのCLIENT_IDを置き換えてブラウザで開く:
```
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=2048&scope=bot
```
- `2048` = メッセージ送信権限
- Minamiサーバーを選択して「認証」

---

## 3. .env への追加

```bash
# ===== [人名] LINE Bot =====
DISCORD_TOKEN_[NAME]=[Discord Bot Token]
[NAME]_DISCORD_CHANNEL_ID=[Discord Channel ID]
LINE_[NAME]_CHANNEL_SECRET=[LINE Channel Secret]
LINE_[NAME]_ACCESS_TOKEN=[LINE Channel Access Token]
```

### 例（Aljela）:
```bash
# ===== Aljela LINE Bot =====
DISCORD_TOKEN_ALJELA=MTQ3MTAwMTc1NTIwMTU3Mjk3Nw.GhU0f3.xxxxx
ALJELA_DISCORD_CHANNEL_ID=1470995067492761712
LINE_ALJELA_CHANNEL_SECRET=df7676ab54512036d5a7b894f83d0aea
LINE_ALJELA_ACCESS_TOKEN=TwNzmbmIBp7zUO4NB0Dozuxxxxx
```

---

## 4. チェックリスト（新しい人を追加するたび）

- [ ] LINE Messaging APIチャネル作成
- [ ] Channel Secret 取得
- [ ] Channel Access Token 取得（Issueボタン）
- [ ] Discord Application 作成
- [ ] Bot Token 取得
- [ ] MESSAGE CONTENT INTENT を ON
- [ ] BotをMinamiサーバーに招待
- [ ] Discord にチャンネル作成（Claude Codeに頼める）
- [ ] .env にトークン4つ追加
- [ ] config.json 作成（Claude Codeに頼める）
- [ ] Cloudflare Tunnel 起動
- [ ] LINE Webhook URL 設定
- [ ] 起動テスト

---

## 5. よくあるトラブル

### Channel Access Token の「Issue」ボタンがない
- チャネルタイプが「LINE Login」になっている可能性
- 「Messaging API」タイプで作り直す

### Botがメッセージを受信しない
- Webhook URLが正しいか確認
- 「Use webhook」がONか確認
- Cloudflare Tunnelが起動しているか確認

### Discord Botがオフライン
- Tokenが正しいか確認（Reset Tokenで再発行）
- MESSAGE CONTENT INTENTがONか確認

### LINE 月200通制限
- Push API（Bot→ユーザー）のみカウント
- Webhook受信（ユーザー→Bot）は無制限
- 超過する場合はライトプラン（月5,000円/5,000通）に変更

---

最終更新: 2026-02-11
