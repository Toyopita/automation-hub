#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
朝の自動化スクリプト（6:40実行）
宿直の日はスキップする

オプション:
  --force  宿直・休日チェックをスキップして強制実行（正月用）
"""

import os
import sys
import time
import argparse
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# ===== 設定値 =====
class Config:
    # SwitchBot API設定
    SWITCHBOT_TOKEN = os.environ.get('SWITCHBOT_TOKEN')
    SWITCHBOT_API_URL = 'https://api.switch-bot.com/v1.1/devices'

    # デバイスID
    TV_DEVICE_ID = '02-202404131305-88391198'
    LIVING_LIGHT_ID = 'C76B03C65C33'

    # シーンID
    TV_CHANNEL_10_SCENE_ID = 'db53c516-8d11-4e65-a8a5-525f63f554d4'  # 10chを押す

    # Google Calendar設定
    CALENDAR_ID = '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com'


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


def control_tv(command: str, command_type: str = 'command') -> bool:
    """テレビ制御"""
    data = {
        'command': command,
        'commandType': command_type,
        'parameter': 'default'
    }
    result = call_switchbot_api(f"{Config.TV_DEVICE_ID}/commands", 'POST', data)
    return result is not None


def control_light(command: str) -> bool:
    """リビング電気制御"""
    data = {'command': command, 'parameter': 'default', 'commandType': 'command'}
    result = call_switchbot_api(f"{Config.LIVING_LIGHT_ID}/commands", 'POST', data)
    return result is not None


def execute_scene(scene_id: str) -> bool:
    """SwitchBotシーンを実行"""
    url = f"https://api.switch-bot.com/v1.1/scenes/{scene_id}/execute"
    headers = {
        'Authorization': Config.SWITCHBOT_TOKEN,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get('statusCode') == 100:
            return True
        else:
            print(f"[ERROR] Scene execution failed: {result.get('message')}")
            return False
    except Exception as e:
        print(f"[ERROR] Scene execution error: {e}")
        return False


def check_shukuchoku() -> bool:
    """宿直カレンダーをチェックして宿直中かを判定"""
    import subprocess

    try:
        # Node.jsスクリプトを実行
        script_path = os.path.join(os.path.dirname(__file__), 'check_shukuchoku.js')
        result = subprocess.run(['/usr/local/bin/node', script_path], capture_output=True, text=True)

        # 標準出力を表示
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                print(line)

        # exit code 1 = 宿直中, 0 = 宿直なし, 2 = エラー
        if result.returncode == 1:
            return True
        elif result.returncode == 0:
            return False
        else:
            print(f"[ERROR] 宿直チェックでエラーが発生しました（exit code: {result.returncode}）")
            if result.stderr:
                print(result.stderr.strip())
            # エラー時はデフォルトで実行する（False）
            return False

    except Exception as e:
        print(f"[ERROR] 宿直チェックエラー: {e}")
        return False


def check_holiday() -> bool:
    """プライベートカレンダーをチェックして休日かを判定"""
    import subprocess

    try:
        # Node.jsスクリプトを実行
        script_path = os.path.join(os.path.dirname(__file__), 'check_holiday.js')
        result = subprocess.run(['/usr/local/bin/node', script_path], capture_output=True, text=True)

        # 標準出力を表示
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                print(line)

        # exit code 1 = 休日, 0 = 通常日, 2 = エラー
        if result.returncode == 1:
            return True
        elif result.returncode == 0:
            return False
        else:
            print(f"[ERROR] 休日チェックでエラーが発生しました（exit code: {result.returncode}）")
            if result.stderr:
                print(result.stderr.strip())
            # エラー時はデフォルトで実行する（False）
            return False

    except Exception as e:
        print(f"[ERROR] 休日チェックエラー: {e}")
        return False


def is_newyear_period() -> bool:
    """1月1日〜3日（正月期間）かどうかを判定"""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    return now.month == 1 and now.day in [1, 2, 3]


def main():
    """メイン処理"""
    # 引数解析
    parser = argparse.ArgumentParser(description='朝の自動化スクリプト')
    parser.add_argument('--force', action='store_true',
                        help='宿直・休日チェックをスキップして強制実行（正月用）')
    args = parser.parse_args()

    print("=== 朝の自動化スクリプト 開始 ===")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 正月期間（1/1〜1/3）は--forceなしでは実行しない（6:00の正月用が実行されるため）
    if not args.force and is_newyear_period():
        print("[INFO] 🎍 正月期間（1/1〜1/3）のため、通常版はスキップします")
        print("[INFO] 6:00の正月用スクリプトで既に実行済みです")
        print("=== 処理完了（スキップ） ===")
        return

    if args.force:
        print("[INFO] 🎍 強制実行モード（正月用）- 宿直・休日チェックをスキップします")
    else:
        # 1. 宿直チェック
        print("[INFO] 宿直カレンダーをチェック中...")
        is_shukuchoku = check_shukuchoku()

        if is_shukuchoku:
            print("[INFO] 宿直中のため、自動化をスキップします")
            print("=== 処理完了（スキップ） ===")
            return

        print("[INFO] 宿直予定なし")

        # 2. 休日チェック
        print("[INFO] プライベートカレンダーをチェック中...")
        is_holiday = check_holiday()

        if is_holiday:
            print("[INFO] 休日のため、自動化をスキップします")
            print("=== 処理完了（スキップ） ===")
            return

        print("[INFO] 休日予定なし。自動化を実行します")

    # 3. テレビON
    print("[INFO] テレビをONにします...")
    tv_result = control_tv('turnOn')
    print(f"[INFO] テレビ制御結果: {'成功' if tv_result else '失敗'}")

    # 3-2. テレビON後に10chを確実に設定（シーン実行）
    if tv_result:
        print("[INFO] 10秒待機してから10chシーンを実行します...")
        time.sleep(10)

        print("[INFO] 10chシーンを実行中...")
        scene_result = execute_scene(Config.TV_CHANNEL_10_SCENE_ID)
        print(f"[INFO] 10chシーン実行結果: {'成功' if scene_result else '失敗'}")

    # 4. リビング電気ON
    print("[INFO] リビング電気をONにします...")
    light_result = control_light('turnOn')
    print(f"[INFO] リビング電気制御結果: {'成功' if light_result else '失敗'}")

    print("=== 処理完了 ===")


if __name__ == '__main__':
    main()
