#!/usr/bin/env python3
"""
点灯スクリプト
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

SWITCHBOT_TOKEN = os.getenv('SWITCHBOT_TOKEN')
SCENE_ID = "b8148402-f873-486b-b808-7c2df2735abb"  # 点灯シーン

def light_on():
    """点灯"""
    url = f"https://api.switch-bot.com/v1.1/scenes/{SCENE_ID}/execute"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print("✓ 点灯しました")
    else:
        print(f"✗ エラー: {response.text}")

if __name__ == "__main__":
    light_on()
