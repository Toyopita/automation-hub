# SwitchBot 自動化システム

SwitchBot APIを使用したスマートホーム自動化スクリプト群。

最終更新: 2026-02-03

---

## 概要

| カテゴリ | スクリプト | 実行方式 | 説明 |
|---------|-----------|---------|------|
| エアコン制御 | `switchbot_aircon_comfort.py` | launchd (15分毎) | 温度差ベースの自動制御 |
| エアコン制御 | `switchbot_aircon_control.py` | **停止済** | 不快指数ベース（旧版） |
| 電池監視 | `battery_monitor.py` | launchd (毎日8:00) | デバイス電池残量監視 |
| 夜間照明 | `night_light_off.py` | launchd (毎日21:00) | リビング電気自動OFF |
| 祖霊社音響 | `music_play.py` | 手動/スラッシュコマンド | 音楽再生 |
| 祖霊社音響 | `music_stop.py` | 手動/スラッシュコマンド | 音楽停止 |
| 祖霊社照明 | `music_light_on.py` | 手動/スラッシュコマンド | 照明点灯 |
| 祖霊社照明 | `music_light_off.py` | 手動/スラッシュコマンド | 照明消灯 |

---

## 1. エアコン自動制御システム

### 1.1 現行システム: `switchbot_aircon_comfort.py`

温度差ベースの自動制御。15分ごとに実行。

#### 使用デバイス

| デバイス | デバイスID | 用途 |
|---------|-----------|------|
| エアコン | `02-202404131311-10141115` | 冷暖房制御 |
| CO2センサー（室内） | `B0E9FE561980` | 室内温湿度・CO2計測 |
| 防水温湿度計（室外） | `D0C84206187C` | 外気温計測 |
| 加湿器 | `D48C49559C0A` | 湿度制御 |

#### 制御ロジック

##### 冬季（11月〜2月）

**夜間モード（21:00〜5:00、外気温≤8℃）**
| 室内温度 | 動作 |
|---------|------|
| < 25℃ | 暖房ON（26℃設定）|
| ≥ 25℃ | 暖房OFF |

**通常モード**
| 室内温度 | 動作 |
|---------|------|
| < 24℃ | 暖房ON（26℃設定）|
| ≥ 26℃ | 暖房不要 |
| 24〜26℃ | 現状維持 |

**加湿器制御**
| 湿度 | 動作 |
|-----|------|
| < 60% | 加湿器ON |
| ≥ 65% | 加湿器OFF |
| 60〜65% | 現状維持 |

**加湿器夜間モード（22:00〜7:00）**
- 自動的に「おやすみモード」に設定

##### 夏季（6月〜8月）

| 条件 | 動作 |
|-----|------|
| 室内 ≥ 28℃ | 冷房ON（29℃設定）|
| 室内 26〜28℃ かつ 温度差 < 5℃ | 冷房ON（29℃設定）|
| 室内 ≤ 26℃ または 温度差 ≥ 7℃ | 冷房不要 |

##### 緊急制御（全季節共通）

| 条件 | 動作 |
|-----|------|
| 室内 ≥ 32℃ | 緊急冷房ON |
| 室内 ≤ 15℃ | 緊急暖房ON |

##### CO2アラート

| CO2濃度 | 動作 |
|---------|------|
| ≥ 1000ppm | Discordに換気通知 |
| < 1000ppm | アラート解除 |

#### 状態管理

- `aircon_state.json`: 前回のエアコンモードを保存
- 状態変化時のみAPIコマンド送信（API呼び出し削減）

#### 記録・通知

| 出力先 | 内容 |
|-------|------|
| Notion | 制御ログをデータベースに記録 |
| macOS通知 | 制御実行時に通知 |
| Discord | エラー発生時に通知 |

#### launchd設定

- **plist**: `/Users/minamitakeshi/Library/LaunchAgents/com.switchbot.aircon_comfort.plist`
- **実行間隔**: 900秒（15分）
- **ログ**: `aircon_comfort.log`, `aircon_comfort_error.log`

---

### 1.2 旧システム: `switchbot_aircon_control.py`（停止済）

不快指数（DI）ベースの制御。**2026-02-03に停止**。

#### 停止理由

- `switchbot_aircon_comfort.py`に統合
- 2つのスクリプトが同時実行されると競合の可能性

#### 旧ロジック（参考）

- 夏季: 時間帯別DI閾値で冷房ON/OFF
- 冬季: 室温23℃未満で暖房ON（27℃設定）
- サーキュレーター制御あり（現行版にはなし）

---

## 2. 電池残量監視: `battery_monitor.py`

### 概要

