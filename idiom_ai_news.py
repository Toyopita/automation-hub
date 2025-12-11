#!/usr/bin/env python3
"""
毎時IdiomサーバーのGoogle News RSSを使用して生成AIニュースを「🤖｜生成AI」フォーラムに投稿

Google News RSSを使用（完全無料・API key不要）
フォーラムチャンネルID: 1448462407763628274
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands
import aiohttp
import feedparser
import re
from html import unescape

# .envファイルを直接読み込み
env_vars = {}
env_path = '/Users/minamitakeshi/discord-mcp-server/.env'
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value

DISCORD_TOKEN = env_vars.get("DISCORD_TOKEN")

# 🤖｜生成AI フォーラムチャンネルID（Idiomサーバー）
GENAI_FORUM_ID = 1448462407763628274

# 投稿履歴ファイル（Idiom専用）
HISTORY_FILE = '/Users/minamitakeshi/discord-mcp-server/idiom_genai_news_history.json'

# Google News RSS URL（日本語の生成AIニュース）
GOOGLE_NEWS_RSS = 'https://news.google.com/rss/search?q=生成AI OR ChatGPT OR Claude OR Gemini OR 人工知能 OR AI OR DeepMind OR OpenAI OR Anthropic&hl=ja&gl=JP&ceid=JP:ja'

# 信頼できる日本語メディア名のリスト（タイトルやsummaryに含まれる文字列で判定）
TRUSTED_MEDIA_NAMES = [
    '日本経済新聞',
    '日経',
    'ITmedia',
    'CNET Japan',
    'CNET',
    'ギズモード',
    'Gizmodo',
    'WIRED',
    'Impress Watch',
    'PC Watch',
    'ASCII.jp',
    'ASCII',
    'ZDNet Japan',
    'ZDNet',
    'TechCrunch',
    'PR TIMES',
    'マイナビニュース',
    'マイナビ',
    'Engadget',
    'Notion',
    'Google',
    'OpenAI',
    'Anthropic',
]

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

        # 30日より古い履歴を削除（日本時間）
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        cutoff_date = (now - timedelta(days=30)).isoformat()
        history = [item for item in history if item['date'] >= cutoff_date]

        return history
    except:
        return []


def save_history(history, new_items):
    """投稿履歴を保存"""
    today = datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

    for item in new_items:
        history.append({
            'date': today,
            'title': item['title'],
            'url': item['url']
        })

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_trusted_source(title, summary):
    """タイトルまたは要約に信頼できるメディア名が含まれているかチェック"""
    combined_text = f"{title} {summary}"
    for media_name in TRUSTED_MEDIA_NAMES:
        if media_name in combined_text:
            return True
    return False


def is_duplicate(title, url, history):
    """履歴と重複しているか確認"""
    for item in history:
        # URLが完全一致
        if item['url'] == url:
            return True
        # タイトルの類似度が高い（80%以上の単語一致）
        title_words = set(title.split())
        history_words = set(item['title'].split())
        if title_words and history_words:
            similarity = len(title_words & history_words) / len(title_words | history_words)
            if similarity > 0.8:
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


def remove_html_tags(text):
    """HTMLタグを除去してプレーンテキストを返す"""
    if not text:
        return ''

    # HTMLエンティティをデコード（&lt; → <）
    text = unescape(text)

    # HTMLタグを全て除去
    text = re.sub(r'<[^>]+>', '', text)

    # 連続する空白を1つにまとめる
    text = re.sub(r'\s+', ' ', text)

    # 前後の空白を削除
    text = text.strip()

    return text


def parse_rss(rss_content):
    """RSSコンテンツをパースしてニュースリストを返す"""
    feed = feedparser.parse(rss_content)
    news_list = []

    # Google Newsの自然な順序を信頼（日付フィルタなし）
    # 重複チェック（30日履歴）で古いニュースは自動的に除外される
    for entry in feed.entries[:50]:  # 最新50件まで取得（より多くから選別）
        # Google NewsのRSSはentryにtitle, link, published, summaryを含む
        title = entry.get('title', '')
        url = entry.get('link', '')
        summary = entry.get('summary', entry.get('description', ''))
        published = entry.get('published', '')

        # HTMLタグを除去
        title = remove_html_tags(title)
        summary = remove_html_tags(summary)

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
    """URLが実際にアクセス可能か検証し、オリジナルURLを返す"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                return (response.status < 400, str(response.url))
    except:
        # HEADリクエストが失敗した場合、GETで再試行
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as response:
                    return (response.status < 400, str(response.url))
        except:
            return (False, url)


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

        # 先にURL検証を実行してオリジナルURLを取得（重複チェックの精度向上のため）
        print('URL検証＆オリジナルURL取得中...')
        verified_news = []
        for news in news_list:
            is_valid, original_url = await verify_url(news['url'])
            if is_valid:
                news['url'] = original_url  # オリジナルURLに置き換え
                verified_news.append(news)
                print(f'  ✅ URL検証OK: {original_url[:60]}...')
            else:
                print(f'  ❌ URL検証NG（除外）: {news["url"][:60]}...')

        if len(verified_news) == 0:
            print('⚠️  全てのニュースがURL検証に失敗しました（投稿をスキップします）')
            await bot.close()
            return

        print(f'検証済みニュース数: {len(verified_news)}')

        # 信頼できる情報源のみにフィルタリング
        print('信頼できる情報源のフィルタリング中...')
        trusted_news = []
        for news in verified_news:
            if is_trusted_source(news['title'], news['summary']):
                trusted_news.append(news)
                print(f'  ✅ 信頼できる情報源: {news["title"][:50]}...')
            else:
                print(f'  ⏭️  除外（信頼できない情報源）: {news["title"][:50]}...')

        if len(trusted_news) == 0:
            print('ℹ️  信頼できる情報源からのニュースが見つかりませんでした（投稿をスキップします）')
            await bot.close()
            return

        print(f'信頼できるニュース数: {len(trusted_news)}')

        # オリジナルURLで重複を除外
        print('重複チェック中（オリジナルURLベース）...')
        unique_news = []
        for news in trusted_news:
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

        # 最新2件のみに絞る（1時間ごと実行のため）
        unique_news = unique_news[:2]
        print(f'投稿対象: {len(unique_news)}件')

        # 各ニュースを個別のスレッドとして投稿
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        today = now.strftime('%Y年%m月%d日')
        posted_count = 0

        for i, news in enumerate(unique_news, 1):
            thread_title = f"{news['title']}"

            # 完全にシンプルな形式：要約 + 空行 + URL のみ
            thread_content = f"{news['summary']}\n\n{news['url']}"

            print(f'スレッド作成中 ({i}/{len(unique_news)}): {thread_title[:50]}...')

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
        save_history(history, unique_news)
        print('投稿履歴を保存しました')

        # macOS通知
        os.system(f'osascript -e \'display notification "{today}の生成AIニュース {posted_count}件をIdiomに投稿しました" with title "Idiom生成AIニュース"\'')

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
