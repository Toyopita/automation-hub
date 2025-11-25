#!/usr/bin/env python3
"""
祖霊社ディスクプレーヤー 再生スクリプト
"""
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

SWITCHBOT_TOKEN = os.getenv('SWITCHBOT_TOKEN')
SCENE_ID = "41e4f462-8d53-40c3-a535-c7945715ec3c"  # 再生シーン

def play_music():
    """音楽を再生"""
    url = f"https://api.switch-bot.com/v1.1/scenes/{SCENE_ID}/execute"
    headers = {
        "Authorization": SWITCHBOT_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        print("✓ 音楽再生を開始しました")
    else:
        print(f"✗ エラー: {response.text}")

if __name__ == "__main__":
    play_music()
