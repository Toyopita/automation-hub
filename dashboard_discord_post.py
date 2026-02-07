#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SwitchBot 環境ダッシュボード - 毎朝Discord投稿
24時間のセンサーデータをmatplotlib画像にしてDiscordに投稿する
"""

import os
import io
import json
import subprocess
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import discord
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv

# dashboard_server からNotion取得関数をインポート
from dashboard_server import (
    query_notion_history, calculate_discomfort_index,
    get_sensor_data, get_aircon_state, evaluate_discomfort,
    CO2_METER_ID, OUTDOOR_SENSOR_ID, JST as _JST,
)

load_dotenv(Path(__file__).parent / '.env')

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
CHANNEL_ID = int(os.environ.get('AIRCON_CONTROL_DISCORD_CHANNEL', '1437603269307535484'))
JST = ZoneInfo('Asia/Tokyo')

# matplotlib 日本語フォント設定
plt.rcParams['font.family'] = 'Hiragino Sans'
plt.rcParams['axes.unicode_minus'] = False


def create_dashboard_image(records: list) -> io.BytesIO:
    """24時間データから4パネル画像を生成"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), facecolor='#0f0f1a')
    fig.subplots_adjust(hspace=0.35, wspace=0.25, top=0.92, bottom=0.08, left=0.08, right=0.96)

    now = datetime.now(JST)
    fig.suptitle(
        f'SwitchBot 環境レポート - {now.strftime("%Y年%m月%d日")}',
        color='#e0e0e0', fontsize=14, fontweight='bold',
    )

    timestamps = [datetime.fromisoformat(r['timestamp']) for r in records]
    # タイムゾーンがない場合JSTを付与
    timestamps = [t.replace(tzinfo=JST) if t.tzinfo is None else t for t in timestamps]

    def style_ax(ax, title, ylabel):
        ax.set_facecolor('#16163a')
        ax.set_title(title, color='#ccc', fontsize=11, pad=8)
        ax.set_ylabel(ylabel, color='#888', fontsize=9)
        ax.tick_params(colors='#666', labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=JST))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.grid(True, alpha=0.15, color='#444')
        for spine in ax.spines.values():
            spine.set_color('#333')

    # --- 1. 温度 ---
    ax1 = axes[0, 0]
    style_ax(ax1, '温度', '°C')
    indoor_t = [r['indoor_temp'] for r in records]
    outdoor_t = [r['outdoor_temp'] for r in records]
    ax1.plot(timestamps, indoor_t, color='#ff6b6b', linewidth=1.5, label='室内')
    ax1.plot(timestamps, outdoor_t, color='#4dabf7', linewidth=1.5, linestyle='--', label='外気')
    # エアコンON区間を背景色で表示
    for i in range(len(records) - 1):
        mode = records[i].get('aircon_mode')
        if mode == '暖房':
            ax1.axvspan(timestamps[i], timestamps[i+1], alpha=0.1, color='#ff8c00', linewidth=0)
        elif mode == '冷房':
            ax1.axvspan(timestamps[i], timestamps[i+1], alpha=0.1, color='#4169e1', linewidth=0)
    ax1.legend(loc='upper right', fontsize=8, framealpha=0.3, labelcolor='#ccc')

    # --- 2. 湿度 ---
    ax2 = axes[0, 1]
    style_ax(ax2, '湿度', '%')
    indoor_h = [r['indoor_humidity'] for r in records]
    outdoor_h = [r['outdoor_humidity'] for r in records]
    ax2.plot(timestamps, indoor_h, color='#51cf66', linewidth=1.5, label='室内')
    ax2.plot(timestamps, outdoor_h, color='#74c0fc', linewidth=1.5, linestyle='--', label='外気')
    ax2.legend(loc='upper right', fontsize=8, framealpha=0.3, labelcolor='#ccc')

    # --- 3. CO2 ---
    ax3 = axes[1, 0]
    style_ax(ax3, 'CO2 濃度', 'ppm')
    co2_vals = [r['co2'] for r in records]
    ax3.fill_between(timestamps, co2_vals, alpha=0.3, color='#ffd43b')
    ax3.plot(timestamps, co2_vals, color='#ffd43b', linewidth=1.5)
    ax3.axhline(y=1000, color='#ff6b6b', linewidth=1, linestyle='--', alpha=0.6)
    ax3.text(timestamps[0], 1010, '1000ppm', color='#ff6b6b', fontsize=7, alpha=0.7)

    # --- 4. 不快指数 ---
    ax4 = axes[1, 1]
    style_ax(ax4, '不快指数', 'DI')
    di_vals = [r['discomfort_index'] for r in records]
    ax4.plot(timestamps, di_vals, color='#cc5de8', linewidth=1.5)
    ax4.axhspan(68, 75, alpha=0.08, color='#51cf66')
    ax4.text(timestamps[0], 69, '快適ゾーン', color='#51cf66', fontsize=7, alpha=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='#0f0f1a')
    plt.close(fig)
    buf.seek(0)
    return buf


