#!/usr/bin/env python3
"""
Discord ⇒ MacBook ⇒ AI ―― 書籍フォーラムAI応答Bot

Minamiサーバーの「書籍フォーラム」で、
「@claude」または「claude」を含む投稿に自動返信します。

書籍フォーラムID: 1433964655172124742
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict, List
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOOK_FORUM_CHANNEL_ID = 1433964655172124742

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 処理済みメッセージIDを記録（重複防止）
processed_messages = set()


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[書籍Bot][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg, flush=True)


async def get_thread_context(thread: discord.Thread, limit: int = 10) -> str:
    """
    スレッドの過去の投稿を取得して文脈を構築

    Args:
        thread: Discordスレッド
        limit: 取得する過去メッセージ数

    Returns:
        文脈文字列
    """
    try:
        messages = []
        async for msg in thread.history(limit=limit, oldest_first=True):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")

        context = "\n".join(messages)
        log('DEBUG', 'スレッド文脈取得', {'messages_count': len(messages)})
        return context

    except Exception as e:
        log('ERROR', 'スレッド文脈取得エラー', {'error': str(e)})
        return ""


def ask_ai(question: str, context: str, book_title: str) -> str:
    """
    AIに質問を投げて返答を取得

    Args:
        question: ユーザーの質問
        context: スレッドの文脈
        book_title: 書籍タイトル

    Returns:
        AIの返答
    """
    try:
        # Geminiに質問を投げる
        prompt = f"""あなたは書籍「{book_title}」についての読書支援AIです。

【これまでの会話】
{context}

【質問】
{question}

【回答ルール】
- 簡潔に、3-5文程度で答えてください
- 書籍の内容に関する質問には、一般的な知識で答えてください
- 読書メモへのコメントは共感や補足を示してください
- 要約リクエストには、会話履歴から重要なポイントを抽出してください
"""

        # geminiコマンドを-pオプションで直接呼び出し
        result = subprocess.run(
            ['/usr/local/bin/gemini', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=900  # 15分
        )

        if result.returncode == 0:
            response = result.stdout.strip()
            # MCP STDERRなどのノイズを除去
            lines = response.split('\n')
            clean_lines = [line for line in lines if not line.startswith('MCP STDERR') and line.strip()]
            clean_response = '\n'.join(clean_lines).strip()

            log('SUCCESS', 'AI返答取得成功', {'length': len(clean_response)})
            return clean_response
        else:
            log('ERROR', 'gemini実行失敗', {'error': result.stderr})
            return "申し訳ありません、現在応答できません。"

    except subprocess.TimeoutExpired:
        log('ERROR', 'geminiタイムアウト')
        return "処理に時間がかかっています。もう一度お試しください。"
    except Exception as e:
        log('ERROR', 'AI質問例外', {'error': str(e)})
        return "エラーが発生しました。"


@bot.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {bot.user}')
    log('INFO', f'書籍フォーラム監視開始: {BOOK_FORUM_CHANNEL_ID}')


@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # 書籍フォーラム以外のメッセージは無視
    if not isinstance(message.channel, discord.Thread):
        return

    if message.channel.parent_id != BOOK_FORUM_CHANNEL_ID:
        return

    # 重複処理防止
    if message.id in processed_messages:
        return

    log('DEBUG', '書籍フォーラムにメッセージ受信', {
        'author': str(message.author),
        'thread': message.channel.name,
        'content': message.content[:100]
    })

    # トリガー検出（Botメンション、または「claude」テキスト）
    is_mentioned = bot.user.mentioned_in(message)
    content_lower = message.content.lower()
    has_claude_text = 'claude' in content_lower

    if not is_mentioned and not has_claude_text:
        processed_messages.add(message.id)
        return

    log('INFO', 'トリガー検出', {'mentioned': is_mentioned, 'text': has_claude_text, 'content': message.content[:100]})

    # スレッドタイトル（書籍名）を取得
    book_title = message.channel.name

    # スレッドの文脈を取得
    context = await get_thread_context(message.channel, limit=10)

    # ユーザーの質問（メンションと「claude」を除去）
    question = message.content
    # Botメンションを除去
    for mention in message.mentions:
        question = question.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
    # 「claude」テキストを除去
    question = question.replace('@claude', '').replace('claude', '').strip()

    # AIに質問
    log('INFO', 'AI質問開始', {'book': book_title, 'question': question[:50]})
    response = ask_ai(question, context, book_title)

    # 返信を投稿
    try:
        await message.reply(response, mention_author=False)
        log('SUCCESS', 'AI返答投稿完了', {'book': book_title})
    except Exception as e:
        log('ERROR', '返答投稿失敗', {'error': str(e)})

    # 処理済みとして記録
    processed_messages.add(message.id)

    # コマンド処理を継続
    await bot.process_commands(message)


if __name__ == "__main__":
    log('INFO', '書籍フォーラムBot起動中...')
    bot.run(DISCORD_TOKEN)
