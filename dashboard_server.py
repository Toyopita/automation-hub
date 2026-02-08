#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SwitchBot 環境ダッシュボード サーバー
FastAPI サーバー（API + HTML配信）

エンドポイント:
  GET /           → dashboard.html
  GET /api/current → SwitchBot APIリアルタイム値
  GET /api/history?period=24h|3d|7d|30d → Notion履歴データ
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Optional, List, Any
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# .env読み込み
load_dotenv(Path(__file__).parent / '.env')

# ===== 設定 =====
SWITCHBOT_TOKEN = os.environ.get('SWITCHBOT_TOKEN')
SWITCHBOT_API_URL = 'https://api.switch-bot.com/v1.1/devices'
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATA_SOURCE_ID = os.environ.get('AIRCON_CONTROL_NOTION_DB', '2a800160-1818-814b-b27a-000b80e0ceb0')

CO2_METER_ID = os.environ.get('CO2_METER_ID', 'B0E9FE561980')
OUTDOOR_SENSOR_ID = os.environ.get('OUTDOOR_SENSOR_ID', 'D0C84206187C')

STATE_FILE = Path(__file__).parent / 'aircon_state.json'
EMOTION_DATA_FILE = Path(__file__).parent / 'emotion_data.json'
JST = ZoneInfo('Asia/Tokyo')

SCORE_KEYS = ['mood', 'energy', 'intimacy', 'longing', 'eros', 'ds', 'playfulness', 'future', 'engagement']


def normalize_entry(entry: Dict) -> Dict:
    """v1エントリにv2デフォルト値を補完（後方互換）"""
    entry.setdefault('trigger', None)
    entry.setdefault('prev_scores', None)
    entry.setdefault('score_deltas', None)
    return entry

# ===== キャッシュ =====
_cache: Dict[str, tuple] = {}
CACHE_TTL = {
    'current': 60,
    'history_24h': 300,
    'history_3d': 600,
    'history_7d': 900,
    'history_30d': 900,
}


def get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        data, ts = _cache[key]
        ttl = CACHE_TTL.get(key, 300)
        if time.time() - ts < ttl:
            return data
    return None


def set_cache(key: str, data: Any):
    _cache[key] = (data, time.time())


# ===== SwitchBot API =====
def call_switchbot_api(endpoint: str) -> Optional[Dict]:
    url = f"{SWITCHBOT_API_URL}/{endpoint}"
    headers = {
        'Authorization': SWITCHBOT_TOKEN,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('statusCode') == 100:
            return result.get('body')
    except Exception as e:
        print(f"[ERROR] SwitchBot API ({endpoint}): {e}")
    return None


def get_sensor_data(device_id: str) -> Optional[Dict]:
    body = call_switchbot_api(f"{device_id}/status")
    if body:
        return {
            'temperature': body.get('temperature'),
            'humidity': body.get('humidity'),
            'co2': body.get('CO2'),
        }
    return None


def get_aircon_state() -> Optional[Dict]:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


# ===== 不快指数 =====
def calculate_discomfort_index(temperature: float, humidity: float) -> float:
    di = 0.81 * temperature + 0.01 * humidity * (0.99 * temperature - 14.3) + 46.3
    return round(di, 1)


def evaluate_discomfort(di: float) -> str:
    if di < 60:
        return '寒い'
    elif di < 68:
        return 'やや寒い'
    elif di < 75:
        return '快適'
    elif di < 80:
        return 'やや暑い'
    else:
        return '暑い'


# ===== Notion API =====
def query_notion_history(period: str) -> List[Dict]:
    """Notionからエアコン制御ログ履歴を取得（ページネーション対応）"""
    now = datetime.now(JST)
    hours = {'24h': 24, '3d': 72, '7d': 168, '30d': 720}.get(period, 24)
    start_time = now - timedelta(hours=hours)

    url = f'https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE_ID}/query'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2025-09-03',
    }

    all_results = []
    start_cursor = None

    while True:
        body: Dict[str, Any] = {
            'filter': {
                'property': '日時',
                'date': {'on_or_after': start_time.isoformat()},
            },
            'sorts': [{'property': '日時', 'direction': 'ascending'}],
            'page_size': 100,
        }
        if start_cursor:
            body['start_cursor'] = start_cursor

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] Notion query: {e}")
            break

        all_results.extend(data.get('results', []))

        if not data.get('has_more'):
            break
        start_cursor = data.get('next_cursor')

    return _parse_notion_results(all_results)


