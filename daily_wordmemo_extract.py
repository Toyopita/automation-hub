#!/usr/bin/env python3
"""
Discord書籍フォーラム → Obsidian WordMemo自動抽出Bot

毎日深夜2時に書籍フォーラムの投稿を監視し、
重要な単語を抽出してObsidianのWordMemoに追加します。
"""

import os
import re
import json
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import discord
from dotenv import load_dotenv
import MeCab

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOOK_FORUM_ID = 1433964655172124742

# Obsidianパス
OBSIDIAN_WORDMEMO_DIR = "/Users/minamitakeshi/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/05_WordMemo"
OBSIDIAN_TEMPLATE = "/Users/minamitakeshi/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/00_Templates/book_memo_template.md"

# ログファイル
LOG_FILE = os.path.expanduser("~/discord-mcp-server/wordmemo_extract.log")
PROCESSED_MESSAGES_FILE = os.path.expanduser("~/discord-mcp-server/wordmemo_processed_messages.json")

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

# MeCab初期化
mecab = MeCab.Tagger()


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[WordMemoBot][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg, flush=True)

    # ログファイルにも記録
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def load_processed_messages() -> Set[int]:
    """処理済みメッセージIDを読み込み"""
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        with open(PROCESSED_MESSAGES_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_processed_messages(message_ids: Set[int]):
    """処理済みメッセージIDを保存"""
    with open(PROCESSED_MESSAGES_FILE, 'w') as f:
        json.dump(list(message_ids), f)


def get_existing_wordmemo_words() -> Set[str]:
    """既存のWordMemo単語を取得"""
    existing_words = set()

    if not os.path.exists(OBSIDIAN_WORDMEMO_DIR):
        log('WARNING', 'WordMemoディレクトリが見つかりません', {'path': OBSIDIAN_WORDMEMO_DIR})
        return existing_words

    for filename in os.listdir(OBSIDIAN_WORDMEMO_DIR):
        if filename.endswith('.md'):
            word = filename.replace('.md', '')
            existing_words.add(word)

    log('INFO', '既存WordMemo読み込み完了', {'count': len(existing_words)})
    return existing_words


def extract_words_from_text(text: str) -> List[str]:
    """
    テキストから重要な単語を抽出（MeCabで形態素解析）
    複合語（例: 鉄器時代）を優先的に抽出

    Args:
        text: 解析対象のテキスト

    Returns:
        抽出された単語のリスト
    """
    words = []
    compound_word = ""  # 複合語を構築
    compound_parts = []  # 複合語を構成する個別単語

    # MeCabで形態素解析
    parsed = mecab.parse(text)
    lines = parsed.split('\n')

    for i, line in enumerate(lines):
        if line == 'EOS' or line == '':
            # 複合語が残っている場合は追加
            if compound_word and len(compound_word) >= 3:
                words.append(compound_word)
            compound_word = ""
            compound_parts = []
            continue

        parts = line.split('\t')
        if len(parts) < 2:
            continue

        surface = parts[0]  # 表層形
        features = parts[1].split(',')

        if len(features) < 2:
            continue

        pos = features[0]  # 品詞
        pos_detail = features[1]  # 品詞細分類

        # 名詞の連続を複合語として扱う
        if pos in ['名詞']:
            # 重要な接尾辞リスト（これらで終わる複合語は抽出対象）
            important_suffixes = ['時代', '主義', '文化', '論', '法', '史', '学', '器', '式', '型']

            if compound_word == "":
                # 新しい複合語の開始
                # 固有名詞・サ変接続から始まるもの、または一般名詞でも抽出
                if pos_detail in ['固有名詞', 'サ変接続', '一般']:
                    compound_word = surface
                    compound_parts.append(surface)
            else:
                # 複合語の継続
                compound_word += surface
                compound_parts.append(surface)
        else:
            # 名詞以外が来たら複合語終了
            if compound_word:
                # 重要な接尾辞リスト
                important_suffixes = ['時代', '主義', '文化', '論', '法', '史', '学', '器', '式', '型']

                # ストップワード除外
                stopwords = {
                    'こと', 'もの', 'ため', 'ところ', 'これ', 'それ', 'あれ', 'どれ',
                    'ここ', 'そこ', 'あそこ', 'どこ', '今', '昔', '前', '後', '中',
                    '上', '下', '内', '外', '間', '時', '頃', '人', '方', '者',
                    '年', '月', '日', '場合', '世界', '社会', '問題', '結果',
                    '理由', '意味', '関係', '状態', '状況', '影響', '効果', '変化',
                    '日本', '時期', '地域', '必要', '重要', '可能', '自分', '相手',
                    '全体', '一部', '最初', '最後', '以上', '以下', '程度', '範囲',
                    '特に', '実際', '一般', '具体', '抽象', '全部', '一つ', '二つ'
                }

                # 抽出条件：
                # 1. 固有名詞またはサ変接続を含む複合語（3文字以上）
                # 2. 重要な接尾辞で終わる複合語（3文字以上）
                has_proper_noun = any(p in compound_parts for p in compound_parts if len(compound_parts) > 0)
                ends_with_important_suffix = any(compound_word.endswith(suffix) for suffix in important_suffixes)

                # 固有名詞を含むか、重要な接尾辞で終わる場合のみ抽出
                if compound_word not in stopwords and len(compound_word) >= 3:
                    # 単独の一般名詞（複合語でない）は除外
                    if len(compound_parts) >= 2 or ends_with_important_suffix:
                        words.append(compound_word)

                compound_word = ""
                compound_parts = []

    return words


def ask_gemini_batch_word_info(words: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Gemini APIで複数の単語の詳細情報を一括取得（バッチ処理）

    Args:
        words: 単語のリスト

    Returns:
        単語をキーとした詳細情報の辞書
    """
    if not words:
        return {}

    try:
        # 単語リストをカンマ区切りで表示
        words_str = "、".join(words)

        prompt = f"""以下の単語について、WordMemo用の詳細情報を教えてください。

【単語リスト】
{words_str}

【必須項目（各単語ごと）】
1. 意味: 簡潔な説明（2-3文）
2. 読み方: ひらがなで
3. 語源・由来: 簡潔に
4. 使用例: 1-2例
5. 類義語: 2-3個（なければ「なし」）
6. 対義語: 1-2個（なければ「なし」）
7. 関連語: 3-5個
8. タグ: この単語の内容を分析して、最も関連性の高いタグを10個生成してください。タグは日本語を基本とし（例外: IT, AIなど一般的に使われる英語）、短く明確な単語を使用してください。最初のタグは単語の主要部分にしてください。

【出力形式】
以下のJSON形式で返してください（単語をキーとしたオブジェクト）：
{{
  "{words[0]}": {{
    "meaning": "...",
    "reading": "...",
    "etymology": "...",
    "usage_examples": "...",
    "synonyms": "...",
    "antonyms": "...",
    "related_words": "...",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
  }},
  "{words[1] if len(words) > 1 else '...'}": {{
    ...
  }}
}}
"""

        # geminiコマンド実行
        result = subprocess.run(
            ['/usr/local/bin/gemini', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode == 0:
            response = result.stdout.strip()
            # JSONブロックを抽出
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # ブロックがない場合は全体をJSON扱い
                json_str = response

            # JSONパース
            batch_results = json.loads(json_str)
            log('SUCCESS', 'Geminiからバッチ単語情報取得成功', {'count': len(batch_results)})
            return batch_results
        else:
            log('ERROR', 'Geminiバッチ実行失敗', {'error': result.stderr})
            return {}

    except subprocess.TimeoutExpired:
        log('ERROR', 'Geminiバッチタイムアウト', {'words': words})
        return {}
    except json.JSONDecodeError as e:
        log('ERROR', 'JSONバッチ解析失敗', {'words': words, 'error': str(e)})
        return {}
    except Exception as e:
        log('ERROR', 'Geminiバッチ質問例外', {'words': words, 'error': str(e)})
        return {}


def create_wordmemo_file(word: str, word_info: Dict[str, str]):
    """
    WordMemoファイルを作成

    Args:
        word: 単語
        word_info: 単語の詳細情報
    """
    try:
        # タグを配列形式に変換
        tags = word_info.get('tags', [])
        tags_str = '[' + ', '.join(tags) + ']'

        # テンプレート読み込み
        with open(OBSIDIAN_TEMPLATE, 'r', encoding='utf-8') as f:
            template = f.read()

        # 置換
        content = template.replace('{{word}}', word)
        content = content.replace('{{date}}', datetime.now().strftime('%Y-%m-%d'))
        content = content.replace('{{tags}}', tags_str)
        content = content.replace('{{meaning}}', word_info.get('meaning', ''))
        content = content.replace('{{reading}}', word_info.get('reading', ''))
        content = content.replace('{{etymology}}', word_info.get('etymology', ''))
        content = content.replace('{{usage_examples}}', word_info.get('usage_examples', ''))
        content = content.replace('{{synonyms}}', word_info.get('synonyms', ''))
        content = content.replace('{{antonyms}}', word_info.get('antonyms', ''))
        content = content.replace('{{related_words}}', word_info.get('related_words', ''))
        content = content.replace('{{source_reference}}', f'Discord書籍フォーラムから自動抽出（{datetime.now().strftime("%Y-%m-%d")}）')

        # ファイル保存
        filepath = os.path.join(OBSIDIAN_WORDMEMO_DIR, f"{word}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        log('SUCCESS', 'WordMemoファイル作成完了', {'word': word, 'filepath': filepath})

    except Exception as e:
        log('ERROR', 'WordMemoファイル作成失敗', {'word': word, 'error': str(e)})


async def process_forum():
    """書籍フォーラムの投稿を処理"""
    log('INFO', '書籍フォーラム処理開始')

    # 処理済みメッセージIDを読み込み
    processed_messages = load_processed_messages()

    # 既存のWordMemo単語を取得
    existing_words = get_existing_wordmemo_words()

    # フォーラム取得
    forum = client.get_channel(BOOK_FORUM_ID)
    if not forum:
        log('ERROR', '書籍フォーラムが見つかりません', {'forum_id': BOOK_FORUM_ID})
        return

    # 全スレッドのメッセージを取得（過去24時間分）
    yesterday = datetime.now() - timedelta(days=1)
    new_words_count = 0
    total_messages = 0
    new_words_batch = []  # バッチ処理用の単語リスト
    BATCH_SIZE = 10  # 10単語ごとにバッチ処理

    # アクティブなスレッド
    for thread in forum.threads:
        log('INFO', 'スレッド処理中', {'thread': thread.name})

        async for message in thread.history(limit=100, after=yesterday):
            total_messages += 1

            # Bot投稿は無視
            if message.author.bot:
                continue

            # 処理済みメッセージは無視
            if message.id in processed_messages:
                continue

            # メッセージから単語抽出
            words = extract_words_from_text(message.content)

            for word in words:
                # 既存のWordMemoにない単語のみ処理
                if word not in existing_words:
                    log('INFO', '新規単語発見', {'word': word, 'thread': thread.name})
                    new_words_batch.append(word)
                    existing_words.add(word)  # 重複を避けるため先に追加

                    # バッチサイズに達したら一括処理
                    if len(new_words_batch) >= BATCH_SIZE:
                        log('INFO', 'バッチ処理開始', {'count': len(new_words_batch)})
                        batch_results = ask_gemini_batch_word_info(new_words_batch)

                        # 各単語のWordMemoファイル作成
                        for batch_word in new_words_batch:
                            if batch_word in batch_results:
                                create_wordmemo_file(batch_word, batch_results[batch_word])
                                new_words_count += 1
                            else:
                                log('WARNING', 'バッチ結果に単語が含まれていません', {'word': batch_word})

                        # バッチをクリア
                        new_words_batch = []

            # 処理済みとして記録
            processed_messages.add(message.id)

    # 残りの単語を処理（BATCH_SIZE未満の場合）
    if new_words_batch:
        log('INFO', '残りバッチ処理開始', {'count': len(new_words_batch)})
        batch_results = ask_gemini_batch_word_info(new_words_batch)

        for batch_word in new_words_batch:
            if batch_word in batch_results:
                create_wordmemo_file(batch_word, batch_results[batch_word])
                new_words_count += 1
            else:
                log('WARNING', 'バッチ結果に単語が含まれていません', {'word': batch_word})

    # 処理済みメッセージIDを保存
    save_processed_messages(processed_messages)

    log('INFO', '書籍フォーラム処理完了', {
        'total_messages': total_messages,
        'new_words': new_words_count
    })


@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')

    try:
        await process_forum()
    except Exception as e:
        log('ERROR', '処理中エラー', {'error': str(e)})
    finally:
        await client.close()


if __name__ == "__main__":
    log('INFO', 'WordMemo抽出Bot起動中...')
    client.run(DISCORD_TOKEN)
