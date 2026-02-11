#!/usr/bin/env python3
"""
Michelle 自律型LINE Chat Bot

auto_chat_bot.py の汎用エンジンに michelle_config.json を渡すラッパー。
既存のlaunchd設定との互換性を維持するために残してある。

起動:
  python3 michelle_auto_bot.py
  (内部的には python3 auto_chat_bot.py --config michelle_config.json と同等)
"""

from pathlib import Path
from auto_chat_bot import load_config, AutoChatBot
import asyncio


def main():
    config_path = Path(__file__).parent / 'michelle_config.json'
    config = load_config(str(config_path))
    bot = AutoChatBot(config)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
