#!/usr/bin/env python3
"""
消灯スクリプト
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

SWITCHBOT_TOKEN = os.getenv('SWITCHBOT_TOKEN')
SCENE_ID = "fb6fbf28-5933-4c52-85e1-0b7f99dc54d2"  # 消灯シーン

def light_off():
    """消灯"""
    url = f"https://api.switch-bot.com/v1.1/scenes/{SCENE_ID}/execute"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print("✓ 消灯しました")
    else:
        print(f"✗ エラー: {response.text}")

if __name__ == "__main__":
    light_off()