SwitchBotデバイスの電池残量を毎日8:00にチェック。10%以下のデバイスがあればDiscord通知。

### 通知先

- **Discordチャンネル**: 📢｜お知らせ（ID: `1434340159389700156`）
- **macOS通知**: 電池残量警告

### launchd設定

- **plist**: `/Users/minamitakeshi/Library/LaunchAgents/com.switchbot.battery_monitor.plist`
- **実行時刻**: 毎日8:00
- **ログ**: `battery_monitor.log`, `battery_monitor_error.log`

---

## 3. 夜間照明OFF: `night_light_off.py`

### 概要

毎日21:00にリビング電気を自動OFFにする。

### 対象デバイス

| デバイス | デバイスID |
|---------|-----------|
| リビング電気 | `C76B03C65C33` |

### launchd設定

- **plist**: `/Users/minamitakeshi/Library/LaunchAgents/com.switchbot.night_light_off.plist`
- **実行時刻**: 毎日21:00
- **ログ**: `night_light_off.log`, `night_light_off_error.log`

---

## 4. 祖霊社 音響・照明制御

### 概要

SwitchBotシーン経由で祖霊社のディスクプレーヤーと照明を制御。
Claude Codeのスラッシュコマンドから実行可能。

### スクリプト一覧

| スクリプト | シーンID | 機能 | スラッシュコマンド |
|-----------|---------|------|------------------|
| `music_play.py` | `41e4f462-8d53-40c3-a535-c7945715ec3c` | 音楽再生 | `/再生` |
| `music_stop.py` | `a7f7434f-19d3-448b-ba96-734d29bb90a2` | 音楽停止 | `/停止` |
| `music_light_on.py` | `b8148402-f873-486b-b808-7c2df2735abb` | 照明点灯 | `/点灯` |
| `music_light_off.py` | `fb6fbf28-5933-4c52-85e1-0b7f99dc54d2` | 照明消灯 | `/消灯`, `/消して` |

### 実行方法

```bash
# 手動実行
python3 music_play.py
python3 music_stop.py
python3 music_light_on.py
python3 music_light_off.py
```

---

## 環境変数

すべてのスクリプトは`.env`ファイルから環境変数を読み込む。

| 変数名 | 説明 |
|-------|------|
| `SWITCHBOT_TOKEN` | SwitchBot API トークン |
| `DISCORD_TOKEN` | Discord Bot トークン |
| `NOTION_TOKEN` | Notion API トークン |
| `AIRCON_DEVICE_ID` | エアコンデバイスID |
| `CO2_METER_ID` | CO2センサーデバイスID |
| `OUTDOOR_SENSOR_ID` | 室外温湿度計デバイスID |
| `HUMIDIFIER_ID` | 加湿器デバイスID |
| `AIRCON_CONTROL_DISCORD_CHANNEL` | エアコン制御ログ用Discordチャンネル |
| `AIRCON_CONTROL_NOTION_DB` | エアコン制御ログ用Notion DB ID |

---

## launchd 管理コマンド

```bash
# 状態確認
launchctl list | grep switchbot

# 再読み込み
launchctl unload ~/Library/LaunchAgents/com.switchbot.aircon_comfort.plist
launchctl load ~/Library/LaunchAgents/com.switchbot.aircon_comfort.plist

# 即時実行（テスト）
cd ~/discord-mcp-server && .venv/bin/python3 switchbot_aircon_comfort.py
```

---

## Notion記録先

| 用途 | データベースID |
|-----|---------------|
| エアコン制御ログ | `2a800160-1818-814b-b27a-000b80e0ceb0` |

---

## トラブルシューティング

### エアコンが制御されない

1. launchdが動作しているか確認: `launchctl list | grep aircon`
2. ログ確認: `tail -50 aircon_comfort.log`
3. センサーデータ取得確認: 手動実行でエラーチェック

### Notion記録エラー

- Discordの🌡️｜エアコン制御ログチャンネルにエラー通知が届く
- Notion API トークンの有効期限を確認

### 電池アラートが届かない

1. launchdが動作しているか確認: `launchctl list | grep battery`
2. ログ確認: `tail -50 battery_monitor.log`

---

## 変更履歴

| 日付 | 変更内容 |
|-----|---------|
| 2026-02-03 | 冬季夜間モード追加（21時〜5時、外気温≤8℃で室温25℃キープ）|
| 2026-02-03 | `switchbot_aircon_control.py`（不快指数ベース）を停止、`switchbot_aircon_comfort.py`に統合 |
| 2026-01-23 | 冬季ロジック改善（温度差条件削除、絶対温度優先） |