def _parse_notion_results(results: list) -> List[Dict]:
    """Notionページ配列をダッシュボード用辞書リストに変換"""
    records = []
    for page in results:
        props = page.get('properties', {})

        date_prop = props.get('日時', {}).get('date')
        if not date_prop or not date_prop.get('start'):
            continue

        def _select(name: str) -> Optional[str]:
            sel = props.get(name, {}).get('select')
            return sel.get('name') if sel else None

        def _number(name: str) -> Optional[float]:
            return props.get(name, {}).get('number')

        def _rich_text(name: str) -> Optional[str]:
            texts = props.get(name, {}).get('rich_text', [])
            return texts[0].get('text', {}).get('content', '') if texts else None

        def _title() -> Optional[str]:
            titles = props.get('制御サマリー', {}).get('title', [])
            return titles[0].get('text', {}).get('content', '') if titles else None

        records.append({
            'timestamp': date_prop['start'],
            'indoor_temp': _number('室内温度'),
            'indoor_humidity': _number('室内湿度'),
            'outdoor_temp': _number('外気温度'),
            'outdoor_humidity': _number('外気湿度'),
            'co2': _number('CO2濃度'),
            'discomfort_index': _number('不快指数'),
            'aircon_mode': _select('エアコンモード'),
            'humidifier': _select('加湿器'),
            'controlled': props.get('制御実行', {}).get('checkbox', False),
            'set_temp': _number('設定温度'),
            'action': _rich_text('制御内容'),
            'summary': _title(),
        })

    return records


# ===== FastAPI =====
app = FastAPI(title='SwitchBot 環境ダッシュボード')


@app.get('/', response_class=HTMLResponse)
async def serve_dashboard():
    html_path = Path(__file__).parent / 'dashboard.html'
    return html_path.read_text(encoding='utf-8')


@app.get('/fuji', response_class=HTMLResponse)
async def serve_fuji_trip():
    html_path = Path(__file__).parent / 'fuji_trip.html'
    return html_path.read_text(encoding='utf-8')


@app.get('/emotion', response_class=HTMLResponse)
async def serve_emotion_dashboard():
    html_path = Path(__file__).parent / 'emotion_dashboard.html'
    return html_path.read_text(encoding='utf-8')


@app.get('/api/emotion/current')
async def api_emotion_current():
    if not EMOTION_DATA_FILE.exists():
        return JSONResponse({'error': 'no data'}, status_code=404)
    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    entries = data.get('entries', [])
    if not entries:
        return JSONResponse({'error': 'no data'}, status_code=404)
    return JSONResponse(entries[-1])


@app.get('/api/emotion/history')
async def api_emotion_history(days: int = Query(default=7, ge=1, le=90)):
    if not EMOTION_DATA_FILE.exists():
        return JSONResponse({'days': days, 'count': 0, 'entries': []})
    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    filtered = [e for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]
    return JSONResponse({'days': days, 'count': len(filtered), 'entries': filtered})


@app.get('/api/current')
async def api_current():
    cached = get_cached('current')
    if cached:
        return JSONResponse(cached)

    indoor = get_sensor_data(CO2_METER_ID)
    outdoor = get_sensor_data(OUTDOOR_SENSOR_ID)

    if not indoor:
        return JSONResponse({'error': '室内センサーデータ取得失敗'}, status_code=500)

    di = calculate_discomfort_index(indoor['temperature'], indoor['humidity'])
    di_eval = evaluate_discomfort(di)

    aircon = get_aircon_state()
    aircon_mode = aircon.get('mode', 'unknown') if aircon else 'unknown'

    result = {
        'indoor': indoor,
        'outdoor': outdoor,
        'discomfort_index': di,
        'discomfort_eval': di_eval,
        'aircon_mode': aircon_mode,
        'timestamp': datetime.now(JST).isoformat(),
    }

    set_cache('current', result)
    return JSONResponse(result)


@app.get('/api/history')
async def api_history(period: str = Query(default='24h', pattern='^(24h|3d|7d|30d)$')):
    cache_key = f'history_{period}'
    cached = get_cached(cache_key)
    if cached:
        return JSONResponse(cached)

    records = query_notion_history(period)
    result = {
        'period': period,
        'count': len(records),
        'records': records,
    }

    set_cache(cache_key, result)
    return JSONResponse(result)


# ===== エントリポイント =====
if __name__ == '__main__':
    print(f"[INFO] SwitchBot 環境ダッシュボード起動: http://localhost:8765")
    uvicorn.run(app, host='0.0.0.0', port=8765)
