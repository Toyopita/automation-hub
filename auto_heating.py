#!/usr/bin/env python3
"""
温度監視スクリプト
CO2センサーの温度が22度を下回ったらエアコンの暖房をON
25度以上になったらOFF
"""
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SWITCHBOT_TOKEN = os.getenv('SWITCHBOT_TOKEN')
SWITCHBOT_SECRET = os.getenv('SWITCHBOT_SECRET')

TEMP_SENSOR_ID = "B0E9FE561980"  # CO2センサー（温湿度計）
AC_DEVICE_ID = "02-202404131311-10141115"  # エアコン

LOW_TEMP_THRESHOLD = 22  # この温度を下回ったら暖房ON
HIGH_TEMP_THRESHOLD = 25  # この温度以上になったらOFF
HEATING_TEMP = 25  # 暖房の設定温度

def get_temperature():
    """CO2センサーから温度を取得"""
    import time
    import hashlib
    import hmac
    import base64
    import uuid
    
    token = SWITCHBOT_TOKEN
    secret = SWITCHBOT_SECRET
    nonce = uuid.uuid4()
    t = int(round(time.time() * 1000))
    string_to_sign = '{}{}{}'.format(token, t, nonce)
    
    string_to_sign = bytes(string_to_sign, 'utf-8')
    secret = bytes(secret, 'utf-8')
    
    sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())
    
    headers = {
        'Authorization': token,
        'sign': sign,
        't': str(t),
        'nonce': str(nonce)
    }
    
    response = requests.get(
        f'https://api.switch-bot.com/v1.1/devices/{TEMP_SENSOR_ID}/status',
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['body']['temperature']
    else:
        print(f"❌ 温度取得失敗: {response.status_code}")
        return None

def control_ac(command, temperature=None, mode=None, fan_speed=None):
    """エアコンを制御"""
    import time
    import hashlib
    import hmac
    import base64
    import uuid
    
    token = SWITCHBOT_TOKEN
    secret = SWITCHBOT_SECRET
    nonce = uuid.uuid4()
    t = int(round(time.time() * 1000))
    string_to_sign = '{}{}{}'.format(token, t, nonce)
    
    string_to_sign = bytes(string_to_sign, 'utf-8')
    secret = bytes(secret, 'utf-8')
    
    sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())
    
    headers = {
        'Authorization': token,
        'sign': sign,
        't': str(t),
        'nonce': str(nonce),
        'Content-Type': 'application/json'
    }
    
    # コマンドパラメータを構築
    if command == "turnOn":
        parameter = f"{temperature},1,{mode or '5'},{fan_speed or '1'}"
    else:
        parameter = "default"
    
    payload = {
        "command": command,
        "parameter": parameter,
        "commandType": "command"
    }
    
    response = requests.post(
        f'https://api.switch-bot.com/v1.1/devices/{AC_DEVICE_ID}/commands',
        headers=headers,
        json=payload
    )
    
    return response.status_code == 200

def main():
    temp = get_temperature()
    
    if temp is None:
        print("❌ 温度取得に失敗しました")
        sys.exit(1)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 現在の温度: {temp}°C")
    
    if temp < LOW_TEMP_THRESHOLD:
        print(f"🔥 温度が{LOW_TEMP_THRESHOLD}°Cを下回りました。暖房をONにします（設定温度: {HEATING_TEMP}°C）")
        if control_ac("turnOn", temperature=HEATING_TEMP, mode="5", fan_speed="1"):
            print("✅ 暖房ON成功")
        else:
            print("❌ 暖房ON失敗")
    
    elif temp >= HIGH_TEMP_THRESHOLD:
        print(f"❄️ 温度が{HIGH_TEMP_THRESHOLD}°C以上になりました。エアコンをOFFにします")
        if control_ac("turnOff"):
            print("✅ エアコンOFF成功")
        else:
            print("❌ エアコンOFF失敗")
    
    else:
        print(f"✅ 温度は正常範囲内です（{LOW_TEMP_THRESHOLD}°C ~ {HIGH_TEMP_THRESHOLD}°C）")

if __name__ == "__main__":
    main()
