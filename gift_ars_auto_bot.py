#!/usr/bin/env python3
"""
Gift_ars 自律型LINE Chat Bot

auto_chat_bot.py の汎用エンジンに gift_ars_config.json を渡すラッパー。

起動:
  python3 gift_ars_auto_bot.py
"""

from pathlib import Path
from auto_chat_bot import load_config, AutoChatBot
import asyncio


def main():
    config_path = Path(__file__).parent / 'gift_ars_config.json'
    config = load_config(str(config_path))
    bot = AutoChatBot(config)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