def create_summary_text(records: list) -> str:
    """サマリーテキストを生成"""
    if not records:
        return '**環境データなし**'

    now = datetime.now(JST)

    indoor_temps = [r['indoor_temp'] for r in records if r['indoor_temp'] is not None]
    outdoor_temps = [r['outdoor_temp'] for r in records if r['outdoor_temp'] is not None]
    co2_vals = [r['co2'] for r in records if r['co2'] is not None]
    humidity_vals = [r['indoor_humidity'] for r in records if r['indoor_humidity'] is not None]
    di_vals = [r['discomfort_index'] for r in records if r['discomfort_index'] is not None]

    heat_count = sum(1 for r in records if r.get('aircon_mode') == '暖房')
    cool_count = sum(1 for r in records if r.get('aircon_mode') == '冷房')
    hum_on_count = sum(1 for r in records if r.get('humidifier') == 'ON')

    latest = records[-1]
    latest_temp = latest.get('indoor_temp', '--')
    latest_hum = latest.get('indoor_humidity', '--')
    latest_co2 = latest.get('co2', '--')

    lines = [
        f'## 🌡️ 環境サマリー - {now.strftime("%Y年%m月%d日")}',
        '',
        f'**現在値**: 室内 {latest_temp}°C / {latest_hum}% / CO2 {latest_co2}ppm',
        '',
        '**24時間統計:**',
    ]

    if indoor_temps:
        lines.append(f'  室内温度: {min(indoor_temps):.1f}°C ~ {max(indoor_temps):.1f}°C（平均 {sum(indoor_temps)/len(indoor_temps):.1f}°C）')
    if outdoor_temps:
        lines.append(f'  外気温度: {min(outdoor_temps):.1f}°C ~ {max(outdoor_temps):.1f}°C（平均 {sum(outdoor_temps)/len(outdoor_temps):.1f}°C）')
    if co2_vals:
        lines.append(f'  CO2濃度: {min(co2_vals)} ~ {max(co2_vals)}ppm（平均 {sum(co2_vals)/len(co2_vals):.0f}ppm）')
    if humidity_vals:
        lines.append(f'  室内湿度: {min(humidity_vals):.0f}% ~ {max(humidity_vals):.0f}%（平均 {sum(humidity_vals)/len(humidity_vals):.0f}%）')
    if di_vals:
        lines.append(f'  不快指数: {min(di_vals):.1f} ~ {max(di_vals):.1f}（平均 {sum(di_vals)/len(di_vals):.1f}）')

    lines.append('')
    lines.append('**制御回数:**')
    lines.append(f'  暖房ON: {heat_count}回 / 冷房ON: {cool_count}回 / 加湿器ON: {hum_on_count}回')
    lines.append('')
    lines.append(f'`自動送信 | {now.strftime("%Y-%m-%d %H:%M")}`')

    return '\n'.join(lines)


