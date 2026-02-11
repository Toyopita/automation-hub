"""
Discord認証エラーハンドラー

認証失敗時の無限ループを防止するためのユーティリティ。
- 認証失敗時は指数バックオフでリトライ
- 最大リトライ回数を超えたら正常終了（KeepAlive回避）
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional

import discord


class AuthRetryConfig:
    """リトライ設定"""
    MAX_RETRIES = 3  # 最大リトライ回数
    INITIAL_WAIT = 300  # 初回待機時間（秒）= 5分
    MAX_WAIT = 1800  # 最大待機時間（秒）= 30分
    BACKOFF_MULTIPLIER = 2  # バックオフ倍率


def _log(service_name: str, level: str, message: str):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    print(f"[{service_name}][{level}] {timestamp} - {message}")


def run_with_retry(
    client: discord.Client,
    token: str,
    service_name: str = "Discord",
    config: Optional[AuthRetryConfig] = None
):
    """
    認証エラー時にリトライ付きでDiscordクライアントを実行

    Args:
        client: discord.Client インスタンス
        token: Discordボットトークン
        service_name: ログ用のサービス名
        config: リトライ設定（省略時はデフォルト）
    """
    if config is None:
        config = AuthRetryConfig()

    retry_count = 0
    wait_time = config.INITIAL_WAIT

    while retry_count <= config.MAX_RETRIES:
        try:
            _log(service_name, 'INFO', '起動中...')
            client.run(token)
            # 正常終了（手動停止など）
            _log(service_name, 'INFO', '正常終了')
            sys.exit(0)

        except discord.LoginFailure as e:
            retry_count += 1
            _log(service_name, 'ERROR', f'認証失敗 ({retry_count}/{config.MAX_RETRIES}): {e}')

            if retry_count > config.MAX_RETRIES:
                _log(service_name, 'CRITICAL',
                     f'認証失敗が{config.MAX_RETRIES}回を超えました。'
                     'トークンを確認してください。プロセスを終了します。')
                # exit(0) で正常終了 → KeepAliveが即座に再起動しない
                # （ThrottleIntervalが適用される）
                sys.exit(0)

            _log(service_name, 'INFO', f'{wait_time}秒待機してリトライします...')
            time.sleep(wait_time)

            # 指数バックオフ
            wait_time = min(wait_time * config.BACKOFF_MULTIPLIER, config.MAX_WAIT)

        except Exception as e:
            # その他のエラー（ネットワークエラーなど）
            _log(service_name, 'ERROR', f'予期しないエラー: {e}')
            # 通常のエラーは再起動で回復する可能性があるのでexit(1)
            sys.exit(1)


async def start_with_retry(
    client: discord.Client,
    token: str,
    service_name: str = "Discord",
    config: Optional[AuthRetryConfig] = None
):
    """
    非同期版: 認証エラー時にリトライ付きでDiscordクライアントを開始

    既存のasyncio.run()内で使用する場合はこちらを使用
    """
    if config is None:
        config = AuthRetryConfig()

    retry_count = 0
    wait_time = config.INITIAL_WAIT

    while retry_count <= config.MAX_RETRIES:
        try:
            _log(service_name, 'INFO', '起動中...')
            await client.start(token)
            _log(service_name, 'INFO', '正常終了')
            return

        except discord.LoginFailure as e:
            retry_count += 1
            _log(service_name, 'ERROR', f'認証失敗 ({retry_count}/{config.MAX_RETRIES}): {e}')

            if retry_count > config.MAX_RETRIES:
                _log(service_name, 'CRITICAL',
                     f'認証失敗が{config.MAX_RETRIES}回を超えました。'
                     'トークンを確認してください。')
                return

            _log(service_name, 'INFO', f'{wait_time}秒待機してリトライします...')
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * config.BACKOFF_MULTIPLIER, config.MAX_WAIT)
