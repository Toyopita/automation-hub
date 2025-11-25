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
SCENE_ID = "a7f7434f-19d3-448b-ba96-734d29bb90a2"  # 停止シーン

def stop_music():
    """音楽を停止"""
    url = f"https://api.switch-bot.com/v1.1/scenes/{SCENE_ID}/execute"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print("✓ 音楽を停止しました")
    else:
        print(f"✗ エラー: {response.text}")

if __name__ == "__main__":
    stop_music()
