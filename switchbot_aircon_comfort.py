#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SwitchBot エアコン制御テスト（温度差ベース）
室内外温度差に基づいた快適制御の検証用スクリプト

科学的根拠:
- 夏季: 室内外温度差5~7℃以内で冷房病予防
- 冬季: 温度差3~5℃以内でヒートショック予防
"""

import os
import sys
import time
import json
import subprocess
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
import discord
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()


# ===== 設定値 =====
class Config:
    # SwitchBot API設定
    SWITCHBOT_TOKEN = os.environ.get('SWITCHBOT_TOKEN')
    SWITCHBOT_API_URL = 'https://api.switch-bot.com/v1.1/devices'

    # Discord設定
    DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
    DISCORD_CHANNEL_ID = int(os.environ.get('AIRCON_CONTROL_DISCORD_CHANNEL', '1437603269307535484'))

    # Notion設定（本番DB）
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
    NOTION_DATABASE_ID = '2a800160-1818-8102-9426-e392d267abd6'  # 本番DB

    # SwitchBotデバイスID
    AIRCON_DEVICE_ID = os.environ.get('AIRCON_DEVICE_ID', '02-202404131311-10141115')
    CO2_METER_ID = os.environ.get('CO2_METER_ID', 'B0E9FE561980')
    OUTDOOR_SENSOR_ID = os.environ.get('OUTDOOR_SENSOR_ID', 'D0C84206187C')
    HUMIDIFIER_ID = os.environ.get('HUMIDIFIER_ID', 'D48C49559C0A')

    # ===== 温度差ベースの制御閾値（科学的根拠に基づく） =====

    # 冬季: ヒートショック予防（推奨温度差3~5℃以内）
    WINTER_TEMP_DIFF_HIGH = 5.0   # 室内-室外 ≧ 5℃ → 暖房OFF（暑く感じる）
    WINTER_TEMP_DIFF_LOW = 2.0    # 室内-室外 ≦ 2℃ → 暖房ON（寒く感じる）
    WINTER_HEATING_TARGET = 25    # 暖房設定温度

    # 夏季: 冷房病予防（推奨温度差5~7℃以内）
    SUMMER_TEMP_DIFF_HIGH = 7.0   # 室外-室内 ≧ 7℃ → 冷房弱める
    SUMMER_TEMP_DIFF_LOW = 5.0    # 室外-室内 ≦ 5℃ → 冷房維持
    SUMMER_COOLING_TARGET = 27    # 冷房設定温度

    # 緊急制御（絶対温度による安全制御）
    EMERGENCY_HOT = 32   # 室内32℃以上で緊急冷房
    EMERGENCY_COLD = 15  # 室内15℃以下で緊急暖房

    # 加湿器設定（冬季のみ）
    HUMIDIFIER_START = 60  # 湿度60%未満で加湿器ON
    HUMIDIFIER_STOP = 65   # 湿度65%以上で加湿器OFF


# ===== SwitchBot API呼び出し =====
def call_switchbot_api(endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Dict]:
    """SwitchBot APIを呼び出す"""
    url = f"{Config.SWITCHBOT_API_URL}/{endpoint}"
    headers = {
        'Authorization': Config.SWITCHBOT_TOKEN,
        'Content-Type': 'application/json'
    }

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        result = response.json()

        if result.get('statusCode') == 100:
            return result.get('body')
        else:
            print(f"[ERROR] SwitchBot API Error: {result.get('message')}")
            return None
    except Exception as e:
        print(f"[ERROR] SwitchBot API呼び出しエラー: {e}")
        return None


def get_sensor_data(device_id: str) -> Optional[Dict]:
    """センサーデータ取得"""
    body = call_switchbot_api(f"{device_id}/status")
    if body:
        return {
            'temperature': body.get('temperature'),
            'humidity': body.get('humidity'),
            'co2': body.get('CO2')
        }
    return None


def control_aircon(mode: str, temperature: Optional[int] = None) -> bool:
    """エアコン制御"""
    if mode == 'none':
        data = {'command': 'turnOff', 'parameter': 'default', 'commandType': 'command'}
        result = call_switchbot_api(f"{Config.AIRCON_DEVICE_ID}/commands", 'POST', data)
        return result is not None

    mode_param = {'cool': '2', 'dry': '3', 'heat': '5', 'auto': '1'}.get(mode, '1')
    fan_speed = '3'  # 中風
    command_params = f"{temperature},{mode_param},{fan_speed},on"

    data = {'command': 'setAll', 'parameter': command_params, 'commandType': 'command'}
    result = call_switchbot_api(f"{Config.AIRCON_DEVICE_ID}/commands", 'POST', data)
    return result is not None


def control_humidifier(mode: str, current_humidity: Optional[float] = None) -> bool:
    """加湿器制御"""
    now = datetime.now()
    hour = now.hour
    is_night_mode_time = (hour >= 22) or (hour < 7)

    if is_night_mode_time:
        print(f"[INFO] 夜間時間帯（{hour}時）: 加湿器をおやすみモードに設定")
        data = {
            'command': 'setMode',
            'parameter': {'mode': 6, 'targetHumidify': 60},
            'commandType': 'command'
        }
        result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
        return result is not None

    if mode == 'maintain':
        return True

    if mode == 'off':
        data = {'command': 'turnOff', 'parameter': 'default', 'commandType': 'command'}
        result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
        return result is not None

    if current_humidity is not None and current_humidity >= 60:
        humidifier_mode = 3
    else:
        humidifier_mode = 2

    data = {
        'command': 'setMode',
        'parameter': {'mode': humidifier_mode, 'targetHumidify': 60},
        'commandType': 'command'
    }
    result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
    return result is not None


# ===== 季節判定 =====
def get_season() -> str:
    """季節判定（月ベース）"""
    month = datetime.now().month
    if 3 <= month <= 5:
        return 'spring'
    elif 6 <= month <= 8:
        return 'summer'
    elif 9 <= month <= 10:
        return 'autumn'
    else:
        return 'winter'


def get_season_jp(season: str) -> str:
    """季節の日本語表記"""
    return {'spring': '春季', 'summer': '夏季', 'autumn': '秋季', 'winter': '冬季'}.get(season, '不明')


def get_time_of_day(hour: int) -> str:
    """時間帯判定"""
    if 6 <= hour < 10:
        return 'morning'
    elif 10 <= hour < 16:
        return 'daytime'
    elif 16 <= hour < 22:
        return 'evening'
    else:
        return 'night'


def get_time_of_day_jp(time_of_day: str) -> str:
    """時間帯の日本語表記"""
    return {'morning': '朝', 'daytime': '昼', 'evening': '夕', 'night': '夜'}.get(time_of_day, '不明')


# ===== 温度差ベースの制御判定（新ロジック） =====
def determine_temp_diff_control(indoor_data: Dict, outdoor_data: Optional[Dict]) -> Dict[str, Any]:
    """
    温度差ベースの制御判定

    科学的根拠:
    - 冬季: 室内外温度差3~5℃以内でヒートショック予防
    - 夏季: 室内外温度差5~7℃以内で冷房病予防
    """
    indoor_temp = indoor_data['temperature']
    indoor_humidity = indoor_data['humidity']
    outdoor_temp = outdoor_data['temperature'] if outdoor_data else None

    season = get_season()
    now = datetime.now()
    time_of_day = get_time_of_day(now.hour)
    is_night = now.hour >= 22 or now.hour < 6

    # 室内外温度差を計算
    temp_diff = None
    if outdoor_temp is not None:
        temp_diff = indoor_temp - outdoor_temp

    # 加湿器制御判定（冬季のみ）
    humidifier_status = 'off'
    if season == 'winter':
        if indoor_humidity < Config.HUMIDIFIER_START:
            humidifier_status = 'on'
        elif indoor_humidity >= Config.HUMIDIFIER_STOP:
            humidifier_status = 'off'
        else:
            humidifier_status = 'maintain'

    # ===== 緊急制御（絶対温度による安全制御） =====
    if indoor_temp >= Config.EMERGENCY_HOT:
        return {
            'mode': 'cool',
            'set_temp': Config.SUMMER_COOLING_TARGET,
            'humidifier': 'off',
            'action': f'【緊急】室内{indoor_temp}℃ → 緊急冷房',
            'priority': 'emergency',
            'controlled': True,
            'reasoning': f'室内温度{indoor_temp}℃が緊急閾値{Config.EMERGENCY_HOT}℃を超過',
            'season': season,
            'time_of_day': time_of_day,
            'temp_diff': temp_diff,
            'temp_diff_action': '緊急制御',
            'night_mode': is_night
        }

    if indoor_temp <= Config.EMERGENCY_COLD:
        return {
            'mode': 'heat',
            'set_temp': Config.WINTER_HEATING_TARGET,
            'humidifier': humidifier_status,
            'action': f'【緊急】室内{indoor_temp}℃ → 緊急暖房',
            'priority': 'emergency',
            'controlled': True,
            'reasoning': f'室内温度{indoor_temp}℃が緊急閾値{Config.EMERGENCY_COLD}℃を下回る',
            'season': season,
            'time_of_day': time_of_day,
            'temp_diff': temp_diff,
            'temp_diff_action': '緊急制御',
            'night_mode': is_night
        }

    # 屋外センサーがない場合は制御なし
    if temp_diff is None:
        return {
            'mode': 'none',
            'set_temp': None,
            'humidifier': humidifier_status,
            'action': '屋外センサーデータなし → 制御スキップ',
            'priority': 'skip',
            'controlled': False,
            'reasoning': '屋外温度データが取得できないため制御をスキップ',
            'season': season,
            'time_of_day': time_of_day,
            'temp_diff': None,
            'temp_diff_action': 'データなし',
            'night_mode': is_night
        }

    # ===== 冬季: 温度差ベース制御 =====
    if season == 'winter':
        if temp_diff >= Config.WINTER_TEMP_DIFF_HIGH:
            # 室内が室外より5℃以上高い → 暖房OFF（暑く感じる）
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': humidifier_status,
                'action': f'冬季・温度差{temp_diff:.1f}℃（≧{Config.WINTER_TEMP_DIFF_HIGH}℃）→ 暖房OFF',
                'priority': 'temp_diff_high',
                'controlled': True,
                'reasoning': f'室内外温度差{temp_diff:.1f}℃が{Config.WINTER_TEMP_DIFF_HIGH}℃以上。体感的に暑いため暖房停止',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '暖房OFF（温度差大）',
                'night_mode': is_night
            }
        elif temp_diff <= Config.WINTER_TEMP_DIFF_LOW:
            # 室内が室外より2℃以下高い → 暖房ON（寒く感じる）
            return {
                'mode': 'heat',
                'set_temp': Config.WINTER_HEATING_TARGET,
                'humidifier': humidifier_status,
                'action': f'冬季・温度差{temp_diff:.1f}℃（≦{Config.WINTER_TEMP_DIFF_LOW}℃）→ 暖房ON（{Config.WINTER_HEATING_TARGET}℃）',
                'priority': 'temp_diff_low',
                'controlled': True,
                'reasoning': f'室内外温度差{temp_diff:.1f}℃が{Config.WINTER_TEMP_DIFF_LOW}℃以下。体感的に寒いため暖房開始',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '暖房ON（温度差小）',
                'night_mode': is_night
            }
        else:
            # 温度差が適正範囲（2~5℃）→ 現状維持
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': humidifier_status,
                'action': f'冬季・温度差{temp_diff:.1f}℃（適正範囲）→ 現状維持',
                'priority': 'temp_diff_ok',
                'controlled': False,
                'reasoning': f'室内外温度差{temp_diff:.1f}℃が適正範囲（{Config.WINTER_TEMP_DIFF_LOW}~{Config.WINTER_TEMP_DIFF_HIGH}℃）',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '現状維持（適正範囲）',
                'night_mode': is_night
            }

    # ===== 夏季: 温度差ベース制御 =====
    if season == 'summer':
        # 夏は室外-室内で計算（室外の方が暑い想定）
        summer_diff = -temp_diff  # 室外-室内

        if summer_diff >= Config.SUMMER_TEMP_DIFF_HIGH:
            # 室外が室内より7℃以上高い → 冷房病リスク、冷房弱める
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': 'off',
                'action': f'夏季・温度差{summer_diff:.1f}℃（≧{Config.SUMMER_TEMP_DIFF_HIGH}℃）→ 冷房OFF（冷房病予防）',
                'priority': 'temp_diff_high',
                'controlled': True,
                'reasoning': f'室内外温度差{summer_diff:.1f}℃が{Config.SUMMER_TEMP_DIFF_HIGH}℃以上。冷房病リスクのため冷房停止',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '冷房OFF（温度差大）',
                'night_mode': is_night
            }
        elif summer_diff >= Config.SUMMER_TEMP_DIFF_LOW:
            # 室外が室内より5~7℃高い → 適正範囲、冷房維持
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': 'off',
                'action': f'夏季・温度差{summer_diff:.1f}℃（適正範囲）→ 現状維持',
                'priority': 'temp_diff_ok',
                'controlled': False,
                'reasoning': f'室内外温度差{summer_diff:.1f}℃が適正範囲（{Config.SUMMER_TEMP_DIFF_LOW}~{Config.SUMMER_TEMP_DIFF_HIGH}℃）',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '現状維持（適正範囲）',
                'night_mode': is_night
            }
        else:
            # 温度差が小さい → 冷房ON
            return {
                'mode': 'cool',
                'set_temp': Config.SUMMER_COOLING_TARGET,
                'humidifier': 'off',
                'action': f'夏季・温度差{summer_diff:.1f}℃（＜{Config.SUMMER_TEMP_DIFF_LOW}℃）→ 冷房ON（{Config.SUMMER_COOLING_TARGET}℃）',
                'priority': 'temp_diff_low',
                'controlled': True,
                'reasoning': f'室内外温度差{summer_diff:.1f}℃が{Config.SUMMER_TEMP_DIFF_LOW}℃未満。快適維持のため冷房開始',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '冷房ON（温度差小）',
                'night_mode': is_night
            }

    # ===== 春・秋: 基本的に制御なし =====
    return {
        'mode': 'none',
        'set_temp': None,
        'humidifier': humidifier_status,
        'action': f'{get_season_jp(season)}・温度差{temp_diff:.1f}℃ → 制御なし',
        'priority': 'moderate_default',
        'controlled': False,
        'reasoning': f'{get_season_jp(season)}は温度差ベース制御の対象外',
        'season': season,
        'time_of_day': time_of_day,
        'temp_diff': temp_diff,
        'temp_diff_action': '中間期・制御なし',
        'night_mode': is_night
    }


# ===== Notion記録 =====
def log_to_notion(log_data: Dict, aircon_result: Optional[bool] = None) -> bool:
    """Notionにログを記録"""
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {Config.NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    control = log_data['control']
    indoor = log_data['indoor']
    outdoor = log_data.get('outdoor')

    # 制御サマリーを生成
    mode_jp = {'cool': '冷房', 'heat': '暖房', 'dry': '除湿', 'none': '停止'}.get(control['mode'], '不明')
    if control['mode'] == 'none':
        summary = f"{control.get('temp_diff_action', '制御なし')}"
    else:
        temp_str = f" {control['set_temp']}℃" if control.get('set_temp') else ""
        summary = f"{mode_jp}ON{temp_str}"
        if control.get('priority') == 'emergency':
            summary += "【緊急】"

    # 日本時間（JST = UTC+9）
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    # Notionに記録するプロパティ
    properties = {
        '制御サマリー': {'title': [{'text': {'content': summary}}]},
    }

    data = {
        'parent': {'database_id': Config.NOTION_DATABASE_ID},
        'properties': properties,
        'children': [
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"日時: {now_jst.strftime('%Y-%m-%d %H:%M:%S')}"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"室内: {indoor['temperature']}℃ / {indoor['humidity']}%"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"室外: {outdoor['temperature'] if outdoor else 'N/A'}℃"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"温度差: {control.get('temp_diff', 'N/A')}℃"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"季節: {get_season_jp(control['season'])}"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"制御内容: {control['action']}"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"制御根拠: {control['reasoning']}"}}]
                }
            },
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': f"API結果: {'成功' if aircon_result else '失敗' if aircon_result is not None else '未実行'}"}}]
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print("[INFO] Notion記録完了（テストDB）")
        return True
    except Exception as e:
        print(f"[ERROR] Notion記録エラー: {e}")
        return False


# ===== macOS通知 =====
def send_macos_notification(title: str, message: str):
    """macOS通知"""
    try:
        subprocess.run([
            'osascript', '-e',
            f'display notification "{message}" with title "{title}"'
        ])
        print("[INFO] macOS通知送信完了")
    except Exception as e:
        print(f"[ERROR] macOS通知エラー: {e}")


# ===== メイン処理 =====
async def main():
    """メイン制御処理"""
    print("=== エアコン制御テスト（温度差ベース）開始 ===")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. センサーデータ取得
    print("[INFO] センサーデータ取得中...")
    indoor_data = get_sensor_data(Config.CO2_METER_ID)
    outdoor_data = get_sensor_data(Config.OUTDOOR_SENSOR_ID)

    if not indoor_data:
        print("[ERROR] 室内センサーデータ取得失敗")
        return

    print(f"[INFO] 室内: {indoor_data['temperature']}℃ / {indoor_data['humidity']}%")
    if outdoor_data:
        print(f"[INFO] 屋外: {outdoor_data['temperature']}℃")
        temp_diff = indoor_data['temperature'] - outdoor_data['temperature']
        print(f"[INFO] 温度差（室内-室外）: {temp_diff:.1f}℃")

    # 2. 温度差ベースの制御判定
    control_decision = determine_temp_diff_control(indoor_data, outdoor_data)
    print(f"[INFO] 制御判定: {control_decision['action']}")
    print(f"[INFO] 制御根拠: {control_decision['reasoning']}")

    # 3. エアコン制御実行
    aircon_result = None
    if control_decision['controlled']:
        print(f"[INFO] エアコン制御実行: {control_decision['mode']} {control_decision.get('set_temp', 'N/A')}℃")
        aircon_result = control_aircon(control_decision['mode'], control_decision.get('set_temp'))
        print(f"[INFO] エアコン制御結果: {'成功' if aircon_result else '失敗'}")
    else:
        print("[INFO] エアコン制御: 制御不要")

    # 4. 加湿器制御実行
    humidifier_mode = control_decision.get('humidifier', 'off')
    print(f"[INFO] 加湿器制御: {humidifier_mode}")
    humidifier_result = control_humidifier(humidifier_mode, indoor_data['humidity'])
    print(f"[INFO] 加湿器制御結果: {'成功' if humidifier_result else '失敗'}")

    # 5. ログデータ作成
    log_data = {
        'indoor': indoor_data,
        'outdoor': outdoor_data,
        'control': control_decision
    }

    # 6. Notion記録
    log_to_notion(log_data, aircon_result)

    # 7. macOS通知
    send_macos_notification(
        "エアコン制御テスト（温度差ベース）",
        control_decision['action']
    )

    print("=== 制御完了 ===")


if __name__ == '__main__':
    asyncio.run(main())