def update_github_pages():
    """GitHub Pages用の静的HTMLを生成してプッシュ"""
    print('[INFO] GitHub Pages更新開始...')
    script_dir = Path(__file__).parent

    # 現在値取得
    indoor = get_sensor_data(CO2_METER_ID)
    outdoor = get_sensor_data(OUTDOOR_SENSOR_ID)
    aircon = get_aircon_state()
    now = datetime.now(JST)

    current = {
        'indoor': indoor,
        'outdoor': outdoor,
        'discomfort_index': calculate_discomfort_index(indoor['temperature'], indoor['humidity']) if indoor else None,
        'discomfort_eval': evaluate_discomfort(calculate_discomfort_index(indoor['temperature'], indoor['humidity'])) if indoor else None,
        'aircon_mode': aircon.get('mode', 'unknown') if aircon else 'unknown',
        'timestamp': now.isoformat(),
    }

    # 全期間のデータ取得
    history = {}
    for p in ['24h', '3d', '7d', '30d']:
        records = query_notion_history(p)
        history[p] = {'period': p, 'count': len(records), 'records': records}
        print(f'[INFO]   {p}: {len(records)}件')

    # dashboard.html読み込み
    html = (script_dir / 'dashboard.html').read_text(encoding='utf-8')

    # データ埋め込み
    now_str = now.strftime('%m/%d %H:%M')
    embedded = (
        '<script>\n'
        f'// === 埋め込みデータ（{now.strftime("%Y-%m-%d %H:%M JST")} スナップショット） ===\n'
        f'const EMBEDDED_CURRENT = {json.dumps(current, ensure_ascii=False)};\n'
        f'const EMBEDDED_HISTORY = {json.dumps(history, ensure_ascii=False)};\n'
        '</script>\n'
        '<script>\n'
        'const _origFetch = window.fetch;\n'
        'window.fetch = function(url) {\n'
        "  if (url === '/api/current') return Promise.resolve({ok:true, json:()=>Promise.resolve(EMBEDDED_CURRENT)});\n"
        "  const m = url.match(/\\/api\\/history\\?period=(\\w+)/);\n"
        '  if (m && EMBEDDED_HISTORY[m[1]]) return Promise.resolve({ok:true, json:()=>Promise.resolve(EMBEDDED_HISTORY[m[1]])});\n'
        '  return _origFetch.apply(this, arguments);\n'
        '};\n'
        '</script>\n'
    )

    html = html.replace('<style>', embedded + '<style>', 1)
    html = html.replace(
        '<title>SwitchBot 環境ダッシュボード</title>',
        f'<title>SwitchBot 環境ダッシュボード（{now_str} スナップショット）</title>',
    )
    html = html.replace(
        'const REFRESH_INTERVAL = 5 * 60 * 1000;',
        'const REFRESH_INTERVAL = 999999999; // 静的スナップショット',
    )

    # docs/index.html に書き出し
    docs = script_dir / 'docs'
    docs.mkdir(exist_ok=True)
    (docs / 'index.html').write_text(html, encoding='utf-8')
    print(f'[INFO] docs/index.html 更新完了')

    # git commit & push
    try:
        subprocess.run(
            ['git', 'add', 'docs/index.html'],
            cwd=str(script_dir), check=True, capture_output=True,
        )
        subprocess.run(
            ['git', 'commit', '-m', f'Update: ダッシュボードスナップショット ({now.strftime("%Y-%m-%d %H:%M")})'],
            cwd=str(script_dir), check=True, capture_output=True,
        )
        subprocess.run(
            ['git', 'push', 'origin', 'master'],
            cwd=str(script_dir), check=True, capture_output=True,
        )
        print('[INFO] GitHub push完了')
    except subprocess.CalledProcessError as e:
        print(f'[WARN] git push失敗: {e.stderr.decode()[:200] if e.stderr else e}')


async def main():
    print(f'[INFO] {datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")} 環境ダッシュボード投稿開始')

    # 24時間分のデータ取得
    print('[INFO] Notionから24時間分のデータ取得中...')
    records = query_notion_history('24h')
    print(f'[INFO] {len(records)}件のレコード取得')

    if not records:
        print('[WARN] データなし、投稿スキップ')
        return

    # 画像生成
    print('[INFO] グラフ画像生成中...')
    image_buf = create_dashboard_image(records)

    # サマリーテキスト生成
    summary = create_summary_text(records)

    # Discord投稿
    print('[INFO] Discordに投稿中...')
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'[INFO] Discord Bot起動: {client.user}')
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            file = discord.File(image_buf, filename='environment_dashboard.png')
            await channel.send(content=summary, file=file)
            print('[INFO] 投稿完了')
        else:
            print(f'[ERROR] チャンネル {CHANNEL_ID} が見つかりません')
        await client.close()

    await client.start(DISCORD_TOKEN)

    # GitHub Pages更新
    update_github_pages()

    print(f'[INFO] {datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")} 完了')


if __name__ == '__main__':
    asyncio.run(main())
