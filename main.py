"""
Discord MCP Server
FastAPI + discord.py による MCP プロトコル完全準拠サーバー
"""

import os
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import discord
from discord.ext import commands
import uvicorn
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# Discord Bot設定
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PORT = int(os.getenv("PORT", 8000))

if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN が設定されていません")

# Discord Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# FastAPI初期化
app = FastAPI(title="Discord MCP Server", version="1.0.0")

# Bot起動完了フラグ
bot_ready = False


@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    print(f"Discord Bot logged in as {bot.user}")


# リクエストモデル
class SendMessageRequest(BaseModel):
    channel_id: str
    content: str


class ReadMessagesRequest(BaseModel):
    channel_id: str
    limit: Optional[int] = 10


# MCP Tools定義
@app.get("/tools")
async def list_tools():
    """MCPツール一覧を返す"""
    return {
        "tools": [
            {
                "name": "discord_send_message",
                "description": "指定したDiscordチャンネルにメッセージを送信します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "送信先チャンネルID"
                        },
                        "content": {
                            "type": "string",
                            "description": "送信するメッセージ内容"
                        }
                    },
                    "required": ["channel_id", "content"]
                }
            },
            {
                "name": "discord_read_messages",
                "description": "指定したDiscordチャンネルの最新メッセージを取得します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "読み取り対象チャンネルID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "取得するメッセージ数（デフォルト: 10）",
                            "default": 10
                        }
                    },
                    "required": ["channel_id"]
                }
            }
        ]
    }


@app.post("/tools/discord_send_message")
async def send_message(request: SendMessageRequest):
    """Discordチャンネルにメッセージを送信"""
    if not bot_ready:
        raise HTTPException(status_code=503, detail="Discord Bot is not ready")

    try:
        channel = bot.get_channel(int(request.channel_id))
        if not channel:
            raise HTTPException(status_code=404, detail=f"Channel {request.channel_id} not found")

        await channel.send(request.content)

        return {
            "success": True,
            "channel_id": request.channel_id,
            "message": "Message sent successfully"
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel_id format")
    except discord.Forbidden:
        raise HTTPException(status_code=403, detail="Bot lacks permission to send messages")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/tools/discord_read_messages")
async def read_messages(request: ReadMessagesRequest):
    """Discordチャンネルの最新メッセージを取得"""
    if not bot_ready:
        raise HTTPException(status_code=503, detail="Discord Bot is not ready")

    try:
        channel = bot.get_channel(int(request.channel_id))
        if not channel:
            raise HTTPException(status_code=404, detail=f"Channel {request.channel_id} not found")

        messages = []
        async for msg in channel.history(limit=request.limit):
            messages.append({
                "id": str(msg.id),
                "author": str(msg.author),
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "attachments": [att.url for att in msg.attachments]
            })

        return {
            "success": True,
            "channel_id": request.channel_id,
            "messages": messages,
            "count": len(messages)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel_id format")
    except discord.Forbidden:
        raise HTTPException(status_code=403, detail="Bot lacks permission to read messages")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/")
async def root():
    """ヘルスチェック"""
    return {
        "service": "Discord MCP Server",
        "status": "running",
        "bot_ready": bot_ready,
        "bot_user": str(bot.user) if bot_ready else None
    }


async def start_bot():
    """Discord Botを起動"""
    await bot.start(DISCORD_BOT_TOKEN)


async def start_server():
    """FastAPIサーバーを起動"""
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Bot と FastAPI サーバーを並行起動"""
    await asyncio.gather(
        start_bot(),
        start_server()
    )


if __name__ == "__main__":
    asyncio.run(main())
