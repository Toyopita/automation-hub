#!/usr/bin/env python3
"""
毎朝7時にNotionニュースをIZUMOサーバーの「🤖｜Notion」フォーラムに投稿

フォーラムチャンネルID: 1434339945656487997
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 🤖｜Notion フォーラムチャンネルID（IZUMOサーバー）
NOTION_FORUM_ID = 1434339945656487997

# 投稿履歴ファイル
HISTORY_FILE = '/Users/minamitakeshi/discord-mcp-server/notion_news_history.json'

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def load_history():
    """過去の投稿履歴を読み込む（直近30日分）"""
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

        # 30日より古い履歴を削除
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        history = [item for item in history if item['date'] >= cutoff_date]

        return history
    except:
        return []


def save_history(history, new_items):
    """投稿履歴を保存"""
    today = datetime.now().isoformat()

    for item in new_items:
        history.append({
            'date': today,
            'title': item['title'],
            'url': item['url']
        })

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_history_text(history):
    """履歴を文字列形式で返す（Geminiへの指示用）"""
    if not history:
        return "なし"

    lines = []
    for item in history[-20:]:  # 直近20件
        lines.append(f"- {item['title']}")

    return "\n".join(lines)


async def fetch_notion_news(history):
    """Geminiに最新のNotionニュースを非同期で取得させる"""
    history_text = get_history_text(history)

    prompt = f"""【重要】必ずWeb検索を実行して、最新のNotionに関するニュースを探してください。

【過去に投稿済みのニュース（直近20件）】:
{history_text}

上記と重複しない、完全に新しいニュースのみを選んでください。
**新しいニュースが見つからない場合は、正直に「新しいニュースはありません」と答えてください。**

要件:
- 直近1ヶ月以内の最新ニュース（できるだけ新しいものを優先）
- 以下のカテゴリをバランス良く含める:
  * Notion公式のアップデート、新機能、API更新などの技術的なニュース
  * 企業導入事例（どの企業がNotionを導入したか、活用事例）
  * ビジネス事例、生産性向上事例、組織での活用方法
  * 統合機能、サードパーティツール連携
- 技術的な内容だけでなく、企業の導入ニュースや活用事例も積極的に含める
- 日本語で、かつ日本語ソースがあれば優先（なければ英語ソースでOK）
- 過去に投稿したニュースとタイトルや内容が重複しないこと（最重要）
- **必ずWeb検索を実行**して、実際に存在する記事のURLを取得すること
- URLは実際にアクセス可能な正確なURLであること（架空のURLは絶対NG）
- 新しいニュースが見つかった場合のみ、以下の形式で出力:

---NEWS_START---
タイトル: [ニュースのタイトル]
概要: [2-3文で簡潔な概要]
URL: [ソース元の完全なURL（必須・Web検索で確認済みのURL）]
---NEWS_END---

- 各ニュースは必ず ---NEWS_START--- と ---NEWS_END--- で囲む
- 新しいニュースが見つからない場合は上記形式を使わず、「新しいニュースはありません」とだけ答える"""

    process = await asyncio.create_subprocess_exec(
        '/usr/local/bin/gemini',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate(input=prompt.encode())

    if process.returncode == 0:
        return stdout.decode().strip()
    else:
        return f"ニュース取得エラー: {stderr.decode()}"


async def verify_url(url):
    """URLが実際にアクセス可能か検証"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                return response.status < 400
    except:
        # HEADリクエストが失敗した場合、GETで再試行
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                    return response.status < 400
        except:
            return False


def parse_news(content):
    """Geminiの返答から個別のニュースを抽出"""
    import re

    # ---NEWS_START--- と ---NEWS_END--- で囲まれた部分を抽出
    news_blocks = re.findall(r'---NEWS_START---(.*?)---NEWS_END---', content, re.DOTALL)

    news_list = []
    for block in news_blocks:
        # タイトル、概要、URLを抽出
        title_match = re.search(r'タイトル:\s*(.+)', block)
        summary_match = re.search(r'概要:\s*(.+?)(?=URL:)', block, re.DOTALL)
        url_match = re.search(r'URL:\s*(.+)', block)

        if title_match and summary_match and url_match:
            news_list.append({
                'title': title_match.group(1).strip(),
                'summary': summary_match.group(1).strip(),
                'url': url_match.group(1).strip()
            })

    return news_list


@bot.event
async def on_ready():
    """Bot起動時に実行"""
    print(f'Bot起動: {bot.user}')

    try:
        # フォーラムチャンネルを取得
        forum = bot.get_channel(NOTION_FORUM_ID)
        if not forum:
            print(f'エラー: フォーラムチャンネル（ID: {NOTION_FORUM_ID}）が見つかりません')
            await bot.close()
            return

        print(f'フォーラム: {forum.name}')

        # 投稿履歴を読み込む
        history = load_history()
        print(f'投稿履歴: {len(history)}件')

        # 最新ニュースを非同期で取得
        print('Geminiから最新のNotionニュースを取得中...')
        news_content = await fetch_notion_news(history)

        # ニュースをパース
        news_list = parse_news(news_content)
        print(f'取得したニュース数: {len(news_list)}')

        if len(news_list) == 0:
            print('ℹ️  新しいニュースはありません（投稿をスキップします）')
            await bot.close()
            return

        # URL検証を実行
        print('URL検証中...')
        verified_news = []
        for news in news_list:
            is_valid = await verify_url(news['url'])
            if is_valid:
                verified_news.append(news)
                print(f'  ✅ URL検証OK: {news["url"]}')
            else:
                print(f'  ❌ URL検証NG（除外）: {news["url"]} - {news["title"]}')

        if len(verified_news) == 0:
            print('⚠️  全てのニュースがURL検証に失敗しました（投稿をスキップします）')
            await bot.close()
            return

        print(f'検証済みニュース数: {len(verified_news)}')

        # 各ニュースを個別のスレッドとして投稿
        today = datetime.now().strftime('%Y年%m月%d日')
        posted_count = 0

        for i, news in enumerate(verified_news, 1):
            thread_title = f"{news['title']}"
            thread_content = f"{news['summary']}\n\n**ソース:** {news['url']}"

            print(f'スレッド作成中 ({i}/{len(verified_news)}): {thread_title}')

            thread = await forum.create_thread(
                name=thread_title[:100],  # Discordのタイトル文字数制限対策
                content=thread_content
            )

            print(f'  ✅ 投稿完了: {thread.thread.jump_url}')
            posted_count += 1

            # 連続投稿の間隔を空ける
            await asyncio.sleep(2)

        print(f'\n✅ 全{posted_count}件の投稿完了')

        # 投稿履歴を保存
        save_history(history, verified_news)
        print('投稿履歴を保存しました')

        # macOS通知
        os.system(f'osascript -e \'display notification "{today}のNotionニュース {posted_count}件を投稿しました" with title "Discord Notionニュース"\'')

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
