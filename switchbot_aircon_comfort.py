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
from pathlib import Path
import discord
from dotenv import load_dotenv

# 状態保存ファイル
STATE_FILE = Path(__file__).parent / 'aircon_state.json'


def load_previous_state() -> Optional[str]:
    """前回のエアコン状態を読み込む"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('mode')
    except Exception as e:
        print(f"[WARN] 前回状態の読み込み失敗: {e}")
    return None


def save_current_state(mode: str):
    """現在のエアコン状態を保存"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'mode': mode, 'updated': datetime.now().isoformat()}, f)
    except Exception as e:
        print(f"[WARN] 状態の保存失敗: {e}")

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
    NOTION_DATA_SOURCE_ID = '2a800160-1818-814b-b27a-000b80e0ceb0'  # v2 Data Source 1

    # SwitchBotデバイスID
    AIRCON_DEVICE_ID = os.environ.get('AIRCON_DEVICE_ID', '02-202404131311-10141115')
    CO2_METER_ID = os.environ.get('CO2_METER_ID', 'B0E9FE561980')
    OUTDOOR_SENSOR_ID = os.environ.get('OUTDOOR_SENSOR_ID', 'D0C84206187C')
    HUMIDIFIER_ID = os.environ.get('HUMIDIFIER_ID', 'D48C49559C0A')

    # ===== 温度差ベースの制御閾値（科学的根拠に基づく） =====

    # 冬季: 絶対温度優先ロジック（2026-01-23改善）
    # ※温度差条件は削除（室内外温度差でヒートショックは起きないため）
    WINTER_HEATING_TARGET = 27    # 暖房設定温度
    WINTER_INDOOR_COLD = 24.0     # 室内 < 24℃ → 暖房ON（体感寒い）
    WINTER_INDOOR_HIGH = 26.0     # 室内 ≧ 26℃ → 暖房不要

    # 冬季夜間モード（21時〜5時、外気温8℃以下で室内25℃キープ）
    WINTER_NIGHT_START_HOUR = 21  # 夜間モード開始時刻
    WINTER_NIGHT_END_HOUR = 5     # 夜間モード終了時刻
    WINTER_NIGHT_OUTDOOR_COLD = 8.0   # 外気温8℃以下で夜間モード適用
    WINTER_NIGHT_TARGET = 27      # 夜間モード暖房設定温度（室温25℃維持のため高めに設定）
    WINTER_NIGHT_INDOOR_THRESHOLD = 25.0  # 室内25℃未満で暖房ON

    # 夏季: 絶対温度 + 温度差の複合ロジック
    SUMMER_TEMP_DIFF_HIGH = 7.0   # 温度差 ≧ 7℃ → 冷房OFF
    SUMMER_TEMP_DIFF_LOW = 5.0    # 温度差 < 5℃ → 体感暑い
    SUMMER_COOLING_TARGET = 29    # 冷房設定温度
    SUMMER_INDOOR_HOT = 28.0      # 室内 ≧ 28℃ → 絶対的に暑い
    SUMMER_INDOOR_WARM = 26.0     # 室内 ≧ 26℃ かつ 温度差小 → 冷房ON
    SUMMER_INDOOR_LOW = 26.0      # 室内 ≦ 26℃ → 冷房OFF

    # 緊急制御（絶対温度による安全制御）
    EMERGENCY_HOT = 32   # 室内32℃以上で緊急冷房
    EMERGENCY_COLD = 15  # 室内15℃以下で緊急暖房

    # CO2濃度アラート
    CO2_ALERT_THRESHOLD = 1000  # CO2 1000ppm以上で換気通知
    CO2_ALERT_CHANNEL_ID = 1437603269307535484  # Minamiサーバー通知チャンネル

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

    # ===== 冬季: 絶対温度優先ロジック（2026-01-23改善） =====
    if season == 'winter':
        # 夜間モード判定（21時〜5時）
        is_winter_night = (now.hour >= Config.WINTER_NIGHT_START_HOUR or now.hour < Config.WINTER_NIGHT_END_HOUR)
        is_outdoor_cold = outdoor_temp is not None and outdoor_temp <= Config.WINTER_NIGHT_OUTDOOR_COLD

        # 夜間モード（21時〜5時、外気温8℃以下）: 室内25℃キープ
        if is_winter_night and is_outdoor_cold:
            if indoor_temp < Config.WINTER_NIGHT_INDOOR_THRESHOLD:
                return {
                    'mode': 'heat',
                    'set_temp': Config.WINTER_NIGHT_TARGET,
                    'humidifier': humidifier_status,
                    'action': f'冬季夜間モード・室内{indoor_temp}℃ < {Config.WINTER_NIGHT_INDOOR_THRESHOLD}℃ → 暖房ON（{Config.WINTER_NIGHT_TARGET}℃）',
                    'priority': 'winter_night',
                    'controlled': True,
                    'reasoning': f'夜間（{now.hour}時）・外気温{outdoor_temp}℃≤{Config.WINTER_NIGHT_OUTDOOR_COLD}℃・室内{indoor_temp}℃が{Config.WINTER_NIGHT_INDOOR_THRESHOLD}℃未満のため暖房ON',
                    'season': season,
                    'time_of_day': time_of_day,
                    'temp_diff': temp_diff,
                    'temp_diff_action': '夜間モード暖房ON',
                    'night_mode': True
                }
            else:
                return {
                    'mode': 'none',
                    'set_temp': None,
                    'humidifier': humidifier_status,
                    'action': f'冬季夜間モード・室内{indoor_temp}℃ ≧ {Config.WINTER_NIGHT_INDOOR_THRESHOLD}℃ → 暖房不要',
                    'priority': 'winter_night_ok',
                    'controlled': False,
                    'reasoning': f'夜間（{now.hour}時）・外気温{outdoor_temp}℃≤{Config.WINTER_NIGHT_OUTDOOR_COLD}℃・室内{indoor_temp}℃が{Config.WINTER_NIGHT_INDOOR_THRESHOLD}℃以上のため暖房不要',
                    'season': season,
                    'time_of_day': time_of_day,
                    'temp_diff': temp_diff,
                    'temp_diff_action': '夜間モード暖房OFF',
                    'night_mode': True
                }

        # 通常モード: 暖房ON条件（最優先）: 室内 < 24℃ → 暖房ON
        if indoor_temp < Config.WINTER_INDOOR_COLD:
            return {
                'mode': 'heat',
                'set_temp': Config.WINTER_HEATING_TARGET,
                'humidifier': humidifier_status,
                'action': f'冬季・室内{indoor_temp}℃ < {Config.WINTER_INDOOR_COLD}℃ → 暖房ON（{Config.WINTER_HEATING_TARGET}℃）',
                'priority': 'temp_cold',
                'controlled': True,
                'reasoning': f'室内温度{indoor_temp}℃が{Config.WINTER_INDOOR_COLD}℃未満のため暖房ON',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '暖房ON（室温優先）',
                'night_mode': is_night
            }
        # 暖房OFF条件: 室内 ≧ 26℃ → 暖房不要
        elif indoor_temp >= Config.WINTER_INDOOR_HIGH:
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': humidifier_status,
                'action': f'冬季・室内{indoor_temp}℃ ≧ {Config.WINTER_INDOOR_HIGH}℃ → 暖房不要',
                'priority': 'temp_high',
                'controlled': False,
                'reasoning': f'室内温度{indoor_temp}℃が{Config.WINTER_INDOOR_HIGH}℃以上のため暖房不要',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '暖房OFF（十分暖かい）',
                'night_mode': is_night
            }
        else:
            # 適正範囲（24〜26℃）→ 現状維持
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': humidifier_status,
                'action': f'冬季・室内{indoor_temp}℃（{Config.WINTER_INDOOR_COLD}〜{Config.WINTER_INDOOR_HIGH}℃）→ 現状維持',
                'priority': 'temp_ok',
                'controlled': False,
                'reasoning': f'室内温度{indoor_temp}℃は適正範囲内',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '現状維持（適正範囲）',
                'night_mode': is_night
            }

    # ===== 夏季: 絶対温度 + 温度差の複合ロジック =====
    if season == 'summer':
        summer_diff = -temp_diff  # 室外-室内

        # 冷房OFF条件: 室内≦26℃ または 温度差≧7℃（コマンド送信しない）
        if indoor_temp <= Config.SUMMER_INDOOR_LOW or summer_diff >= Config.SUMMER_TEMP_DIFF_HIGH:
            reason = []
            if indoor_temp <= Config.SUMMER_INDOOR_LOW:
                reason.append(f'室内{indoor_temp}℃≦{Config.SUMMER_INDOOR_LOW}℃')
            if summer_diff >= Config.SUMMER_TEMP_DIFF_HIGH:
                reason.append(f'温度差{summer_diff:.1f}℃≧{Config.SUMMER_TEMP_DIFF_HIGH}℃')
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': 'off',
                'action': f'夏季・{" / ".join(reason)} → 冷房不要',
                'priority': 'temp_low',
                'controlled': False,  # OFFコマンドは送信しない
                'reasoning': f'{" または ".join(reason)}のため冷房不要',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '冷房OFF',
                'night_mode': is_night
            }
        # 冷房ON条件1: 室内≧28℃（絶対的に暑い）
        elif indoor_temp >= Config.SUMMER_INDOOR_HOT:
            return {
                'mode': 'cool',
                'set_temp': Config.SUMMER_COOLING_TARGET,
                'humidifier': 'off',
                'action': f'夏季・室内{indoor_temp}℃≧{Config.SUMMER_INDOOR_HOT}℃ → 冷房ON（{Config.SUMMER_COOLING_TARGET}℃）',
                'priority': 'temp_hot',
                'controlled': True,
                'reasoning': f'室内温度{indoor_temp}℃が{Config.SUMMER_INDOOR_HOT}℃以上（絶対的に暑い）',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '冷房ON（絶対暑）',
                'night_mode': is_night
            }
        # 冷房ON条件2: 室内26~28℃ かつ 温度差<5℃（体感暑い）
        elif indoor_temp >= Config.SUMMER_INDOOR_WARM and summer_diff < Config.SUMMER_TEMP_DIFF_LOW:
            return {
                'mode': 'cool',
                'set_temp': Config.SUMMER_COOLING_TARGET,
                'humidifier': 'off',
                'action': f'夏季・室内{indoor_temp}℃ / 温度差{summer_diff:.1f}℃<{Config.SUMMER_TEMP_DIFF_LOW}℃ → 冷房ON（{Config.SUMMER_COOLING_TARGET}℃）',
                'priority': 'temp_diff_low',
                'controlled': True,
                'reasoning': f'室内{indoor_temp}℃かつ温度差{summer_diff:.1f}℃が小さい（体感暑い）',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '冷房ON（体感暑）',
                'night_mode': is_night
            }
        else:
            # 適正範囲 → 現状維持
            return {
                'mode': 'none',
                'set_temp': None,
                'humidifier': 'off',
                'action': f'夏季・室内{indoor_temp}℃ / 温度差{summer_diff:.1f}℃ → 現状維持',
                'priority': 'temp_ok',
                'controlled': False,
                'reasoning': f'室内温度・温度差ともに適正範囲',
                'season': season,
                'time_of_day': time_of_day,
                'temp_diff': temp_diff,
                'temp_diff_action': '現状維持（適正範囲）',
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


# ===== 不快指数計算 =====
def calculate_discomfort_index(temperature: float, humidity: float) -> float:
    """不快指数（DI）を計算"""
    di = 0.81 * temperature + 0.01 * humidity * (0.99 * temperature - 14.3) + 46.3
    return round(di, 1)


def evaluate_discomfort_index(di: float, season: str) -> Dict[str, str]:
    """不快指数を評価"""
    if season == 'summer':
        if di < 70:
            return {'level': 'comfortable', 'text': '快適'}
        elif di < 75:
            return {'level': 'slightly_hot', 'text': 'やや暑い'}
        elif di < 80:
            return {'level': 'hot', 'text': '暑くて汗が出る'}
        elif di < 85:
            return {'level': 'very_hot', 'text': '暑くてたまらない'}
        else:
            return {'level': 'extremely_hot', 'text': '非常に暑い'}
    else:  # winter, spring, autumn
        if di < 60:
            return {'level': 'cold', 'text': '寒い'}
        elif di < 68:
            return {'level': 'slightly_cold', 'text': 'やや寒い'}
        elif di < 75:
            return {'level': 'comfortable', 'text': '快適'}
        elif di < 80:
            return {'level': 'slightly_warm', 'text': 'やや暖かい'}
        else:
            return {'level': 'hot', 'text': '暑い'}


# ===== Notion記録 =====
def log_to_notion(log_data: Dict, aircon_result: Optional[bool] = None) -> bool:
    """Notionにログを記録（既存DBフォーマット）"""
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {Config.NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2025-09-03'
    }

    control = log_data['control']
    indoor = log_data['indoor']
    outdoor = log_data.get('outdoor')

    # 制御サマリーを生成
    mode_jp = {'cool': '冷房', 'heat': '暖房', 'dry': '除湿', 'none': '停止'}.get(control['mode'], '不明')
    temp_diff = control.get('temp_diff')
    temp_diff_str = f"（温度差{temp_diff:.1f}℃）" if temp_diff is not None else ""

    if control['mode'] == 'none':
        summary = f"制御なし{temp_diff_str}"
    else:
        temp_str = f" {control['set_temp']}℃" if control.get('set_temp') else ""
        summary = f"{mode_jp}ON{temp_str}{temp_diff_str}"
        if control.get('priority') == 'emergency':
            summary += "【緊急】"

    # 日本時間（JST = UTC+9）
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    # 不快指数計算
    di = calculate_discomfort_index(indoor['temperature'], indoor['humidity'])
    di_eval = evaluate_discomfort_index(di, control['season'])

    # 既存DBのプロパティに合わせて記録
    properties = {
        '制御サマリー': {'title': [{'text': {'content': summary}}]},
        '日時': {'date': {'start': now_jst.strftime('%Y-%m-%dT%H:%M:%S+09:00')}},
        '室内温度': {'number': indoor['temperature']},
        '室内湿度': {'number': indoor['humidity']},
        'CO2濃度': {'number': indoor.get('co2')},
        '季節': {'select': {'name': get_season_jp(control['season'])}},
        '時間帯': {'select': {'name': get_time_of_day_jp(control['time_of_day'])}},
        'エアコンモード': {'select': {'name': mode_jp}},
        '加湿器': {'select': {'name': {'on': 'ON', 'off': 'OFF', 'maintain': '維持'}.get(control.get('humidifier', 'off'), 'OFF')}},
        '制御内容': {'rich_text': [{'text': {'content': control['action'][:2000]}}]},
        '制御根拠': {'rich_text': [{'text': {'content': control['reasoning'][:2000]}}]},
        '制御実行': {'checkbox': control['controlled']},
        '優先度': {'select': {'name': '通常'}},
        '夜間モード': {'checkbox': control.get('night_mode', False)},
        '不快指数': {'number': di},
        '不快指数評価': {'select': {'name': di_eval['text']}}
    }

    # 設定温度（ない場合は0）
    properties['設定温度'] = {'number': control.get('set_temp') or 0}

    # 外気温度・湿度
    if outdoor:
        properties['外気温度'] = {'number': outdoor['temperature']}
        properties['外気湿度'] = {'number': outdoor['humidity']}

    # API制御結果
    if aircon_result is not None:
        properties['API制御結果'] = {'select': {'name': '成功' if aircon_result else '失敗'}}

    data = {
        'parent': {'type': 'data_source_id', 'data_source_id': Config.NOTION_DATA_SOURCE_ID},
        'properties': properties
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if not response.ok:
            error_detail = response.text[:500] if hasattr(response, 'text') else str(response.status_code)
            print(f"[ERROR] Notion記録エラー: {response.status_code}")
            print(f"[ERROR] Response: {error_detail}")
            send_discord_error_notification(
                f"Notion API エラー (Status: {response.status_code})",
                error_detail
            )
            return False
        response.raise_for_status()
        print("[INFO] Notion記録完了")
        return True
    except Exception as e:
        print(f"[ERROR] Notion記録エラー: {e}")
        send_discord_error_notification(
            f"Notion記録例外エラー",
            str(e)
        )
        return False


# ===== Discord エラー通知 =====
def send_discord_error_notification(error_message: str, error_details: str = ""):
    """Notion記録エラー時にDiscord通知を送信"""
    try:
        url = f"https://discord.com/api/v10/channels/{Config.DISCORD_CHANNEL_ID}/messages"
        headers = {
            'Authorization': f'Bot {Config.DISCORD_TOKEN}',
            'Content-Type': 'application/json'
        }

        content = f"🚨 **エアコン制御システム - Notion記録エラー**\n\n"
        content += f"**エラー内容**: {error_message}\n"
        if error_details:
            content += f"**詳細**: {error_details[:500]}\n"
        content += f"**発生時刻**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "⚠️ Notion記録が失敗しています。確認してください。"

        data = {'content': content}
        response = requests.post(url, headers=headers, json=data)

        if response.ok:
            print("[INFO] Discord エラー通知送信完了")
        else:
            print(f"[WARN] Discord エラー通知送信失敗: {response.status_code}")
    except Exception as e:
        print(f"[WARN] Discord エラー通知送信エラー: {e}")


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


# ===== CO2アラート（Discord通知） =====
CO2_ALERT_STATE_FILE = Path(__file__).parent / 'co2_alert_state.json'

def load_co2_alert_state() -> bool:
    """前回のCO2アラート状態を読み込む（True=アラート中）"""
    try:
        if CO2_ALERT_STATE_FILE.exists():
            with open(CO2_ALERT_STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('alerted', False)
    except:
        pass
    return False

def save_co2_alert_state(alerted: bool):
    """CO2アラート状態を保存"""
    try:
        with open(CO2_ALERT_STATE_FILE, 'w') as f:
            json.dump({'alerted': alerted, 'updated': datetime.now().isoformat()}, f)
    except:
        pass

def send_co2_alert_discord(co2_level: int):
    """CO2アラートをDiscordに送信"""
    try:
        url = f"https://discord.com/api/v10/channels/{Config.CO2_ALERT_CHANNEL_ID}/messages"
        headers = {
            'Authorization': f'Bot {Config.DISCORD_TOKEN}',
            'Content-Type': 'application/json'
        }
        data = {
            'content': f'⚠️ **CO2濃度アラート**\n\n現在のCO2濃度: **{co2_level}ppm**\n\n換気してください！'
        }
        response = requests.post(url, headers=headers, json=data)
        if response.ok:
            print(f"[INFO] CO2アラートDiscord通知送信完了: {co2_level}ppm")
        else:
            print(f"[ERROR] CO2アラートDiscord通知失敗: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] CO2アラートDiscord通知エラー: {e}")


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
    co2_level = indoor_data.get('co2')
    if co2_level:
        print(f"[INFO] CO2濃度: {co2_level}ppm")
    if outdoor_data:
        print(f"[INFO] 屋外: {outdoor_data['temperature']}℃")
        temp_diff = indoor_data['temperature'] - outdoor_data['temperature']
        print(f"[INFO] 温度差（室内-室外）: {temp_diff:.1f}℃")

    # 1.5. CO2濃度チェック（1000ppm超で換気通知）
    if co2_level and co2_level >= Config.CO2_ALERT_THRESHOLD:
        was_alerted = load_co2_alert_state()
        if not was_alerted:
            send_co2_alert_discord(co2_level)
            save_co2_alert_state(True)
            print(f"[INFO] CO2アラート発報: {co2_level}ppm")
        else:
            print(f"[INFO] CO2高濃度継続中（アラート済み）: {co2_level}ppm")
    elif co2_level and co2_level < Config.CO2_ALERT_THRESHOLD:
        was_alerted = load_co2_alert_state()
        if was_alerted:
            save_co2_alert_state(False)
            print(f"[INFO] CO2濃度正常化: {co2_level}ppm")

    # 2. 温度差ベースの制御判定
    control_decision = determine_temp_diff_control(indoor_data, outdoor_data)
    print(f"[INFO] 制御判定: {control_decision['action']}")
    print(f"[INFO] 制御根拠: {control_decision['reasoning']}")

    # 3. 前回の状態と比較してエアコン制御実行
    previous_mode = load_previous_state()
    current_mode = control_decision['mode']
    print(f"[INFO] 前回モード: {previous_mode} → 今回モード: {current_mode}")

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
