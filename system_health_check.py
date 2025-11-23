#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム健全性チェックスクリプト
全launchdジョブの実行状態とエラーログを分析し、Discord/Notionに報告
"""

import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict
import requests
from dotenv import load_dotenv

# .envファイル読み込み
load_dotenv()


@dataclass
class JobStatus:
    """launchdジョブの状態"""
    label: str
    pid: str
    status: str
    last_exit_status: int


@dataclass
class ErrorLogEntry:
    """エラーログエントリ"""
    timestamp: datetime
    level: str
    script: str
    message: str


class Config:
    """設定クラス"""
    DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_CHANNEL_ID = os.getenv('SYSTEM_HEALTH_CHANNEL_ID')  # 新規チャンネルID
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('SYSTEM_HEALTH_NOTION_DB')  # 新規データベースID
    LAUNCHD_DIR = Path.home() / 'Library' / 'LaunchAgents'
    LOG_DIR = Path.home() / 'discord-mcp-server'
    TIMEZONE = 'Asia/Tokyo'


class LaunchdJobChecker:
    """launchdジョブの状態チェック"""

    def __init__(self):
        self.launchd_prefix = 'com.discord.'

    def get_all_jobs(self) -> List[str]:
        """全launchdジョブラベルを取得"""
        jobs = []
        for plist_file in Config.LAUNCHD_DIR.glob(f'{self.launchd_prefix}*.plist'):
            label = plist_file.stem
            jobs.append(label)
        return sorted(jobs)

    def get_job_status(self, label: str) -> JobStatus:
        """個別ジョブの状態を取得"""
        try:
            # launchctl list でジョブ情報を取得
            result = subprocess.run(
                ['launchctl', 'list', label],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # ジョブがロードされていない
                return JobStatus(label=label, pid='-', status='not_loaded', last_exit_status=-1)

            # 出力をパース
            output = result.stdout
            pid = '-'
            last_exit = 0

            # PID行を探す
            for line in output.split('\n'):
                if '"PID"' in line:
                    match = re.search(r'=\s*(\d+|0)', line)
                    if match:
                        pid = match.group(1)
                        if pid == '0':
                            pid = '-'
                elif '"LastExitStatus"' in line:
                    match = re.search(r'=\s*(-?\d+)', line)
                    if match:
                        last_exit = int(match.group(1))

            # ステータス判定
            if pid != '-':
                status = 'running'
            elif last_exit == 0:
                status = 'success'
            else:
                status = 'failed'

            return JobStatus(
                label=label,
                pid=pid,
                status=status,
                last_exit_status=last_exit
            )

        except subprocess.TimeoutExpired:
            print(f"[WARN] Timeout getting status for {label}")
            return JobStatus(label=label, pid='-', status='timeout', last_exit_status=-1)
        except Exception as e:
            print(f"[ERROR] Failed to get status for {label}: {e}")
            return JobStatus(label=label, pid='-', status='error', last_exit_status=-1)

    def check_all_jobs(self) -> Dict[str, JobStatus]:
        """全ジョブの状態をチェック"""
        jobs = self.get_all_jobs()
        results = {}

        print(f"[INFO] Checking {len(jobs)} launchd jobs...")

        for job in jobs:
            status = self.get_job_status(job)
            results[job] = status

        return results

    def categorize_jobs(self, job_statuses: Dict[str, JobStatus]) -> Dict[str, List[str]]:
        """ジョブを状態別に分類"""
        categories = {
            'running': [],
            'success': [],
            'failed': [],
            'not_loaded': [],
            'error': []
        }

        for label, status in job_statuses.items():
            categories[status.status].append(label)

        return categories


class ErrorLogAnalyzer:
    """エラーログ分析"""

    def __init__(self):
        self.log_dir = Config.LOG_DIR

    def get_today_errors(self) -> List[ErrorLogEntry]:
        """今日のエラーログを取得"""
        today = datetime.now().date()
        errors = []

        # 全.logファイルをスキャン
        for log_file in self.log_dir.glob('*.log'):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        # エラーレベルのログを検索
                        if '[ERROR]' in line or '[CRITICAL]' in line:
                            # タイムスタンプ抽出
                            timestamp_match = re.search(
                                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
                                line
                            )

                            if timestamp_match:
                                timestamp_str = timestamp_match.group(1)
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                                # 今日のログのみ
                                if timestamp.date() == today:
                                    level = 'ERROR' if '[ERROR]' in line else 'CRITICAL'
                                    errors.append(ErrorLogEntry(
                                        timestamp=timestamp,
                                        level=level,
                                        script=log_file.stem,
                                        message=line.strip()
                                    ))
            except Exception as e:
                print(f"[WARN] Failed to read {log_file}: {e}")

        return sorted(errors, key=lambda x: x.timestamp, reverse=True)

    def get_error_summary(self, errors: List[ErrorLogEntry]) -> Dict[str, int]:
        """エラーをスクリプト別に集計"""
        summary = defaultdict(int)

        for error in errors:
            summary[error.script] += 1

        return dict(summary)


class HealthReporter:
    """健全性レポート生成・送信"""

    def __init__(self):
        self.discord_token = Config.DISCORD_TOKEN
        self.discord_channel_id = Config.DISCORD_CHANNEL_ID
        self.notion_token = Config.NOTION_TOKEN
        self.notion_db_id = Config.NOTION_DATABASE_ID

    def generate_daily_report(
        self,
        job_categories: Dict[str, List[str]],
        error_summary: Dict[str, int],
        total_errors: int
    ) -> str:
        """日次レポート生成(Discord用)"""
        now = datetime.now()

        report = f"📊 **システム健全性レポート**\n"
        report += f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # ジョブサマリー
        total_jobs = sum(len(jobs) for jobs in job_categories.values())
        report += f"**📋 launchdジョブ状態** (合計: {total_jobs})\n"
        report += f"✅ 成功: {len(job_categories['success'])}\n"
        report += f"🏃 実行中: {len(job_categories['running'])}\n"
        report += f"❌ 失敗: {len(job_categories['failed'])}\n"
        report += f"⚠️ 未ロード: {len(job_categories['not_loaded'])}\n\n"

        # 失敗ジョブの詳細
        if job_categories['failed']:
            report += f"**🚨 失敗したジョブ ({len(job_categories['failed'])})**\n"
            for job in job_categories['failed'][:10]:  # 最大10件
                report += f"- `{job}`\n"
            if len(job_categories['failed']) > 10:
                report += f"...他{len(job_categories['failed']) - 10}件\n"
            report += "\n"

        # エラーログサマリー
        report += f"**📝 エラーログ** (合計: {total_errors})\n"
        if error_summary:
            sorted_errors = sorted(error_summary.items(), key=lambda x: x[1], reverse=True)
            for script, count in sorted_errors[:5]:  # 上位5件
                report += f"- `{script}`: {count}件\n"
            if len(error_summary) > 5:
                report += f"...他{len(error_summary) - 5}スクリプト\n"
        else:
            report += "エラーなし ✨\n"

        # 総合評価
        report += "\n**🎯 総合評価**\n"
        if job_categories['failed'] or total_errors > 10:
            report += "⚠️ 要注意: 失敗ジョブまたは多数のエラーを検出\n"
        elif total_errors > 0:
            report += "⚡ 注意: 一部エラーあり\n"
        else:
            report += "✅ 良好: 問題なし\n"

        return report

    def send_discord_notification(self, message: str) -> bool:
        """Discord通知送信"""
        try:
            if not self.discord_token or not self.discord_channel_id:
                print("[WARN] Discord credentials not configured")
                return False

            url = f"https://discord.com/api/v10/channels/{self.discord_channel_id}/messages"
            headers = {
                'Authorization': f'Bot {self.discord_token}',
                'Content-Type': 'application/json'
            }
            data = {'content': message}

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.ok:
                print("[INFO] Discord notification sent successfully")
                return True
            else:
                print(f"[ERROR] Discord notification failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Discord notification error: {e}")
            return False

    def save_to_notion(
        self,
        report_type: str,
        job_categories: Dict[str, List[str]],
        error_summary: Dict[str, int],
        total_errors: int
    ) -> bool:
        """Notionにレポートを保存"""
        try:
            if not self.notion_token or not self.notion_db_id:
                print("[WARN] Notion credentials not configured")
                return False

            now = datetime.now()
            total_jobs = sum(len(jobs) for jobs in job_categories.values())

            # 総合評価を決定
            if job_categories['failed'] or total_errors > 10:
                overall_status = "要注意"
            elif total_errors > 0:
                overall_status = "注意"
            else:
                overall_status = "良好"

            # レポート名生成
            if report_type == "weekly":
                report_name = f"週次レポート {now.strftime('%Y年%m月 第%W週')}"
            else:
                report_name = f"日次レポート {now.strftime('%Y-%m-%d')}"

            # Notion APIリクエスト
            url = "https://api.notion.com/v1/pages"
            headers = {
                'Authorization': f'Bearer {self.notion_token}',
                'Content-Type': 'application/json',
                'Notion-Version': '2025-09-03'
            }

            properties = {
                'レポート名': {
                    'type': 'title',
                    'title': [{'type': 'text', 'text': {'content': report_name}}]
                },
                'レポート日時': {
                    'type': 'date',
                    'date': {'start': now.strftime('%Y-%m-%d')}
                },
                'レポートタイプ': {
                    'type': 'select',
                    'select': {'name': '週次' if report_type == 'weekly' else '日次'}
                },
                '総ジョブ数': {
                    'type': 'number',
                    'number': total_jobs
                },
                '成功ジョブ数': {
                    'type': 'number',
                    'number': len(job_categories['success'])
                },
                '失敗ジョブ数': {
                    'type': 'number',
                    'number': len(job_categories['failed'])
                },
                '実行中ジョブ数': {
                    'type': 'number',
                    'number': len(job_categories['running'])
                },
                'エラーログ件数': {
                    'type': 'number',
                    'number': total_errors
                },
                '総合評価': {
                    'type': 'select',
                    'select': {'name': overall_status}
                }
            }

            data = {
                'parent': {'database_id': self.notion_db_id},
                'properties': properties
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.ok:
                print(f"[INFO] Notion {report_type} report saved successfully")
                return True
            else:
                print(f"[ERROR] Notion save failed: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return False

        except Exception as e:
            print(f"[ERROR] Notion save error: {e}")
            return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("システム健全性チェック開始")
    print("=" * 60)

    # launchdジョブチェック
    print("\n[1/3] launchdジョブをチェック中...")
    job_checker = LaunchdJobChecker()
    job_statuses = job_checker.check_all_jobs()
    job_categories = job_checker.categorize_jobs(job_statuses)

    print(f"  - 成功: {len(job_categories['success'])}")
    print(f"  - 実行中: {len(job_categories['running'])}")
    print(f"  - 失敗: {len(job_categories['failed'])}")

    # エラーログ分析
    print("\n[2/3] エラーログを分析中...")
    log_analyzer = ErrorLogAnalyzer()
    errors = log_analyzer.get_today_errors()
    error_summary = log_analyzer.get_error_summary(errors)

    print(f"  - 今日のエラー: {len(errors)}件")
    print(f"  - 影響スクリプト: {len(error_summary)}個")

    # レポート生成・送信
    print("\n[3/3] レポートを生成・送信中...")
    reporter = HealthReporter()
    daily_report = reporter.generate_daily_report(job_categories, error_summary, len(errors))

    print("\n" + "=" * 60)
    print(daily_report)
    print("=" * 60)

    # Discord通知
    reporter.send_discord_notification(daily_report)

    print("\nシステム健全性チェック完了")


if __name__ == '__main__':
    main()
