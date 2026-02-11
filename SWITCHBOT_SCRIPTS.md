# SwitchBot自動化スクリプト一覧

このディレクトリ内のSwitchBot関連スクリプトをまとめたインデックスです。

> **注意**: スクリプトの移動・リネームは禁止です。launchd設定が絶対パスで参照しています。

---

## 定期実行スクリプト

### 朝の自動化
| スクリプト | 実行時刻 | launchd設定 | 機能 |
|-----------|---------|-------------|------|
| `morning_automation.py` | 6:40 | `com.morning.automation.plist` | テレビON→10ch、リビング電気ON |
| `morning_automation.py --force` | 6:00 (1/1〜1/3) | `com.morning.newyear.plist` | 正月版（宿直・休日チェックなし） |

**スキップ条件（通常版のみ）:**
- 宿直カレンダーに予定あり
- 休日カレンダーに予定あり
- 正月期間（1/1〜1/3）

**依存スクリプト:** `check_shukuchoku.js`, `check_holiday.js`

---

### 夜間制御
| スクリプト | 実行時刻 | launchd設定 | 機能 |
|-----------|---------|-------------|------|
| `night_light_off.py` | 21:00 | `com.switchbot.night_light_off.plist` | リビング電気OFF（リトライ10回） |

---

### エアコン快適制御
| スクリプト | 実行間隔 | launchd設定 | 状態 |
|-----------|---------|-------------|------|
| `switchbot_aircon_comfort.py` | 15分毎 | `com.switchbot.aircon_comfort.plist` | **稼働中** |
| `switchbot_aircon_control.py` | 15分毎 | `com.switchbot.aircon_control.plist` | 停止中 |
| `auto_heating.py` | - | なし | 未使用 |

#### switchbot_aircon_comfort.py（現行版）
- **冬季**: 室内24℃未満 → 暖房ON（26℃）、室内26℃以上 → OFF
- **冬季夜間（21〜5時、外気8℃以下）**: 室内25℃未満 → 暖房ON
- **夏季**: 室内28℃以上 or 温度差5℃未満 → 冷房ON（29℃）
- **緊急**: 室内32℃以上 → 緊急冷房、室内15℃以下 → 緊急暖房
- **加湿器制御**: 冬季に湿度60%未満でON
- **記録**: Notion + Discord通知

#### switchbot_aircon_control.py（旧版・停止中）
- 不快指数ベースの季節別制御
- サーキュレーター制御あり

---

### バッテリー監視
| スクリプト | 実行時刻 | launchd設定 | 機能 |
|-----------|---------|-------------|------|
| `battery_monitor.py` | 8:00 | `com.switchbot.battery_monitor.plist` | 全デバイス電池残量チェック、10%以下で通知 |

---

## 手動実行スクリプト（祖霊社音響・照明）

| スクリプト | コマンド | 機能 |
|-----------|---------|------|
| `music_play.py` | 「再生」 | 祖霊社ディスクプレーヤーで音楽再生 |
| `music_stop.py` | 「停止」 | 音楽停止 |
| `music_light_on.py` | 「点灯」 | 祖霊社照明点灯 |
| `music_light_off.py` | 「消灯」「消して」 | 祖霊社照明消灯 |

**実装**: SwitchBotシーン経由で実行

---

## デバイスID一覧

| デバイス | ID | 用途 |
|---------|-----|------|
| テレビ | `02-202404131305-88391198` | 朝の自動化 |
| リビング電気 | `C76B03C65C33` | 朝・夜の照明制御 |
| エアコン | `02-202404131311-10141115` | 快適温度制御 |
| CO2センサー（室内） | `B0E9FE561980` | 室内温湿度取得 |
| 外気センサー（屋外） | `D0C84206187C` | 外気温度取得 |
| サーキュレーター | `3C84279DF0A6` | 旧版で使用 |
| 加湿器 | `D48C49559C0A` | 冬季湿度制御 |

---

## ログファイル

| スクリプト | 標準出力 | エラー出力 |
|-----------|---------|-----------|
| morning_automation.py | `morning_automation.log` | `morning_automation_error.log` |
| morning_automation.py --force | `morning_newyear.log` | `morning_newyear_error.log` |
| night_light_off.py | `night_light_off.log` | `night_light_off_error.log` |
| switchbot_aircon_comfort.py | `aircon_comfort.log` | `aircon_comfort_error.log` |
| switchbot_aircon_control.py | `aircon_control.log` | `aircon_control_error.log` |

---

## 確認コマンド

```bash
# launchd状態確認
launchctl list | grep -E "morning|switchbot"

# ログ確認
tail -f ~/discord-mcp-server/morning_automation.log
tail -f ~/discord-mcp-server/aircon_comfort.log
tail -f ~/discord-mcp-server/night_light_off.log

# 手動実行テスト
cd ~/discord-mcp-server
.venv/bin/python3 morning_automation.py
.venv/bin/python3 night_light_off.py
.venv/bin/python3 switchbot_aircon_comfort.py
```

---

## 関連ドキュメント

- `~/.claude/discord_automation.md` - Discord自動化全体のドキュメント
- `~/.claude/integrations.md` - 外部サービス連携（SwitchBot含む）

---

最終更新: 2026-02-03
