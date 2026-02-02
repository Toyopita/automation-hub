#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SwitchBot エアコン自動制御システム
不快指数ベースの季節別快適制御
"""

import os
import sys
import time
import json
import subprocess
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List
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

    # Notion設定
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
    NOTION_DATA_SOURCE_ID = os.environ.get('AIRCON_CONTROL_NOTION_DB', '2a800160-1818-814b-b27a-000b80e0ceb0')

    # SwitchBotデバイスID
    AIRCON_DEVICE_ID = os.environ.get('AIRCON_DEVICE_ID', '02-202404131311-10141115')
    CO2_METER_ID = os.environ.get('CO2_METER_ID', 'B0E9FE561980')
    OUTDOOR_SENSOR_ID = os.environ.get('OUTDOOR_SENSOR_ID', 'D0C84206187C')
    CIRCULATOR_ID = os.environ.get('CIRCULATOR_ID', '3C84279DF0A6')
    HUMIDIFIER_ID = os.environ.get('HUMIDIFIER_ID', 'D48C49559C0A')

    # 季節判定基準
    SUMMER_TEMP = 25
    WINTER_TEMP = 20

    # 冬季設定
    WINTER_HEATING_START = 23  # 室温23℃未満で暖房開始（通常）
    WINTER_HEATING_START_COLD = 25  # 室温25℃未満で暖房開始（外気温が低い日）
    COLD_OUTDOOR_THRESHOLD = 8  # 外気温8℃以下で「寒い日」と判定
    WINTER_HEATING_TARGET = 27  # 暖房設定温度27℃（通常）
    WINTER_HEATING_TARGET_NIGHT = 24  # 暖房設定温度24℃（深夜0:00〜6:00）
    WINTER_HEATING_STOP = 26    # 室温26℃で暖房停止

    # 加湿器設定（冬季のみ）
    HUMIDIFIER_START = 60  # 湿度60%未満で加湿器ON
    HUMIDIFIER_STOP = 65   # 湿度65%以上で加湿器OFF

    # 中間期設定（現在は制御なし）
    MODERATE_IDEAL_MIN = 25
    MODERATE_IDEAL_MAX = 28
    MODERATE_HEATING_TARGET = 23
    MODERATE_COOLING_TARGET = 29

    # 不快指数制御基準（夏季）
    DI_MORNING_START = 75
    DI_DAYTIME_START = 74
    DI_EVENING_START = 73
    DI_NIGHT_START = 76
    DI_STOP_THRESHOLD = 71
    DI_EMERGENCY = 85
    DI_SEVERE = 80
    COOLING_TARGET_TEMP = 29

    # 湿度制御
    HUMIDITY_HIGH = 70
    HUMIDITY_EMERGENCY = 80

    # 緊急制御
    EMERGENCY_HOT = 32
    EMERGENCY_COLD = 15


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
        # エアコンOFF
        data = {'command': 'turnOff', 'parameter': 'default', 'commandType': 'command'}
        result = call_switchbot_api(f"{Config.AIRCON_DEVICE_ID}/commands", 'POST', data)
        return result is not None

    # エアコンON（setAllコマンド一発で全設定を送信）
    # モード: 0/1=自動, 2=冷房, 3=除湿, 4=ファン, 5=暖房（Qiitaから確認済み）
    # 風量: 1=自動, 2=弱, 3=中, 4=強
    mode_param = {'cool': '2', 'dry': '3', 'heat': '5', 'auto': '1'}.get(mode, '1')
    fan_speed = '3'  # 中風
    command_params = f"{temperature},{mode_param},{fan_speed},on"

    data = {'command': 'setAll', 'parameter': command_params, 'commandType': 'command'}
    result = call_switchbot_api(f"{Config.AIRCON_DEVICE_ID}/commands", 'POST', data)
    return result is not None


def control_circulator(mode: str) -> bool:
    """サーキュレーター制御"""
    command = 'turnOn' if mode == 'on' else 'turnOff'
    data = {'command': command, 'parameter': 'default', 'commandType': 'command'}
    result = call_switchbot_api(f"{Config.CIRCULATOR_ID}/commands", 'POST', data)
    return result is not None


def control_humidifier(mode: str, current_humidity: Optional[float] = None) -> bool:
    """加湿器制御"""
    # 時間帯チェック: 22:00〜7:00の間は強制的におやすみモード
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    is_night_mode_time = (hour >= 22) or (hour < 7)

    if is_night_mode_time:
        # 22:00〜7:00の間は強制的におやすみモード（mode=6）
        print(f"[INFO] 夜間時間帯（{hour}:{minute:02d}）: 加湿器をおやすみモードに設定")
        data = {
            'command': 'setMode',
            'parameter': {'mode': 6, 'targetHumidify': 60},  # 6 = おやすみモード
            'commandType': 'command'
        }
        result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
        return result is not None

    # 通常時間帯の制御
    if mode == 'maintain':
        return True  # 現状維持の場合は制御しない

    if mode == 'off':
        # 加湿器OFF
        data = {'command': 'turnOff', 'parameter': 'default', 'commandType': 'command'}
        result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
        return result is not None

    # 加湿器ON + モード設定
    # mode: 1=強, 2=中, 3=弱, 5=humidity mode, 6=sleep, 7=auto, 8=drying
    # 湿度60%以上の場合は弱モード、それ以外は中モード
    if current_humidity is not None and current_humidity >= 60:
        humidifier_mode = 3  # 弱モード
    else:
        humidifier_mode = 2  # 中モード

    data = {
        'command': 'setMode',
        'parameter': {'mode': humidifier_mode, 'targetHumidify': 60},
        'commandType': 'command'
    }
    result = call_switchbot_api(f"{Config.HUMIDIFIER_ID}/commands", 'POST', data)
    return result is not None


# ===== 不快指数計算 =====
def calculate_discomfort_index(temperature: float, humidity: float) -> float:
    """不快指数（DI）を計算"""
    di = 0.81 * temperature + 0.01 * humidity * (0.99 * temperature - 14.3) + 46.3
    return round(di, 1)


def evaluate_discomfort_index(di: float) -> Dict[str, str]:
    """不快指数を評価（夏季用）"""
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


def evaluate_comfort_index_winter(di: float) -> Dict[str, str]:
    """快適度を評価（冬季用）"""
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


def evaluate_comfort_index_spring(di: float) -> Dict[str, str]:
    """快適度を評価（春季用）"""
    if di < 65:
        return {'level': 'slightly_cold', 'text': 'やや寒い'}
    elif di < 72:
        return {'level': 'comfortable', 'text': '快適'}
    elif di < 77:
        return {'level': 'slightly_warm', 'text': 'やや暖かい'}
    else:
        return {'level': 'hot', 'text': '暑い'}


def evaluate_comfort_index_autumn(di: float) -> Dict[str, str]:
    """快適度を評価（秋季用）"""
    if di < 65:
        return {'level': 'slightly_cold', 'text': 'やや寒い'}
    elif di < 72:
        return {'level': 'comfortable', 'text': '快適'}
    elif di < 77:
        return {'level': 'slightly_warm', 'text': 'やや暖かい'}
    else:
        return {'level': 'hot', 'text': '暑い'}


# ===== 時間帯・季節判定 =====
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


def is_night_time(hour: int) -> bool:
    """夜間判定"""
    return hour >= 22 or hour < 6


def get_season(outdoor_temp: Optional[float] = None) -> str:
    """季節判定（月ベース：春夏秋冬）"""
    month = datetime.now().month

    # 月による季節判定
    if 3 <= month <= 5:
        return 'spring'  # 3月～5月: 春季
    elif 6 <= month <= 8:
        return 'summer'  # 6月～8月: 夏季
    elif 9 <= month <= 10:
        return 'autumn'  # 9月～10月: 秋季
    else:  # 11月～2月
        return 'winter'  # 11月～2月: 冬季


def get_season_jp(season: str) -> str:
    """季節の日本語表記"""
    return {'spring': '春季', 'summer': '夏季', 'autumn': '秋季', 'winter': '冬季'}.get(season, '不明')


# ===== 制御判定ロジック（GASから移植） =====
# （前のコードと同じなので省略）

def determine_seasonal_control(indoor_data: Dict, outdoor_data: Optional[Dict]) -> Dict[str, Any]:
    """メイン制御判定（簡易版 - 詳細は省略）"""
    indoor_temp = indoor_data['temperature']
    indoor_humidity = indoor_data['humidity']
    outdoor_temp = outdoor_data['temperature'] if outdoor_data else None

    season = get_season()  # 月ベースで判定
    now = datetime.now()
    time_of_day = get_time_of_day(now.hour)
    is_night = is_night_time(now.hour)

    # 全ての季節で不快指数を計算
    di = calculate_discomfort_index(indoor_temp, indoor_humidity)

    # 季節に応じた評価関数を選択
    if season == 'spring':
        di_eval = evaluate_comfort_index_spring(di)  # 春季用
    elif season == 'summer':
        di_eval = evaluate_discomfort_index(di)  # 夏季用
    elif season == 'autumn':
        di_eval = evaluate_comfort_index_autumn(di)  # 秋季用
    else:  # winter
        di_eval = evaluate_comfort_index_winter(di)  # 冬季用

    # 簡易版：夏季のみ実装
    if season == 'summer':
        di_thresholds = {
            'morning': Config.DI_MORNING_START,
            'daytime': Config.DI_DAYTIME_START,
            'evening': Config.DI_EVENING_START,
            'night': Config.DI_NIGHT_START
        }
        threshold = di_thresholds[time_of_day]

        if di >= threshold:
            return {
                'mode': 'cool',
                'set_temp': Config.COOLING_TARGET_TEMP,
                'circulator': 'off' if is_night else 'on',
                'humidifier': 'off',
                'action': f'{time_of_day}時間帯制御（DI:{di} → {Config.COOLING_TARGET_TEMP}℃）',
                'priority': f'di_{time_of_day}',
                'controlled': True,
                'reasoning': f'不快指数{di}（{di_eval["text"]}）で冷房',
                'season': season,
                'time_of_day': time_of_day,
                'discomfort_index': di,
                'night_mode': is_night
            }
        else:
            return {
                'mode': 'none',
                'set_temp': None,
                'circulator': 'off' if is_night else 'on',
                'humidifier': 'off',
                'action': f'夏季快適状態（DI:{di}）',
                'priority': 'summer_comfortable',
                'controlled': False,
                'reasoning': f'不快指数{di}（{di_eval["text"]}）で快適',
                'season': season,
                'time_of_day': time_of_day,
                'discomfort_index': di,
                'night_mode': is_night
            }

    # 冬季制御
    if season == 'winter':
        # 加湿器制御判定
        humidifier_status = 'on' if indoor_humidity < Config.HUMIDIFIER_START else ('off' if indoor_humidity >= Config.HUMIDIFIER_STOP else 'maintain')

        # 外気温に応じた暖房開始温度を決定
        is_cold_day = outdoor_temp is not None and outdoor_temp <= Config.COLD_OUTDOOR_THRESHOLD
        heating_start_temp = Config.WINTER_HEATING_START_COLD if is_cold_day else Config.WINTER_HEATING_START

        if indoor_temp < heating_start_temp:
            return {
                'mode': 'heat',
                'set_temp': Config.WINTER_HEATING_TARGET,
                'circulator': 'off',
                'humidifier': humidifier_status,
                'action': f'冬季暖房（室温{indoor_temp}℃ → {Config.WINTER_HEATING_TARGET}℃）',
                'priority': 'winter_heating',
                'controlled': True,
                'reasoning': f'室温{indoor_temp}℃が{Config.WINTER_HEATING_START}℃未満のため暖房',
                'season': season,
                'time_of_day': time_of_day,
                'discomfort_index': di,
                'night_mode': is_night
            }
        elif indoor_temp >= Config.WINTER_HEATING_STOP:
            return {
                'mode': 'none',
                'set_temp': None,
                'circulator': 'off',
                'humidifier': humidifier_status,
                'action': f'冬季暖房停止（室温{indoor_temp}℃ → OFF）',
                'priority': 'winter_heating_stop',
                'controlled': True,
                'reasoning': f'室温{indoor_temp}℃が{Config.WINTER_HEATING_STOP}℃以上のため暖房停止',
                'season': season,
                'time_of_day': time_of_day,
                'discomfort_index': di,
                'night_mode': is_night
            }
        else:
            # 22℃〜26℃の間は現状維持
            return {
                'mode': 'none',
                'set_temp': None,
                'circulator': 'off',
                'humidifier': humidifier_status,
                'action': f'冬季適温維持（室温{indoor_temp}℃）',
                'priority': 'winter_maintain',
                'controlled': False,
                'reasoning': f'室温{indoor_temp}℃が適温範囲内',
                'season': season,
                'time_of_day': time_of_day,
                'discomfort_index': di,
                'night_mode': is_night
            }

    # 春・秋は制御なし（デフォルト）だが、加湿器判定は実施
    humidifier_status = 'on' if indoor_humidity < Config.HUMIDIFIER_START else ('off' if indoor_humidity >= Config.HUMIDIFIER_STOP else 'maintain')

    return {
        'mode': 'none',
        'set_temp': None,
        'circulator': 'off',
        'humidifier': humidifier_status,
        'action': f'{get_season_jp(season)}・制御なし',
        'priority': f'{season}_default',
        'controlled': False,
        'reasoning': f'{get_season_jp(season)}：制御条件なし',
        'season': season,
        'time_of_day': time_of_day,
        'discomfort_index': di,
        'night_mode': is_night
    }


# ===== Notion記録 =====
def log_to_notion(log_data: Dict, aircon_result: Optional[bool] = None) -> bool:
    """Notionにログを記録"""
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
    if control['mode'] == 'none':
        summary = f"制御なし（{get_season_jp(control['season'])}）"
    else:
        temp_str = f" {control['set_temp']}℃" if control.get('set_temp') else ""
        summary = f"{mode_jp}ON{temp_str}"
        if control.get('night_mode'):
            summary += "（夜間）"
        if control.get('priority', '').startswith('emergency'):
            summary += "【緊急】"
        elif control.get('priority', '').startswith('severe'):
            summary += "【重度】"

    # 日本時間（JST = UTC+9）
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    properties = {
        '制御サマリー': {'title': [{'text': {'content': summary}}]},
        '日時': {'date': {'start': now_jst.strftime('%Y-%m-%dT%H:%M:%S+09:00')}},
        '室内温度': {'number': indoor['temperature']},
        '室内湿度': {'number': indoor['humidity']},
        'CO2濃度': {'number': indoor.get('co2')},
        '季節': {'select': {'name': get_season_jp(control['season'])}},
        '時間帯': {'select': {'name': get_time_of_day_jp(control['time_of_day'])}},
        'エアコンモード': {'select': {'name': mode_jp}},
        'サーキュレーター': {'select': {'name': 'ON' if control['circulator'] == 'on' else 'OFF'}},
        '加湿器': {'select': {'name': {'on': 'ON', 'off': 'OFF', 'maintain': '維持'}.get(control.get('humidifier', 'off'), 'OFF')}},
        '制御内容': {'rich_text': [{'text': {'content': control['action'][:2000]}}]},  # 最大2000文字
        '制御根拠': {'rich_text': [{'text': {'content': control['reasoning'][:2000]}}]},
        '制御実行': {'checkbox': control['controlled']},
        '優先度': {'select': {'name': {'emergency': '緊急', 'severe': '重度'}.get(control.get('priority', '').split('_')[0], '通常')}},
        '夜間モード': {'checkbox': control.get('night_mode', False)}
    }

    # API制御結果を記録（制御が実行された場合のみ）
    if aircon_result is not None:
        properties['API制御結果'] = {'select': {'name': '成功' if aircon_result else '失敗'}}

    # 設定温度（ない場合は0）
    properties['設定温度'] = {'number': control.get('set_temp') or 0}

    if outdoor:
        properties['外気温度'] = {'number': outdoor['temperature']}
        properties['外気湿度'] = {'number': outdoor['humidity']}

    # 不快指数を全ての季節で記録
    if control.get('discomfort_index') is not None:
        properties['不快指数'] = {'number': control['discomfort_index']}

        # 季節に応じた評価関数を使用
        season = control.get('season')
        if season == 'spring':
            di_eval = evaluate_comfort_index_spring(control['discomfort_index'])
        elif season == 'summer':
            di_eval = evaluate_discomfort_index(control['discomfort_index'])
        elif season == 'autumn':
            di_eval = evaluate_comfort_index_autumn(control['discomfort_index'])
        else:  # winter
            di_eval = evaluate_comfort_index_winter(control['discomfort_index'])

        properties['不快指数評価'] = {'select': {'name': di_eval['text']}}

    data = {
        'parent': {'type': 'data_source_id', 'data_source_id': Config.NOTION_DATA_SOURCE_ID},
        'properties': properties
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if not response.ok:
            error_detail = response.text[:500]
            print(f"[ERROR] Notion API failed with status {response.status_code}")
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


# ===== Discord通知 =====
async def send_discord_notification(log_data: Dict):
    """Discord通知（古い通知削除 → 新規投稿）"""
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(Config.DISCORD_CHANNEL_ID)

        if not channel:
            print("[ERROR] Discordチャンネルが見つかりません")
            await client.close()
            return

        # 古い通知を全て削除（Botの過去メッセージ全て）
        try:
            deleted_count = 0
            async for message in channel.history(limit=50):
                if message.author.id == client.user.id:
                    await message.delete()
                    deleted_count += 1
            if deleted_count > 0:
                print(f"[INFO] 古いDiscord通知を{deleted_count}件削除しました")
        except Exception as e:
            print(f"[WARN] 古い通知削除エラー: {e}")

        # 新規通知投稿
        control = log_data['control']
        indoor = log_data['indoor']
        outdoor = log_data.get('outdoor')

        embed = discord.Embed(
            title="🌡️ エアコン制御実行",
            description=control['action'],
            color=0x00ff00 if not control['controlled'] else 0xff9900,
            timestamp=datetime.now()
        )

        embed.add_field(name="制御内容", value=control['action'], inline=False)
        embed.add_field(name="時間帯", value=f"{get_time_of_day_jp(control['time_of_day'])}（{datetime.now().strftime('%H:%M')}）", inline=True)
        embed.add_field(name="季節", value=get_season_jp(control['season']), inline=True)
        embed.add_field(name="室内環境", value=f"{indoor['temperature']}℃ / {indoor['humidity']}%", inline=True)

        if outdoor:
            embed.add_field(name="外気環境", value=f"{outdoor['temperature']}℃ / {outdoor['humidity']}%", inline=True)

        if control.get('discomfort_index'):
            di_eval = evaluate_discomfort_index(control['discomfort_index'])
            embed.add_field(name="不快指数", value=f"{control['discomfort_index']} ({di_eval['text']})", inline=True)

        embed.add_field(name="制御根拠", value=control['reasoning'], inline=False)

        await channel.send(embed=embed)
        print("[INFO] Discord通知送信完了")

        await client.close()

    try:
        await client.start(Config.DISCORD_TOKEN)
    except Exception as e:
        print(f"[ERROR] Discord通知エラー: {e}")


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
    print("=== SwitchBot エアコン自動制御システム 開始 ===")
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
        print(f"[INFO] 屋外: {outdoor_data['temperature']}℃ / {outdoor_data['humidity']}%")

    # 2. 制御判定
    control_decision = determine_seasonal_control(indoor_data, outdoor_data)
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

    # 4. サーキュレーター制御実行
    circulator_mode = control_decision.get('circulator', 'off')
    print(f"[INFO] サーキュレーター制御: {circulator_mode}")
    circulator_result = control_circulator(circulator_mode)
    print(f"[INFO] サーキュレーター制御結果: {'成功' if circulator_result else '失敗'}")

    # 5. 加湿器制御実行
    humidifier_mode = control_decision.get('humidifier', 'off')
    print(f"[INFO] 加湿器制御: {humidifier_mode}")
    humidifier_result = control_humidifier(humidifier_mode, indoor_data['humidity'])
    print(f"[INFO] 加湿器制御結果: {'成功' if humidifier_result else '失敗'}")

    # 6. ログデータ作成
    log_data = {
        'indoor': indoor_data,
        'outdoor': outdoor_data,
        'control': control_decision
    }

    # 6. Notion記録（API制御結果を渡す）
    log_to_notion(log_data, aircon_result)

    # 7. Discord通知
    await send_discord_notification(log_data)

    # 8. macOS通知
    send_macos_notification(
        "エアコン制御システム",
        control_decision['action']
    )

    print("=== 制御完了 ===")


if __name__ == '__main__':
    asyncio.run(main())
