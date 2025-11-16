#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
夜間自動化スクリプト（21:00実行）
リビング電気を自動でOFFにする
"""

import os
import sys
import requests
import subprocess
from datetime import datetime
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
    LIVING_LIGHT_ID = 'C76B03C65C33'


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


def control_light(command: str) -> bool:
    """リビング電気制御"""
    data = {'command': command, 'parameter': 'default', 'commandType': 'command'}
    result = call_switchbot_api(f"{Config.LIVING_LIGHT_ID}/commands", 'POST', data)
    return result is not None


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


def main():
    """メイン処理"""
    print("=== 夜間自動化スクリプト 開始 ===")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # リビング電気OFF
    print("[INFO] リビング電気をOFFにします...")
    light_result = control_light('turnOff')

    if light_result:
        print(f"[INFO] リビング電気制御結果: 成功")
        send_macos_notification(
            "夜間自動化",
            "リビング電気をOFFにしました（21:00）"
        )
    else:
        print(f"[ERROR] リビング電気制御結果: 失敗")
        send_macos_notification(
            "夜間自動化エラー",
            "リビング電気のOFF制御に失敗しました"
        )

    print("=== 処理完了 ===")


if __name__ == '__main__':
    main()
