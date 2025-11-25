#!/usr/bin/env python3
"""
祖霊社ディスクプレーヤー 停止スクリプト
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

SWITCHBOT_TOKEN = os.getenv('SWITCHBOT_TOKEN')
DEVICE_ID = "02-202506171446-61222081"

def stop_music():
    """音楽を停止"""
    url = f"https://api.switch-bot.com/v1.1/devices/{DEVICE_ID}/commands"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "command": "Stop",
        "parameter": "default",
        "commandType": "command"
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        print("✓ 音楽を停止しました")
    else:
        print(f"✗ エラー: {response.text}")

if __name__ == "__main__":
    stop_music()
