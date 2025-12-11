#!/usr/bin/env python3
"""
毎時IdiomサーバーのGoogle News RSSを使用して国内情勢ニュースを「🇯🇵｜国内情勢」フォーラムに投稿

Google News RSSを使用（完全無料・API key不要）
フォーラムチャンネルID: 1448493374863573044
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

# 🇯🇵｜国内情勢 フォーラムチャンネルID（Idiomサーバー）
FORUM_ID = 1448493374863573044

# 投稿履歴ファイル（Idiom専用）
HISTORY_FILE = '/Users/minamitakeshi/discord-mcp-server/idiom_japan_news_history.json'

# Google News RSS URL（国内情勢関連ニュース - 網羅的キーワード）
# カテゴリ: 政治、政策、経済、社会、地方
GOOGLE_NEWS_RSS = 'https://news.google.com/rss/search?q=国会 OR 内閣 OR 首相 OR 官邸 OR 与党 OR 野党 OR 自民党 OR 立憲民主党 OR 政権 OR 選挙 OR 衆議院 OR 参議院 OR 予算案 OR 法案 OR 閣議決定 OR 規制改革 OR 少子化対策 OR 社会保障 OR 年金 OR 医療制度 OR 介護 OR 日銀 OR 金融政策 OR 円安 OR 円高 OR 物価高 OR インフレ OR 賃上げ OR 景気 OR 災害 OR 地震 OR 台風 OR 事件 OR 事故 OR 裁判 OR 判決 OR 知事 OR 市長 OR 地方自治 OR 地方創生 OR マイナンバー OR 税制改正 OR 防衛費&hl=ja&gl=JP&ceid=JP:ja'

# 信頼できるメディア名のリスト
TRUSTED_MEDIA_NAMES = [
    '日本経済新聞',
    '日経',
    '朝日新聞',
    '読売新聞',
    '毎日新聞',
    '産経新聞',
    '東京新聞',
    '北海道新聞',
    '中日新聞',
    '西日本新聞',
    '時事通信',
    '共同通信',
    'NHK',
    'TBS',
    'テレビ朝日',
    '日本テレビ',
    'フジテレビ',
    'テレビ東京',
    '東洋経済',
    'ダイヤモンド',
    'Bloomberg',
    'ブルームバーグ',
    'Reuters',
    'ロイター',
    'WEDGE',
    'JBpress',
    '現代ビジネス',
    'Yahoo!ニュース',
    'PR TIMES',
    '文春オンライン',
    '新潮',
    'AERA',
    'プレジデント',
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
        if item['url'] == url:
            return True
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
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def parse_rss(rss_content):
    """RSSコンテンツをパースしてニュースリストを返す"""
    feed = feedparser.parse(rss_content)
    news_list = []

    for entry in feed.entries[:50]:
        title = entry.get('title', '')
        url = entry.get('link', '')
        summary = entry.get('summary', entry.get('description', ''))
        published = entry.get('published', '')

        title = remove_html_tags(title)
        summary = remove_html_tags(summary)

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
        forum = bot.get_channel(FORUM_ID)
        if not forum:
            print(f'エラー: フォーラムチャンネル（ID: {FORUM_ID}）が見つかりません')
            await bot.close()
            return

        print(f'フォーラム: {forum.name}')

        history = load_history()
        print(f'投稿履歴: {len(history)}件')

        print('Google News RSSから国内情勢ニュースを取得中...')
        rss_content = await fetch_google_news()

        if not rss_content:
            print('❌ RSS取得に失敗しました')
            await bot.close()
            return

        news_list = parse_rss(rss_content)
        print(f'RSS取得ニュース数: {len(news_list)}')

        if len(news_list) == 0:
            print('ℹ️  ニュースが見つかりませんでした')
            await bot.close()
            return

        print('URL検証＆オリジナルURL取得中...')
        verified_news = []
        for news in news_list:
            is_valid, original_url = await verify_url(news['url'])
            if is_valid:
                news['url'] = original_url
                verified_news.append(news)

        if len(verified_news) == 0:
            print('⚠️  全てのニュースがURL検証に失敗しました')
            await bot.close()
            return

        print(f'検証済みニュース数: {len(verified_news)}')

        print('信頼できる情報源のフィルタリング中...')
        trusted_news = [news for news in verified_news if is_trusted_source(news['title'], news['summary'])]

        if len(trusted_news) == 0:
            print('ℹ️  信頼できる情報源からのニュースが見つかりませんでした')
            await bot.close()
            return

        print(f'信頼できるニュース数: {len(trusted_news)}')

        print('重複チェック中...')
        unique_news = [news for news in trusted_news if not is_duplicate(news['title'], news['url'], history)]

        if len(unique_news) == 0:
            print('ℹ️  新しいニュースはありません')
            await bot.close()
            return

        print(f'新規ニュース数: {len(unique_news)}')

        unique_news = unique_news[:2]
        print(f'投稿対象: {len(unique_news)}件')

        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        today = now.strftime('%Y年%m月%d日')
        posted_count = 0

        for i, news in enumerate(unique_news, 1):
            thread_title = f"{news['title']}"
            thread_content = f"{news['summary']}\n\n{news['url']}"

            print(f'スレッド作成中 ({i}/{len(unique_news)}): {thread_title[:50]}...')

            thread = await forum.create_thread(
                name=thread_title[:100],
                content=thread_content
            )

            print(f'  ✅ 投稿完了: {thread.thread.jump_url}')
            posted_count += 1

            await asyncio.sleep(2)

        print(f'\n✅ 全{posted_count}件の投稿完了')

        save_history(history, unique_news)
        print('投稿履歴を保存しました')

        os.system(f'osascript -e \'display notification "{today}の国内情勢ニュース {posted_count}件をIdiomに投稿しました" with title "Idiom 国内情勢ニュース"\'')

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
