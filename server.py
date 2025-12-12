import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from fastmcp import FastMCP

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKENが.envファイルに設定されていません。")

# FastMCP のインスタンス化
mcp = FastMCP("Discord MCP Server")

# Discord bot のインスタンス作成
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Bot起動フラグ
bot_started = False

@mcp.tool()
async def send_message(channel_id: str, message: str) -> dict:
    """
    指定されたチャンネルIDにDiscordメッセージを送信します。

    Args:
        channel_id: メッセージを送信するDiscordチャンネルのID
        message: 送信するメッセージ本文
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            # スレッドの場合はfetchで取得
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except:
                return {"status": "error", "message": f"Channel with ID {channel_id} not found."}

        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            await channel.send(message)
            return {"status": "success", "message": f"Sent '{message}' to channel {channel_id}"}
        else:
            return {"status": "error", "message": f"Channel with ID {channel_id} is not a text channel or thread."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def get_bot_status() -> dict:
    """
    Discordボットの現在のステータス（レイテンシ、所属サーバー数）を返します。
    """
    if not bot.is_ready():
        return {"status": "Bot is not ready yet."}

    return {
        "status": "online",
        "latency_ms": round(bot.latency * 1000, 2),
        "guild_count": len(bot.guilds),
    }

@mcp.tool()
async def midjourney_imagine(channel_id: str, prompt: str) -> dict:
    """
    Midjourneyで画像を生成します。/imagineコマンドを実行します。

    Args:
        channel_id: Midjourneyが利用可能なDiscordチャンネルのID
        prompt: Midjourneyに渡す画像生成プロンプト（パラメータを含む全体）
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    try:
        channel = bot.get_channel(int(channel_id))
        if channel and isinstance(channel, discord.TextChannel):
            # Midjourneyの/imagineコマンドを送信
            message = f"/imagine prompt: {prompt}"
            await channel.send(message)
            return {
                "status": "success",
                "message": f"Midjourney imagine command sent to channel {channel_id}",
                "prompt": prompt
            }
        else:
            return {"status": "error", "message": f"Channel with ID {channel_id} not found or is not a text channel."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_channels() -> dict:
    """
    Botがアクセスできる全てのDiscordチャンネルをリスト表示します。
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    channels = []
    for guild in bot.guilds:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append({
                    "guild_name": guild.name,
                    "channel_name": channel.name,
                    "channel_id": str(channel.id)
                })

    return {"status": "success", "channels": channels}

@mcp.tool()
async def fetch_messages(channel_id: str, limit: int = 50) -> dict:
    """
    指定されたチャンネルから最新のメッセージ履歴を取得します。

    Args:
        channel_id: メッセージを取得するDiscordチャンネルのID
        limit: 取得するメッセージ数（デフォルト: 50、最大: 100）
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    # limitの上限チェック
    if limit > 100:
        limit = 100

    try:
        channel = bot.get_channel(int(channel_id))
        if not channel:
            # スレッドの場合はfetchで取得
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except:
                return {"status": "error", "message": f"Channel with ID {channel_id} not found."}

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return {"status": "error", "message": f"Channel with ID {channel_id} is not a text channel or thread."}

        # メッセージ履歴を取得（新しい順）
        messages = []
        async for message in channel.history(limit=limit):
            messages.append({
                "message_id": str(message.id),
                "author": str(message.author),
                "author_id": str(message.author.id),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "attachments": [att.url for att in message.attachments] if message.attachments else []
            })

        return {
            "status": "success",
            "channel_id": channel_id,
            "channel_name": channel.name,
            "message_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def create_forum_channel(category_id: str, channel_name: str) -> dict:
    """
    指定されたカテゴリ内に新しいフォーラムチャンネルを作成します。

    Args:
        category_id: カテゴリのID
        channel_name: 作成するフォーラムチャンネル名
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    try:
        category = bot.get_channel(int(category_id))
        if not category:
            return {"status": "error", "message": f"Category with ID {category_id} not found."}

        if not isinstance(category, discord.CategoryChannel):
            return {"status": "error", "message": f"Channel {category_id} is not a category."}

        # フォーラムチャンネルを作成
        forum_channel = await category.guild.create_forum(
            name=channel_name,
            category=category
        )

        return {
            "status": "success",
            "message": f"Forum channel '{channel_name}' created successfully",
            "channel_id": str(forum_channel.id),
            "channel_name": forum_channel.name,
            "category_name": category.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def create_forum_thread(forum_id: str, thread_title: str, first_message: str) -> dict:
    """
    Discordフォーラムに新しいスレッドを作成します。

    Args:
        forum_id: フォーラムチャンネルのID
        thread_title: スレッドのタイトル
        first_message: 最初のメッセージ内容
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    try:
        forum_channel = bot.get_channel(int(forum_id))
        if not forum_channel:
            return {"status": "error", "message": f"Forum channel with ID {forum_id} not found."}

        if not isinstance(forum_channel, discord.ForumChannel):
            return {"status": "error", "message": f"Channel {forum_id} is not a forum channel."}

        # フォーラムに新しいスレッドを作成
        thread_with_message = await forum_channel.create_thread(
            name=thread_title,
            content=first_message
        )

        thread = thread_with_message.thread

        return {
            "status": "success",
            "message": f"Forum thread created successfully",
            "thread_id": str(thread.id),
            "thread_name": thread.name,
            "thread_url": f"https://discord.com/channels/{forum_channel.guild.id}/{thread.id}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_forum_threads(forum_id: str) -> dict:
    """
    フォーラムチャンネルのスレッド一覧を取得します。

    Args:
        forum_id: フォーラムチャンネルのID
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    try:
        forum_channel = bot.get_channel(int(forum_id))
        if not forum_channel:
            return {"status": "error", "message": f"Forum channel with ID {forum_id} not found."}

        if not isinstance(forum_channel, discord.ForumChannel):
            return {"status": "error", "message": f"Channel {forum_id} is not a forum channel."}

        threads = []

        # アクティブなスレッドを取得
        for thread in forum_channel.threads:
            threads.append({
                "thread_id": str(thread.id),
                "thread_name": thread.name,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "archived": thread.archived,
                "locked": thread.locked,
                "message_count": thread.message_count,
                "thread_url": f"https://discord.com/channels/{forum_channel.guild.id}/{thread.id}"
            })

        # アーカイブされたスレッドも取得
        async for thread in forum_channel.archived_threads(limit=50):
            threads.append({
                "thread_id": str(thread.id),
                "thread_name": thread.name,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "archived": thread.archived,
                "locked": thread.locked,
                "message_count": thread.message_count,
                "thread_url": f"https://discord.com/channels/{forum_channel.guild.id}/{thread.id}"
            })

        return {
            "status": "success",
            "forum_id": forum_id,
            "forum_name": forum_channel.name,
            "thread_count": len(threads),
            "threads": threads
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def create_category(guild_id: str, category_name: str) -> dict:
    """
    指定されたサーバー（ギルド）に新しいカテゴリを作成します。

    Args:
        guild_id: サーバー（ギルド）のID
        category_name: 作成するカテゴリ名
    """
    global bot_started

    # Botがまだ起動していない場合は起動
    if not bot_started:
        import asyncio
        asyncio.create_task(bot.start(TOKEN))
        bot_started = True
        # Bot接続を待つ
        await asyncio.sleep(3)

    if not bot.is_ready():
        return {"status": "error", "message": "Bot is not ready yet."}

    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            return {"status": "error", "message": f"Guild with ID {guild_id} not found."}

        # カテゴリを作成
        category = await guild.create_category(name=category_name)

        return {
            "status": "success",
            "message": f"Category '{category_name}' created successfully",
            "category_id": str(category.id),
            "category_name": category.name,
            "guild_name": guild.name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
