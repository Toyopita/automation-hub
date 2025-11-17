#!/usr/bin/env python3
"""
毎朝7時に生成AIニュースをIZUMOサーバーの「🤖｜生成AI」フォーラムに投稿

Google News RSSを使用（完全無料・API key不要）
フォーラムチャンネルID: 1434340159389700157
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import feedparser

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 🤖｜生成AI フォーラムチャンネルID（IZUMOサーバー）
GENAI_FORUM_ID = 1434340159389700157

# 投稿履歴ファイル
HISTORY_FILE = '/Users/minamitakeshi/discord-mcp-server/genai_news_history.json'

# Google News RSS URL（日本語の生成AIニュース）
GOOGLE_NEWS_RSS = 'https://news.google.com/rss/search?q=生成AI OR ChatGPT OR Claude OR Gemini OR 人工知能 OR AI&hl=ja&gl=JP&ceid=JP:ja'

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


def is_duplicate(title, url, history):
    """履歴と重複しているか確認"""
    for item in history:
        # URLが完全一致
        if item['url'] == url:
            return True
        # タイトルの類似度が高い（70%以上の単語一致）
        title_words = set(title.split())
        history_words = set(item['title'].split())
        if title_words and history_words:
            similarity = len(title_words & history_words) / len(title_words | history_words)
            if similarity > 0.7:
                return True
    return False


async def fetch_google_news():
    """Google News RSSから最新ニュースを取得"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GOOGLE_NEWS_RSS, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    rss_content = await response.text()
                    return rss_content
                else:
                    print(f'RSS取得エラー: ステータスコード {response.status}')
                    return None
    except Exception as e:
        print(f'RSS取得エラー: {e}')
        return None


def parse_rss(rss_content):
    """RSSコンテンツをパースしてニュースリストを返す"""
    feed = feedparser.parse(rss_content)
    news_list = []

    for entry in feed.entries[:20]:  # 最新20件まで取得
        # Google NewsのRSSはentryにtitle, link, published, summaryを含む
        title = entry.get('title', '')
        url = entry.get('link', '')
        summary = entry.get('summary', entry.get('description', ''))
        published = entry.get('published', '')

        # Google NewsのリンクからオリジナルURLを抽出
        # Google Newsはリダイレクトを使うため、実際のURLを取得
        if url:
            news_list.append({
                'title': title,
                'summary': summary[:200] if summary else 'ニュース概要なし',
                'url': url,
                'published': published
            })

    return news_list


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


@bot.event
async def on_ready():
    """Bot起動時に実行"""
    print(f'Bot起動: {bot.user}')

    try:
        # フォーラムチャンネルを取得
        forum = bot.get_channel(GENAI_FORUM_ID)
        if not forum:
            print(f'エラー: フォーラムチャンネル（ID: {GENAI_FORUM_ID}）が見つかりません')
            await bot.close()
            return

        print(f'フォーラム: {forum.name}')

        # 投稿履歴を読み込む
        history = load_history()
        print(f'投稿履歴: {len(history)}件')

        # Google News RSSから最新ニュースを取得
        print('Google News RSSから生成AIニュースを取得中...')
        rss_content = await fetch_google_news()

        if not rss_content:
            print('❌ RSS取得に失敗しました')
            await bot.close()
            return

        # RSSをパース
        news_list = parse_rss(rss_content)
        print(f'RSS取得ニュース数: {len(news_list)}')

        if len(news_list) == 0:
            print('ℹ️  ニュースが見つかりませんでした')
            await bot.close()
            return

        # 重複を除外
        print('重複チェック中...')
        unique_news = []
        for news in news_list:
            if not is_duplicate(news['title'], news['url'], history):
                unique_news.append(news)
                print(f'  ✅ 新規: {news["title"][:50]}...')
            else:
                print(f'  ⏭️  重複（スキップ）: {news["title"][:50]}...')

        if len(unique_news) == 0:
            print('ℹ️  新しいニュースはありません（投稿をスキップします）')
            await bot.close()
            return

        print(f'新規ニュース数: {len(unique_news)}')

        # 最新5件のみに絞る
        unique_news = unique_news[:5]
        print(f'投稿対象: {len(unique_news)}件')

        # URL検証を実行
        print('URL検証中...')
        verified_news = []
        for news in unique_news:
            is_valid = await verify_url(news['url'])
            if is_valid:
                verified_news.append(news)
                print(f'  ✅ URL検証OK: {news["url"][:60]}...')
            else:
                print(f'  ❌ URL検証NG（除外）: {news["url"][:60]}...')

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
            thread_content = f"""📰 **ニュース概要**
{news['summary']}

---
🔗 **記事を読む:** {news['url']}
"""

            print(f'スレッド作成中 ({i}/{len(verified_news)}): {thread_title[:50]}...')

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
        os.system(f'osascript -e \'display notification "{today}の生成AIニュース {posted_count}件を投稿しました（Google News RSS使用）" with title "Discord生成AIニュース"\'')

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
