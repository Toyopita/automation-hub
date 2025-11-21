#!/usr/bin/env python3
"""
launchd設定の整合性チェック

毎日実行して、launchd設定が参照しているファイルが存在するか確認
問題があればDiscordに通知
"""

import os
import glob
import xml.etree.ElementTree as ET
import asyncio
import discord
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_CHANNEL_ID = 1437603269307535484  # エアコン制御ログチャンネル

def check_launchd_files():
    """launchd設定ファイルをチェック"""
    plist_dir = os.path.expanduser('~/Library/LaunchAgents')
    plist_files = glob.glob(f'{plist_dir}/com.discord.*.plist')
    
    missing_files = []
    
    for plist_file in plist_files:
        try:
            tree = ET.parse(plist_file)
            root = tree.getroot()
            
            # ProgramArgumentsを探す
            dict_elem = root.find('dict')
            keys = dict_elem.findall('key')
            
            for i, key in enumerate(keys):
                if key.text == 'ProgramArguments':
                    array_elem = dict_elem[i+1]
                    if array_elem.tag == 'array':
                        strings = array_elem.findall('string')
                        if len(strings) >= 2:
                            script_path = strings[1].text
                            
                            # ファイルが存在するかチェック
                            if not os.path.exists(script_path):
                                plist_name = os.path.basename(plist_file)
                                missing_files.append({
                                    'plist': plist_name,
                                    'missing_path': script_path
                                })
        except Exception as e:
            print(f"Error checking {plist_file}: {e}")
    
    return missing_files

async def send_discord_notification(missing_files):
    """Discordに通知"""
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(ADMIN_CHANNEL_ID)
            
            if missing_files:
                message = "⚠️ **launchd設定エラー検出**\n\n"
                message += f"以下の{len(missing_files)}件のlaunchd設定が存在しないファイルを参照しています：\n\n"
                
                for item in missing_files[:10]:  # 最大10件
                    message += f"• `{item['plist']}`\n"
                    message += f"  参照先: `{item['missing_path']}`\n\n"
                
                if len(missing_files) > 10:
                    message += f"...他{len(missing_files) - 10}件\n\n"
                
                message += "修正が必要です。Claude Codeに確認を依頼してください。"
                
                await channel.send(message)
                print(f"✅ Discord通知送信完了（{len(missing_files)}件の問題）")
            else:
                print("✅ すべてのlaunchd設定が正常です")
                
        except Exception as e:
            print(f"❌ Discord通知エラー: {e}")
        finally:
            await client.close()
    
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    print("=== launchd整合性チェック開始 ===")
    missing = check_launchd_files()
    
    if missing:
        print(f"⚠️ {len(missing)}件の問題を検出")
        asyncio.run(send_discord_notification(missing))
    else:
        print("✅ 問題なし")
