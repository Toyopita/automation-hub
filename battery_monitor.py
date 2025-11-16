#!/usr/bin/env python3
"""
SwitchBotデバイスの電池残量を監視し、10%以下になったら通知
毎日1回実行
SwitchBot API v1.0を使用（トークンのみ）
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SWITCHBOT_TOKEN = os.getenv("SWITCHBOT_TOKEN")

# 通知先チャンネル（お知らせチャンネル）
NOTIFICATION_CHANNEL_ID = 1434340159389700156  # 📢｜お知らせ

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def get_switchbot_devices():
    """SwitchBotデバイス一覧を取得（API v1.0）"""
    headers = {
        'Authorization': SWITCHBOT_TOKEN,
        'Content-Type': 'application/json; charset=utf8'
    }
    
    response = requests.get('https://api.switch-bot.com/v1.0/devices', headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('body', {}).get('deviceList', [])
    return []


def get_device_status(device_id):
    """デバイスのステータスを取得（API v1.0）"""
    headers = {
        'Authorization': SWITCHBOT_TOKEN,
        'Content-Type': 'application/json; charset=utf8'
    }
    
    response = requests.get(f'https://api.switch-bot.com/v1.0/devices/{device_id}/status', headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('body', {})
    return {}


@bot.event
async def on_ready():
    """Bot起動時に実行"""
    print(f'Bot起動: {bot.user}')
    
    try:
        # デバイス一覧取得
        devices = get_switchbot_devices()
        print(f'デバイス数: {len(devices)}')
        
        low_battery_devices = []
        
        # 各デバイスの電池残量をチェック
        for device in devices:
            device_id = device.get('deviceId')
            device_name = device.get('deviceName')
            device_type = device.get('deviceType')
            
            # ステータス取得
            status = get_device_status(device_id)
            battery = status.get('battery')
            
            if battery is not None:
                print(f'{device_name} ({device_type}): {battery}%')
                
                # 10%以下の場合
                if battery <= 10:
                    low_battery_devices.append({
                        'name': device_name,
                        'type': device_type,
                        'battery': battery
                    })
        
        # 10%以下のデバイスがあれば通知
        if low_battery_devices:
            # Discord通知
            channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
            if channel:
                message = "🔋 **SwitchBot電池残量警告**\n\n以下のデバイスの電池残量が10%以下です：\n\n"
                for device in low_battery_devices:
                    message += f"⚠️ **{device['name']}** ({device['type']}): {device['battery']}%\n"
                message += "\n電池交換が必要です。"
                
                await channel.send(message)
                print(f'✅ Discord通知送信完了: {len(low_battery_devices)}件')
            
            # macOS通知
            device_names = ", ".join([d['name'] for d in low_battery_devices])
            os.system(f'osascript -e \'display notification "電池残量10%以下: {device_names}" with title "SwitchBot電池警告"\'')
            
        else:
            print('✅ 全デバイス正常（電池残量10%以上）')
    
    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()
    
    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
