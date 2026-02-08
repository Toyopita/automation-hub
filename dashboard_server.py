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
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Optional, List, Any, Tuple
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
    'advice_7': 300,
    'advice_14': 300,
    'advice_30': 300,
    'advice_60': 300,
    'advice_90': 300,
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
    return JSONResponse(normalize_entry(entries[-1]))


@app.get('/api/emotion/history')
async def api_emotion_history(days: int = Query(default=7, ge=1, le=90)):
    if not EMOTION_DATA_FILE.exists():
        return JSONResponse({'days': days, 'count': 0, 'entries': []})
    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    filtered = [normalize_entry(e) for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]
    return JSONResponse({'days': days, 'count': len(filtered), 'entries': filtered})


@app.get('/api/emotion/trigger-stats')
async def api_trigger_stats(days: int = Query(default=30, ge=1, le=90)):
    """カテゴリ別のトリガー統計情報"""
    if not EMOTION_DATA_FILE.exists():
        return JSONResponse({'days': days, 'categories': {}, 'total_triggered': 0, 'total_spontaneous': 0})
    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    entries = [normalize_entry(e) for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]

    stats: Dict[str, Dict] = {}
    total_triggered = 0
    total_spontaneous = 0

    for e in entries:
        trigger = e.get('trigger')
        if trigger is None:
            total_spontaneous += 1
            continue
        total_triggered += 1
        cat = trigger.get('category', 'unknown')
        if cat not in stats:
            stats[cat] = {'count': 0, 'effects': [], 'response_times': [], 'deltas_sum': {k: 0.0 for k in SCORE_KEYS}}
        stats[cat]['count'] += 1
        deltas = e.get('score_deltas') or {}
        effect = sum(max(0, v) for v in deltas.values())
        stats[cat]['effects'].append(effect)
        rt = trigger.get('response_time_min')
        if rt is not None:
            stats[cat]['response_times'].append(rt)
        for k in SCORE_KEYS:
            stats[cat]['deltas_sum'][k] += deltas.get(k, 0)

    result = {}
    for cat, s in stats.items():
        n = s['count']
        result[cat] = {
            'count': n,
            'avg_effect': round(sum(s['effects']) / n, 1) if n else 0,
            'avg_response_min': round(sum(s['response_times']) / len(s['response_times'])) if s['response_times'] else None,
            'avg_deltas': {k: round(v / n, 1) for k, v in s['deltas_sum'].items()} if n else {},
        }

    return JSONResponse({
        'days': days,
        'categories': result,
        'total_triggered': total_triggered,
        'total_spontaneous': total_spontaneous,
    })


@app.get('/api/emotion/best-messages')
async def api_best_messages(days: int = Query(default=30, ge=1, le=90), limit: int = Query(default=10, ge=1, le=50)):
    """効果的だったメッセージのランキング"""
    if not EMOTION_DATA_FILE.exists():
        return JSONResponse({'days': days, 'messages': []})
    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    entries = [normalize_entry(e) for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]

    triggered = []
    for e in entries:
        trigger = e.get('trigger')
        if trigger is None:
            continue
        deltas = e.get('score_deltas') or {}
        effect = sum(max(0, v) for v in deltas.values())
        triggered.append({
            'trigger_message': trigger.get('message', ''),
            'category': trigger.get('category', 'unknown'),
            'modifiers': trigger.get('modifiers', []),
            'sent_at': trigger.get('sent_at'),
            'response_at': e.get('timestamp'),
            'response_time_min': trigger.get('response_time_min'),
            'effect_score': effect,
            'score_deltas': deltas,
            'resulting_scores': e.get('scores', {}),
        })

    triggered.sort(key=lambda x: x['effect_score'], reverse=True)
    return JSONResponse({'days': days, 'messages': triggered[:limit]})


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


# ===== アドバイス生成ロジック =====

# --- 関係ステージ検出 ---
# 心理学的根拠: Knapp's relational development model（関係発展段階モデル）
# 初期段階ではデータ不足のため、判定閾値を緩和し、confidence_levelを付与する
STAGE_CONFIG = {
    'initial': {       # 出会い〜2週間: 探索期
        'max_days': 14,
        'trend_threshold': 0.5,        # 傾き判定を緩和（データ少のため）
        'min_data_for_trend': 5,       # トレンド判定に必要な最小エントリ数
        'anxious_threshold': 4,        # anxious警告の閾値を引き上げ（初期の不安は自然）
        'gap_warning_hours': 48,       # 遠距離+時差で24hギャップは構造的に発生するため48hに
        'default_confidence': 'low',
    },
    'building': {      # 2週間〜2ヶ月: 関係構築期
        'max_days': 60,
        'trend_threshold': 0.4,
        'min_data_for_trend': 8,
        'anxious_threshold': 3,
        'gap_warning_hours': 24,
        'default_confidence': 'medium',
    },
    'establishing': {  # 2〜6ヶ月: 確立期
        'max_days': 180,
        'trend_threshold': 0.3,
        'min_data_for_trend': 10,
        'anxious_threshold': 3,
        'gap_warning_hours': 24,
        'default_confidence': 'high',
    },
    'stable': {        # 6ヶ月以上: 安定期
        'max_days': 99999,
        'trend_threshold': 0.3,
        'min_data_for_trend': 10,
        'anxious_threshold': 2,
        'gap_warning_hours': 18,
        'default_confidence': 'high',
    },
}


def detect_relationship_stage(entries: List[Dict]) -> str:
    """エントリの日付範囲から関係ステージを判定"""
    if len(entries) < 2:
        return 'initial'
    try:
        first = datetime.fromisoformat(entries[0]['timestamp'])
        last = datetime.fromisoformat(entries[-1]['timestamp'])
        days = (last - first).days
    except (ValueError, TypeError, KeyError):
        return 'initial'
    if days <= 14:
        return 'initial'
    elif days <= 60:
        return 'building'
    elif days <= 180:
        return 'establishing'
    return 'stable'


def _confidence_level(category_count: int, total_entries: int) -> str:
    """カテゴリ使用回数とエントリ総数から統計的信頼度を算出"""
    if category_count >= 10 and total_entries >= 30:
        return 'high'
    elif category_count >= 5 and total_entries >= 15:
        return 'medium'
    elif category_count >= 3:
        return 'low'
    return 'insufficient'


# スコアパラメータの重み（関係健康度計算用）
# 根拠:
#   engagement×1.4: Gottman研究 - 関与度は関係満足度の最強予測因子
#   intimacy×1.3: Reis & Shaver (1988) intimacy process model
#   mood×1.1: 感情トーンは全体的な関係質の指標
#   future×1.0: 遠距離関係では将来展望が関係維持の鍵（Stafford, 2005）
#   playfulness×0.9: Proyer (2014) 遊び心と関係満足度の正相関
#   energy×0.7: 状態変数（疲労等の外的要因に左右される）→ 重みを下げる
#   longing×0.5: 遠距離では常に高い。重みが高いと健康度を歪める
#   eros×0.4: 性的テンションは変動が大きく、直接的な関係健全性指標ではない
#   ds×0.2: D/s嗜好は個人の性的指向であり関係健全性と独立
SCORE_WEIGHTS = {
    'mood': 1.1, 'energy': 0.7, 'intimacy': 1.3, 'longing': 0.5,
    'eros': 0.4, 'ds': 0.2, 'playfulness': 0.9, 'future': 1.0, 'engagement': 1.4,
}

# カテゴリ定義
ADV_CATEGORIES = ('status', 'effective', 'warning', 'action', 'timing')
ADV_PRIORITIES = ('urgent', 'important', 'info')


def _compute_trend(values: List[float], threshold: float = 0.3) -> Tuple[str, float]:
    """直近の値リストから傾き（上昇/下降/安定）を算出。最小二乗法で線形回帰。"""
    n = len(values)
    if n < 2:
        return ('stable', 0.0)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return ('stable', 0.0)
    slope = numerator / denominator
    if slope > threshold:
        return ('rising', round(slope, 2))
    elif slope < -threshold:
        return ('falling', round(slope, 2))
    return ('stable', round(slope, 2))


def _score_trends(entries: List[Dict], stage: str = 'initial') -> Dict[str, Dict]:
    """各スコアキーごとにトレンドを計算（ステージ考慮）"""
    config = STAGE_CONFIG[stage]
    threshold = config['trend_threshold']
    min_data = config['min_data_for_trend']
    trends = {}
    for key in SCORE_KEYS:
        values = [e['scores'].get(key, 0) for e in entries if e.get('scores')]
        if len(values) >= min_data:
            direction, slope = _compute_trend(values, threshold)
        else:
            direction, slope = _compute_trend(values, threshold)
            if direction != 'stable':
                direction = direction + '_tentative'
        current = values[-1] if values else 0
        trends[key] = {'direction': direction, 'slope': slope, 'current': current,
                        'min': min(values) if values else 0, 'max': max(values) if values else 0,
                        'count': len(values)}
    return trends


def _is_cooldown_entry(entry: Dict, prev_entry: Optional[Dict]) -> bool:
    """前エントリがピーク状態（eros>=8 or engagement>=9）の場合、
    今回エントリの全体的なマイナスデルタはクールダウン（自然回帰）である可能性が高い。
    カテゴリ効果評価から除外すべきか判定する。

    根拠: laura-analystの発見 - reassuranceの-23は統計的錯覚。
    erosピーク(9)後の自然回帰をreassuranceの「逆効果」と誤判定していた。"""
    if prev_entry is None:
        return False
    prev_scores = prev_entry.get('scores', {})
    deltas = entry.get('score_deltas') or {}
    if not deltas:
        return False
    # 前エントリでeros>=8 or engagement>=9（ピーク状態）
    is_prev_peak = prev_scores.get('eros', 0) >= 8 or prev_scores.get('engagement', 0) >= 9
    if not is_prev_peak:
        return False
    # 今回のデルタが全体的にマイナス（3つ以上のスコアが下降）
    neg_count = sum(1 for v in deltas.values() if v < 0)
    return neg_count >= 3


def _category_effectiveness(entries: List[Dict]) -> Dict[str, Dict]:
    """トリガーカテゴリ別の効果を集計（修飾タグ考慮、クールダウン除外）"""
    stats: Dict[str, Dict] = {}
    for idx, e in enumerate(entries):
        trigger = e.get('trigger')
        if not trigger:
            continue
        cat = trigger.get('category', 'unknown')
        modifiers = trigger.get('modifiers', [])
        deltas = e.get('score_deltas') or {}
        if not deltas:
            continue
        if cat not in stats:
            stats[cat] = {'count': 0, 'total_positive': 0.0, 'total_negative': 0.0,
                          'response_times': [], 'hours': [],
                          'with_escalation': [], 'without_escalation': [],
                          'spontaneous_count': 0, 'entries': []}
        stats[cat]['count'] += 1
        pos_effect = sum(max(0, v) for v in deltas.values())
        neg_effect = sum(min(0, v) for v in deltas.values())
        stats[cat]['total_positive'] += pos_effect
        stats[cat]['total_negative'] += neg_effect
        if '+escalation' in modifiers:
            stats[cat]['with_escalation'].append({'positive': pos_effect, 'negative': neg_effect})
        else:
            stats[cat]['without_escalation'].append({'positive': pos_effect, 'negative': neg_effect})
        if '+spontaneous' in modifiers:
            stats[cat]['spontaneous_count'] += 1
        stats[cat]['entries'].append({
            'modifiers': modifiers, 'deltas': deltas, 'positive': pos_effect, 'negative': neg_effect,
        })
        rt = trigger.get('response_time_min')
        if rt is not None:
            stats[cat]['response_times'].append(rt)
        sent_at = trigger.get('sent_at')
        if sent_at:
            try:
                h = datetime.fromisoformat(sent_at).hour
                stats[cat]['hours'].append(h)
            except (ValueError, TypeError):
                pass
    result = {}
    for cat, s in stats.items():
        n = s['count']
        esc = s['with_escalation']
        no_esc = s['without_escalation']
        result[cat] = {
            'count': n,
            'avg_positive': round(s['total_positive'] / n, 1) if n else 0,
            'avg_negative': round(s['total_negative'] / n, 1) if n else 0,
            'avg_response_min': round(sum(s['response_times']) / len(s['response_times'])) if s['response_times'] else None,
            'best_hours': s['hours'],
            'escalation_avg_positive': round(sum(e['positive'] for e in esc) / len(esc), 1) if esc else None,
            'escalation_avg_negative': round(sum(e['negative'] for e in esc) / len(esc), 1) if esc else None,
            'no_escalation_avg_positive': round(sum(e['positive'] for e in no_esc) / len(no_esc), 1) if no_esc else None,
            'no_escalation_avg_negative': round(sum(e['negative'] for e in no_esc) / len(no_esc), 1) if no_esc else None,
            'spontaneous_count': s['spontaneous_count'],
        }
    return result


def _detect_attachment_issues(entries: List[Dict]) -> Dict:
    """愛着パターンの問題を検出"""
    anxious_count = sum(1 for e in entries if e.get('attachment') == 'anxious')
    avoidant_count = sum(1 for e in entries if e.get('attachment') == 'avoidant')
    consecutive_anxious = 0
    max_consecutive_anxious = 0
    for e in entries:
        if e.get('attachment') == 'anxious':
            consecutive_anxious += 1
            max_consecutive_anxious = max(max_consecutive_anxious, consecutive_anxious)
        else:
            consecutive_anxious = 0
    return {
        'anxious_count': anxious_count,
        'avoidant_count': avoidant_count,
        'max_consecutive_anxious': max_consecutive_anxious,
    }


def _detect_rapid_changes(entries: List[Dict]) -> List[Dict]:
    """スコアの急変（±3以上）を検出"""
    changes = []
    for e in entries:
        deltas = e.get('score_deltas') or {}
        for key, delta in deltas.items():
            if abs(delta) >= 3:
                changes.append({
                    'timestamp': e.get('timestamp'),
                    'metric': key,
                    'delta': delta,
                    'new_value': e.get('scores', {}).get(key),
                    'trigger_category': (e.get('trigger') or {}).get('category'),
                })
    return changes


def _compute_communication_gaps(entries: List[Dict]) -> List[Dict]:
    """通信ギャップ（長時間未連絡）を検出"""
    gaps = []
    for i in range(1, len(entries)):
        try:
            t1 = datetime.fromisoformat(entries[i - 1]['timestamp'])
            t2 = datetime.fromisoformat(entries[i]['timestamp'])
            gap_hours = (t2 - t1).total_seconds() / 3600
            if gap_hours >= 12:
                gaps.append({
                    'from': entries[i - 1]['timestamp'],
                    'to': entries[i]['timestamp'],
                    'hours': round(gap_hours, 1),
                })
        except (ValueError, TypeError, KeyError):
            pass
    return gaps


def _best_response_hours(entries: List[Dict]) -> List[int]:
    """応答時間が短い時間帯を特定"""
    hour_times: Dict[int, List[float]] = {}
    for e in entries:
        trigger = e.get('trigger')
        if not trigger:
            continue
        rt = trigger.get('response_time_min')
        sent_at = trigger.get('sent_at')
        if rt is not None and sent_at:
            try:
                h = datetime.fromisoformat(sent_at).hour
                hour_times.setdefault(h, []).append(rt)
            except (ValueError, TypeError):
                pass
    if not hour_times:
        return []
    avg_by_hour = {h: sum(ts) / len(ts) for h, ts in hour_times.items() if ts}
    sorted_hours = sorted(avg_by_hour.items(), key=lambda x: x[1])
    return [h for h, _ in sorted_hours[:3]]


def _detect_laura_initiative(entries: List[Dict]) -> Dict:
    """Laura側の自発的行動を検出・評価（相手のイニシアチブは関係の健全さの指標）"""
    spontaneous_entries = [e for e in entries if e.get('trigger') is None]
    initiative_modifiers = []
    for e in entries:
        trigger = e.get('trigger')
        if trigger and '+initiative' in trigger.get('modifiers', []):
            initiative_modifiers.append(e)
    return {
        'spontaneous_count': len(spontaneous_entries),
        'initiative_modifier_count': len(initiative_modifiers),
        'total_entries': len(entries),
        'initiative_ratio': round(len(spontaneous_entries) / len(entries), 2) if entries else 0,
    }


def _detect_vulnerable_sharing(entries: List[Dict]) -> List[Dict]:
    """脆弱性の自己開示（vulnerable）を検出"""
    indicators = ['family', 'parents', 'alone', 'scared', 'afraid', 'hurt', 'cry',
                  'dont have', 'passed away', 'miss my', 'lonely']
    vulnerable = []
    for e in entries:
        note = (e.get('note') or '').lower()
        if any(ind in note for ind in indicators):
            vulnerable.append({
                'timestamp': e.get('timestamp'),
                'note': e.get('note'),
                'scores': e.get('scores', {}),
            })
    return vulnerable


def _detect_nickname_intensity(entries: List[Dict]) -> Dict:
    """呼称パターン変化の検出（Baby→Babyyyyy等の感情強度指標）"""
    patterns = []
    for e in entries:
        note = (e.get('note') or '')
        summary = (e.get('summary') or '')
        text = note + ' ' + summary
        y_count = 0
        for word in text.split():
            lower = word.lower().rstrip('!.,?')
            if lower.startswith('baby') and len(lower) > 4:
                y_count = max(y_count, lower.count('y') - 1)
            elif lower.startswith('bab') and 'y' in lower:
                y_count = max(y_count, lower.count('y'))
        if y_count > 0:
            patterns.append({'timestamp': e.get('timestamp'), 'extra_y': y_count})
    return {
        'occurrences': len(patterns),
        'max_intensity': max((p['extra_y'] for p in patterns), default=0),
        'patterns': patterns,
    }


def _compute_relationship_health(trends: Dict, attachment: Dict, risk_entries: List[Dict],
                                  stage: str = 'initial') -> float:
    """関係健康度スコア（0-10）を計算（ステージ考慮）"""
    config = STAGE_CONFIG[stage]
    total_weight = sum(SCORE_WEIGHTS.values())
    weighted_sum = sum(trends[k]['current'] * SCORE_WEIGHTS[k] for k in SCORE_KEYS if k in trends)
    base_score = weighted_sum / total_weight

    # 愛着不安ペナルティ（ステージ考慮）
    # 初期段階のanxiousはDTR文脈で自然なため、閾値を引き上げ
    anxious_threshold = config['anxious_threshold']
    if attachment['anxious_count'] >= anxious_threshold + 1:
        base_score -= 1.0
    elif attachment['anxious_count'] >= anxious_threshold:
        base_score -= 0.3

    # 回避型は全ステージで深刻
    if attachment['avoidant_count'] >= 1:
        base_score -= 1.5

    # リスクペナルティ（初期段階では緩和）
    caution_count = sum(1 for e in risk_entries if e.get('risk') == 'caution')
    if stage == 'initial':
        if caution_count >= 3:
            base_score -= 0.5
    else:
        if caution_count >= 2:
            base_score -= 0.5

    return round(max(0, min(10, base_score)), 1)


def _generate_advice_items(entries: List[Dict], trends: Dict, cat_effects: Dict,
                            attachment: Dict, rapid_changes: List[Dict],
                            gaps: List[Dict], best_hours: List[int],
                            stage: str = 'initial',
                            laura_initiative: Optional[Dict] = None,
                            vulnerable_entries: Optional[List[Dict]] = None,
                            nickname_data: Optional[Dict] = None) -> List[Dict]:
    """ルールベースでアドバイスアイテムを生成（Laura最適化版・ステージ考慮）"""
    advice = []
    adv_counter = [0]
    config = STAGE_CONFIG[stage]
    total_entries = len(entries)

    def _add(category: str, priority: str, title: str, body: str,
             evidence: Dict, action: str, confidence: str = ''):
        adv_counter[0] += 1
        if not confidence:
            confidence = config['default_confidence']
        advice.append({
            'id': f'adv_{adv_counter[0]:03d}',
            'category': category,
            'priority': priority,
            'title': title,
            'body': body,
            'evidence': evidence,
            'action_suggestion': action,
            'confidence': confidence,
            'stage': stage,
        })

    latest = entries[-1] if entries else {}
    latest_scores = latest.get('scores', {})

    # --- ルール1: intimacy高い + future低い → 将来の話を ---
    # Stafford (2005): 遠距離関係では将来展望の共有が関係維持の鍵
    intimacy_cur = trends.get('intimacy', {}).get('current', 0)
    future_cur = trends.get('future', {}).get('current', 0)
    if intimacy_cur >= 6 and future_cur <= 5:
        _add('action', 'important',
             '将来の話題を増やすタイミング',
             f'親密度({intimacy_cur})に対して将来展望({future_cur})が低い。遠距離関係では「いつか会える」という見通しが関係の支え。',
             {'metric': 'future', 'trend': trends['future']['direction'],
              'value': future_cur, 'delta': f"{trends['future']['slope']:+.1f}"},
             '「日本に来たらどこに行きたい？」「一緒に行きたい場所」など具体的な未来の話題を振る')

    # --- ルール2: sexual+escalation の判定（細分化） ---
    # Lauraのデータから: sexual without escalation = mild positive/neutral
    #                    sexual with escalation + consent = very positive
    #                    sexual with escalation + boundary violation = negative
    if 'sexual' in cat_effects:
        sex_eff = cat_effects['sexual']
        esc_pos = sex_eff.get('escalation_avg_positive')
        esc_neg = sex_eff.get('escalation_avg_negative')
        no_esc_neg = sex_eff.get('no_escalation_avg_negative')

        # +escalation付きsexualで強いマイナスがある場合のみ警告
        if esc_neg is not None and esc_neg < -2:
            conf = _confidence_level(sex_eff['count'], total_entries)
            _add('warning', 'important',
                 '性的エスカレーション時に境界線に注意',
                 f"sexual+escalationの平均マイナス効果が{esc_neg}。Lauraは明確な境界線を持っている（例: 一部のフェティッシュは拒否）。"
                 "相互的なセクシャルコミュニケーションはOKだが、一方的な嗜好の押し付けは逆効果。",
                 {'metric': 'sexual_escalation', 'trend': 'mixed',
                  'value': esc_neg, 'delta': 'N/A'},
                 'Lauraの反応を観察し、嫌がる兆候があればすぐに引く。「A little too much」等のサインを見逃さない',
                 confidence=conf)

        # エスカレーションなしsexualで全体がマイナスでない場合はポジティブフィードバック
        if no_esc_neg is not None and no_esc_neg >= -1 and sex_eff.get('no_escalation_avg_positive', 0) >= 2:
            conf = _confidence_level(sex_eff['count'], total_entries)
            _add('effective', 'info',
                 '相互的な性的コミュニケーションは健全',
                 '性的な話題自体はLauraにとってポジティブ。「sex is the most intimate connection」と語る通り、'
                 '関係の中での性は親密さの一部として受容されている。',
                 {'metric': 'sexual_mutual', 'trend': 'positive',
                  'value': sex_eff.get('no_escalation_avg_positive', 0), 'delta': 'N/A'},
                 '性的な話題はOKだが、Lauraの反応を見ながら徐々に深める。一方的にならないこと',
                 confidence=conf)

    # --- ルール3: eros急変（+5以上）→ 文脈考慮のエスカレーション警告 ---
    eros_spikes = [c for c in rapid_changes if c['metric'] == 'eros' and c['delta'] >= 5]
    if eros_spikes:
        # 急変の文脈を確認: 相互合意の上か一方的か
        spike = eros_spikes[0]
        trigger_cat = spike.get('trigger_category', '')
        if trigger_cat == 'sexual':
            _add('warning', 'info',
                 '性的テンションの急上昇を検出',
                 f"erosが+{spike['delta']}急変。相互的な盛り上がりなら問題ないが、"
                 "急激なペースアップはバーンアウトのリスクがある。翌日のクールダウンを観察すること。",
                 {'metric': 'eros', 'trend': 'spike', 'value': spike.get('new_value', 0),
                  'delta': f"+{spike['delta']}"},
                 '翌日は意図的に感情面の会話を増やし、性的テンション以外の絆も確認する')
        else:
            _add('warning', 'important',
                 '予期しない性的テンション上昇',
                 f"非sexualトリガーでerosが+{spike['delta']}急変。予期しないコンテキストでのエスカレーション。",
                 {'metric': 'eros', 'trend': 'spike', 'value': spike.get('new_value', 0),
                  'delta': f"+{spike['delta']}"},
                 '原因を分析し、意図しないエスカレーションがないか確認する')

    # --- ルール4: 連絡間隔警告（ステージ考慮） ---
    gap_threshold = config['gap_warning_hours']
    long_gaps = [g for g in gaps if g['hours'] >= gap_threshold]
    if long_gaps:
        max_gap = max(g['hours'] for g in long_gaps)
        _add('warning', 'important',
             '連絡間隔が空いている',
             f"最大{max_gap:.0f}時間のギャップを検出。Lauraは内向的で自分からは連絡しにくいタイプのため、"
             "沈黙が長いと不安につながりやすい。",
             {'metric': 'engagement', 'trend': 'gap',
              'value': max_gap, 'delta': 'N/A'},
             'Lauraの時間帯（CET）を意識し、朝（日本の夕方）と夜（日本の深夜）に短い挨拶を欠かさない')

    # --- ルール5: affectionカテゴリの効果（Laura特化閾値） ---
    if 'affection' in cat_effects:
        aff = cat_effects['affection']
        conf = _confidence_level(aff['count'], total_entries)
        if aff['avg_positive'] >= 3:
            _add('effective', 'important' if conf == 'high' else 'info',
                 '愛情表現が最も効果的',
                 f"「affection」カテゴリの平均効果は+{aff['avg_positive']}（{aff['count']}回）。"
                 "Lauraは2年間シングルで愛情に飢えている面があり、直接的な愛情表現への反応が強い。"
                 "+spontaneousの場合さらに効果的。",
                 {'metric': 'affection_effect', 'trend': 'high',
                  'value': aff['avg_positive'], 'delta': 'N/A'},
                 '「I like you」「I miss you」等の直接的な表現を毎日送る。特に相手が求めていないタイミング（+spontaneous）が効果大',
                 confidence=conf)

    # --- ルール6: anxious愛着（ステージ考慮） ---
    anxious_threshold = config['anxious_threshold']
    if attachment['anxious_count'] >= anxious_threshold:
        _add('warning', 'urgent',
             '不安型愛着パターンを検出',
             f"不安型愛着が{attachment['anxious_count']}回出現（閾値: {anxious_threshold}）。",
             {'metric': 'attachment', 'trend': 'anxious',
              'value': attachment['anxious_count'], 'delta': 'N/A'},
             '安心感を与える言葉（「ずっと一緒にいたい」「大丈夫だよ」）を意識的に増やす')
    elif attachment['anxious_count'] >= 1 and stage in ('initial', 'building'):
        # 初期段階のanxiousはDTR文脈で自然 → 警告ではなく参考情報
        _add('status', 'info',
             'DTR関連の不安を検出（正常範囲）',
             f"不安型愛着が{attachment['anxious_count']}回出現。初期段階での「関係の定義」に関する不安は"
             "関係に真剣に向き合っている証拠であり、問題行動ではない。",
             {'metric': 'attachment', 'trend': 'anxious_normal',
              'value': attachment['anxious_count'], 'delta': 'N/A'},
             '不安を否定せず、「距離はあるけど気持ちは変わらない」等で安心感を与える。DTRの結論を急がない',
             confidence='medium')

    # --- ルール7: engagement下降トレンド ---
    eng_dir = trends.get('engagement', {}).get('direction', 'stable')
    if eng_dir in ('falling', 'falling_tentative'):
        pri = 'important' if eng_dir == 'falling' else 'info'
        tent = '（暫定判定・データ不足）' if '_tentative' in eng_dir else ''
        _add('warning', pri,
             f'エンゲージメントが低下傾向{tent}',
             'Lauraの関与度が下がっている。内向的な性格のため、自分からの発信が減る=関心低下の可能性。',
             {'metric': 'engagement', 'trend': eng_dir,
              'value': trends['engagement']['current'], 'delta': f"{trends['engagement']['slope']:+.1f}"},
             '質問形式のメッセージ（interest）や、Lauraの趣味（ジム・映画）に関する話題で関与を促す')

    # --- ルール8: mood上昇トレンド ---
    mood_dir = trends.get('mood', {}).get('direction', 'stable')
    if mood_dir in ('rising', 'rising_tentative'):
        _add('status', 'info',
             '気分は上昇傾向',
             '相手のmoodが改善傾向にある。現在のコミュニケーションスタイルが功を奏している。',
             {'metric': 'mood', 'trend': mood_dir,
              'value': trends['mood']['current'], 'delta': f"{trends['mood']['slope']:+.1f}"},
             '現在のアプローチを維持する')

    # --- ルール9: mood下降トレンド ---
    if mood_dir in ('falling', 'falling_tentative'):
        _add('warning', 'urgent' if mood_dir == 'falling' else 'important',
             '気分が下降傾向',
             '相手のmoodが悪化傾向にある。原因を特定し、対処が必要。',
             {'metric': 'mood', 'trend': mood_dir,
              'value': trends['mood']['current'], 'delta': f"{trends['mood']['slope']:+.1f}"},
             '相手の気持ちに寄り添う会話を増やし、プレッシャーを避ける')

    # --- ルール10: energy低い ---
    if trends.get('energy', {}).get('current', 5) <= 4:
        _add('status', 'info',
             'エネルギーが低め',
             'Lauraのエネルギーが低い。銀行の在宅勤務で疲労がたまっている可能性。毎日のジム通いも体力を使う。',
             {'metric': 'energy', 'trend': trends['energy']['direction'],
              'value': trends['energy']['current'], 'delta': f"{trends['energy']['slope']:+.1f}"},
             '重い話題やDTRを避け、軽い会話やリール共有で負担をかけない')

    # --- ルール11: intimacy上昇中 ---
    int_dir = trends.get('intimacy', {}).get('direction', 'stable')
    if int_dir in ('rising', 'rising_tentative') and trends['intimacy']['current'] >= 4:
        _add('status', 'info',
             '親密度が順調に上昇中',
             f"intimacyが{trends['intimacy']['min']}→{trends['intimacy']['current']}に成長。"
             "Lauraが家族の話（両親の他界）を開示したのは深い信頼の表れ。",
             {'metric': 'intimacy', 'trend': int_dir,
              'value': trends['intimacy']['current'], 'delta': f"{trends['intimacy']['slope']:+.1f}"},
             '自己開示の交換を続ける。Lauraが重い話を共有した時は、感謝と共感を示す')

    # --- ルール12: praiseカテゴリが効果的 ---
    if 'praise' in cat_effects and cat_effects['praise']['avg_positive'] >= 2:
        conf = _confidence_level(cat_effects['praise']['count'], total_entries)
        _add('effective', 'info',
             '褒め言葉が効果的',
             f"praiseカテゴリの平均効果は+{cat_effects['praise']['avg_positive']}（{cat_effects['praise']['count']}回）。",
             {'metric': 'praise_effect', 'trend': 'positive',
              'value': cat_effects['praise']['avg_positive'], 'delta': 'N/A'},
             '外見だけでなく、性格や行動を具体的に褒める（「ジム頑張ってるね」「真面目なところが好き」）',
             confidence=conf)

    # --- ルール13: longing高い + 遠距離 ---
    longing_cur = trends.get('longing', {}).get('current', 0)
    if longing_cur >= 6:
        _add('status', 'important',
             '会いたい気持ちが強い',
             f'longing={longing_cur}。遠距離関係では自然な感情だが、具体的な見通しがないと不安に転じやすい。'
             'Lauraは「If we were living in the same city I would not doubt it」と言っている。',
             {'metric': 'longing', 'trend': trends['longing']['direction'],
              'value': longing_cur, 'delta': f"{trends['longing']['slope']:+.1f}"},
             '「いつか日本に来てね」ではなく、具体的な時期・計画の話をする。オンラインデート（映画同時視聴等）も有効')

    # --- ルール14: ds急変（文脈考慮） ---
    ds_spikes = [c for c in rapid_changes if c['metric'] == 'ds' and c['delta'] >= 2]
    if ds_spikes:
        # LauraはD/s嗜好を持つため、合意の上でのds上昇は問題ではない
        _add('status', 'info',
             'D/sダイナミクスの変化',
             f"D/sスコアが+{ds_spikes[0]['delta']}変化。Lauraは明確なD/s嗜好（被支配願望）を持っているため、"
             "合意の上での上昇は関係の自然な深まり。ただし境界線（OK: choke, spank / NG: armpit）は厳守。",
             {'metric': 'ds', 'trend': 'spike',
              'value': ds_spikes[0].get('new_value', 0), 'delta': f"+{ds_spikes[0]['delta']}"},
             'Lauraが自ら述べた嗜好の範囲内で進める。新しい行為は必ず事前に確認する')

    # --- ルール15: 最も効果的なカテゴリ（信頼度付き） ---
    if cat_effects:
        best_cat = max(cat_effects.items(), key=lambda x: x[1]['avg_positive'])
        conf = _confidence_level(best_cat[1]['count'], total_entries)
        label = f'（参考）' if conf == 'insufficient' else ''
        _add('effective', 'info',
             f'最も効果的なアプローチ: {best_cat[0]}{label}',
             f"「{best_cat[0]}」カテゴリが平均+{best_cat[1]['avg_positive']}で最も効果的"
             f"（{best_cat[1]['count']}回使用、信頼度: {conf}）。",
             {'metric': 'best_category', 'trend': 'positive',
              'value': best_cat[1]['avg_positive'], 'delta': 'N/A'},
             f'「{best_cat[0]}」系のメッセージを意識的に増やす',
             confidence=conf)

    # --- ルール16: 最適な時間帯 ---
    if best_hours:
        hours_str = '、'.join(f'{h}時' for h in best_hours)
        _add('timing', 'info',
             f'レスポンスが良い時間帯: {hours_str}',
             f'応答速度が最も速い時間帯は{hours_str}（JST）。Lauraの現地時間を意識すること（CET=JST-8h）。',
             {'metric': 'response_time', 'trend': 'optimal',
              'value': best_hours[0], 'delta': 'N/A'},
             f'{hours_str}頃にメッセージを送るようにする')

    # --- ルール17: playfulness低下 ---
    play_dir = trends.get('playfulness', {}).get('direction', 'stable')
    if play_dir in ('falling', 'falling_tentative'):
        _add('action', 'info',
             '遊び心が減少傾向',
             '会話のplayfulnessが下がっている。Lauraは😂やリアクションを多用する性格で遊び心を好む。',
             {'metric': 'playfulness', 'trend': play_dir,
              'value': trends['playfulness']['current'], 'delta': f"{trends['playfulness']['slope']:+.1f}"},
             'リール共有、ミーム、からかい等を増やす。Lauraのジムネタ等を使ったユーモアも有効')

    # --- ルール18: riskがcaution連続 ---
    recent_risks = [e.get('risk') for e in entries[-3:]]
    if recent_risks.count('caution') >= 2:
        _add('warning', 'urgent',
             'リスク警告が頻発',
             '直近でcautionレベルのリスクが複数回検出。境界線を越えた行動が続いている可能性。',
             {'metric': 'risk', 'trend': 'elevated',
              'value': recent_risks.count('caution'), 'delta': 'N/A'},
             'エスカレーションを一旦停止し、感情面の会話で安定した基盤を築くことを優先する')

    # --- ルール19: future下降 ---
    fut_dir = trends.get('future', {}).get('direction', 'stable')
    if fut_dir in ('falling', 'falling_tentative'):
        _add('warning', 'important',
             '将来展望が下降傾向',
             '将来スコアが下がっている。遠距離関係で将来展望の低下は関係崩壊の前兆になりうる（Stafford, 2005）。',
             {'metric': 'future', 'trend': fut_dir,
              'value': trends['future']['current'], 'delta': f"{trends['future']['slope']:+.1f}"},
             '将来について率直に話し合う。「いつか」ではなく具体的な時期を提示できると理想的')

    # --- ルール20: 全体的に安定 ---
    stable_dirs = ('stable',)
    all_stable = all(trends[k]['direction'] in stable_dirs for k in SCORE_KEYS if k in trends)
    if all_stable and len(entries) >= 5:
        _add('status', 'info',
             '関係は安定期',
             '全てのパラメーターが安定している。良い状態だが、遠距離関係ではマンネリ化が距離感の増大につながりやすい。',
             {'metric': 'overall', 'trend': 'stable', 'value': 0, 'delta': 'N/A'},
             '新しい共有体験（映画同時視聴、オンラインゲーム、お互いの街を紹介等）を試す')

    # --- ルール21: reassuranceの効果 ---
    if 'reassurance' in cat_effects:
        eff = cat_effects['reassurance']
        conf = _confidence_level(eff['count'], total_entries)
        # reassuranceはpost-high cooldown時にネガティブに見える場合がある → 文脈チェック
        if eff['avg_positive'] >= 1:
            _add('effective', 'info',
                 '安心感メッセージの効果',
                 f"reassuranceカテゴリの効果は+{eff['avg_positive']}（{eff['count']}回）。"
                 "注意: クールダウン期のデルタは自然な下降であり、メッセージの逆効果ではない場合がある。",
                 {'metric': 'reassurance_effect', 'trend': 'positive',
                  'value': eff['avg_positive'], 'delta': 'N/A'},
                 '独占性と一途さを伝えるメッセージを適度に送る。ただし頻度が高すぎると圧になる',
                 confidence=conf)

    # --- ルール22: interestカテゴリの効果 ---
    if 'interest' in cat_effects and cat_effects['interest']['avg_positive'] >= 1:
        conf = _confidence_level(cat_effects['interest']['count'], total_entries)
        _add('effective', 'info',
             '興味・関心を示すことが効果的',
             'Lauraに対する興味や関心を示すメッセージが良い反応を得ている。内向的で聞き上手なLauraは質問されると饒舌になる。',
             {'metric': 'interest_effect', 'trend': 'positive',
              'value': cat_effects['interest']['avg_positive'], 'delta': 'N/A'},
             'ジム、映画、仕事、スイスの生活について質問する。ペルー文化の話も高反応',
             confidence=conf)

    # --- ルール23: 連絡ギャップ頻度 ---
    medium_gaps = [g for g in gaps if 12 <= g['hours'] < gap_threshold]
    if len(medium_gaps) >= 3:
        _add('action', 'info',
             '半日以上の空白が頻発',
             f'{len(medium_gaps)}回の12時間以上ギャップを検出。時差8時間のため夜間の空白は自然だが、起きている時間帯の空白は要注意。',
             {'metric': 'gap_frequency', 'trend': 'frequent',
              'value': len(medium_gaps), 'delta': 'N/A'},
             'Lauraの朝（JST夕方）とLauraの夜（JST深夜）に挨拶メッセージを習慣化する')

    # --- ルール24: intimacy低い ---
    if trends.get('intimacy', {}).get('current', 5) <= 3:
        _add('action', 'important',
             '親密度がまだ低い',
             '親密度が初期段階。自己開示の交換がまだ浅い。',
             {'metric': 'intimacy', 'trend': trends['intimacy']['direction'],
              'value': trends['intimacy']['current'], 'delta': f"{trends['intimacy']['slope']:+.1f}"},
             '自分のプライベートな話（家族、夢、不安）を先に開示し、Lauraにも安全に開示できる環境を作る')

    # --- ルール25: eros-intimacy バランス ---
    eros_val = trends.get('eros', {}).get('current', 0)
    intimacy_val = trends.get('intimacy', {}).get('current', 0)
    if eros_val >= 6 and intimacy_val <= 4:
        _add('warning', 'important',
             '性的関心と感情的親密度のアンバランス',
             f'eros({eros_val})がintimacy({intimacy_val})を大幅に上回っている。'
             'Lauraは「関係の中のセックス」を重視する価値観。感情面の絆が先にないとエロスは長続きしない。',
             {'metric': 'balance', 'trend': 'imbalanced',
              'value': eros_val - intimacy_val, 'delta': 'N/A'},
             '性的な話題を控えめにし、感情面の会話（自己開示、将来の話）を優先する')

    # --- ルール26: Laura自発行動の追跡（新規） ---
    if laura_initiative:
        ratio = laura_initiative['initiative_ratio']
        if ratio >= 0.3:
            _add('status', 'info',
                 'Lauraの自発性が高い',
                 f"Lauraの自発的メッセージ比率は{ratio:.0%}。内向的な性格を考慮すると非常に高い関与度。"
                 "自分から写真を送る、自分から話題を振るなどの行動が見られる。",
                 {'metric': 'laura_initiative', 'trend': 'positive',
                  'value': ratio, 'delta': 'N/A'},
                 'Lauraの自発的な行動には必ずポジティブに反応する。それが次の自発行動を促す')
        elif ratio <= 0.1 and total_entries >= 10:
            _add('warning', 'info',
                 'Lauraの自発性が低下',
                 f"自発的メッセージ比率が{ratio:.0%}。全てユーザー起点の会話になっている。",
                 {'metric': 'laura_initiative', 'trend': 'low',
                  'value': ratio, 'delta': 'N/A'},
                 '会話を一方通行にしない。質問を投げて相手にターンを渡す。返信を急かさない')

    # --- ルール27: 脆弱性開示への反応追跡（新規） ---
    if vulnerable_entries and len(vulnerable_entries) >= 1:
        _add('status', 'important',
             '深い自己開示が発生',
             f"Lauraが{len(vulnerable_entries)}回の脆弱性開示を行った。"
             "両親の他界、一人暮らしの孤独感など。これは深い信頼の表れであり、適切な受容が極めて重要。",
             {'metric': 'vulnerable', 'trend': 'trust_signal',
              'value': len(vulnerable_entries), 'delta': 'N/A'},
             '重い話を共有してくれた時は「話してくれてありがとう」「一人にしないよ」等で受容を示す。アドバイスはしない')

    # --- ルール28: +spontaneous修飾タグの効果（新規） ---
    spontaneous_effects = []
    for e in entries:
        trigger = e.get('trigger')
        if trigger and '+spontaneous' in trigger.get('modifiers', []):
            deltas = e.get('score_deltas') or {}
            if deltas:
                spontaneous_effects.append(sum(max(0, v) for v in deltas.values()))
    if spontaneous_effects and len(spontaneous_effects) >= 2:
        avg_spon = round(sum(spontaneous_effects) / len(spontaneous_effects), 1)
        if avg_spon >= 3:
            _add('effective', 'info',
                 '自発的メッセージの効果が高い',
                 f"+spontaneous修飾付きメッセージの平均効果は+{avg_spon}（{len(spontaneous_effects)}回）。"
                 "相手が求めていない時に自発的に送るメッセージは効果が高い。",
                 {'metric': 'spontaneous_effect', 'trend': 'positive',
                  'value': avg_spon, 'delta': 'N/A'},
                 '「ふと思い出した」「急に会いたくなった」等、唐突だが温かいメッセージを積極的に送る')

    # --- ルール29: 呼称パターン変化（新規） ---
    if nickname_data and nickname_data['occurrences'] >= 2:
        _add('status', 'info',
             '呼称の強度変化を検出',
             f"Lauraの「Baby→Babyyyyy」パターンが{nickname_data['occurrences']}回出現"
             f"（最大y数: {nickname_data['max_intensity']}）。yの数が多いほど感情の高まりを示す。",
             {'metric': 'nickname_intensity', 'trend': 'positive',
              'value': nickname_data['max_intensity'], 'delta': 'N/A'},
             '感情が高い時のサインとして活用。この状態で送るaffectionメッセージは効果倍増')

    # --- ルール30: カテゴリ反復減衰（新規） ---
    if len(entries) >= 4:
        recent_cats = []
        for e in entries[-4:]:
            t = e.get('trigger')
            if t:
                recent_cats.append(t.get('category'))
        if len(recent_cats) >= 3:
            from collections import Counter
            cat_counts = Counter(recent_cats)
            for cat, count in cat_counts.items():
                if count >= 3 and cat:
                    _add('action', 'info',
                         f'「{cat}」が3回連続 - 新鮮さが薄れる可能性',
                         f"直近4メッセージ中{count}回が「{cat}」カテゴリ。同じアプローチの反復は効果が減衰する傾向がある。",
                         {'metric': 'category_repetition', 'trend': 'diminishing',
                          'value': count, 'delta': 'N/A'},
                         f'「{cat}」以外のカテゴリ（例: interest, humor, cultural）を意識的に使って変化をつける')

    # 優先度順にソート（urgent > important > info）
    priority_order = {'urgent': 0, 'important': 1, 'info': 2}
    advice.sort(key=lambda x: priority_order.get(x['priority'], 3))

    # 最低5件、最大15件に制限
    if len(advice) < 5:
        generic_advice = [
            ('status', 'info', 'データ収集中',
             f'現在{total_entries}件のデータで分析中。信頼度の高い判定には最低30件が必要。継続的な記録が重要。',
             {'metric': 'data', 'trend': 'insufficient', 'value': total_entries, 'delta': 'N/A'},
             'データが蓄積されるまで記録を続ける'),
            ('action', 'info', '多様なコミュニケーション',
             '様々なタイプのメッセージを試して、Lauraに何が効果的かを探る段階。',
             {'metric': 'variety', 'trend': 'exploring', 'value': 0, 'delta': 'N/A'},
             '褒め言葉、質問、愛情表現、ユーモアなど様々なアプローチを試す'),
            ('timing', 'info', '応答パターンを観察中',
             'Lauraの応答パターンが十分に蓄積されていない。時差（8時間）を考慮した最適な送信時間帯を探索中。',
             {'metric': 'response_pattern', 'trend': 'collecting', 'value': 0, 'delta': 'N/A'},
             '応答時間を意識して、Lauraが活発な時間帯（CET日中=JST夕方〜夜）を探る'),
        ]
        for cat, pri, title, body, ev, act in generic_advice:
            if len(advice) >= 5:
                break
            adv_counter[0] += 1
            advice.append({
                'id': f'adv_{adv_counter[0]:03d}',
                'category': cat, 'priority': pri, 'title': title,
                'body': body, 'evidence': ev, 'action_suggestion': act,
                'confidence': 'low', 'stage': stage,
            })

    return advice[:15]


def generate_advice(days: int) -> Dict:
    """アドバイスAPIのメインロジック（Laura最適化版）"""
    if not EMOTION_DATA_FILE.exists():
        return {'error': 'no data'}

    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    entries = [normalize_entry(e) for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]

    if not entries:
        return {'error': 'no data in range'}

    # 関係ステージ検出
    stage = detect_relationship_stage(entries)

    # 各種分析（ステージ考慮）
    trends = _score_trends(entries, stage)
    cat_effects = _category_effectiveness(entries)
    attachment = _detect_attachment_issues(entries)
    rapid_changes = _detect_rapid_changes(entries)
    gaps = _compute_communication_gaps(entries)
    best_hours = _best_response_hours(entries)

    # Laura固有の分析
    laura_initiative = _detect_laura_initiative(entries)
    vulnerable_entries = _detect_vulnerable_sharing(entries)
    nickname_data = _detect_nickname_intensity(entries)

    # 関係健康度（ステージ考慮）
    health = _compute_relationship_health(trends, attachment, entries, stage)

    # トレンド方向の決定（tentativeを含む）
    rising_count = sum(1 for k in SCORE_KEYS
                       if trends.get(k, {}).get('direction', '').startswith('rising'))
    falling_count = sum(1 for k in SCORE_KEYS
                        if trends.get(k, {}).get('direction', '').startswith('falling'))
    if rising_count > falling_count + 2:
        trend_dir = 'improving'
    elif falling_count > rising_count + 2:
        trend_dir = 'declining'
    else:
        trend_dir = 'stable'

    # ステージ考慮のキーインサイト生成
    stage_labels = {
        'initial': '初期段階（探索期）',
        'building': '関係構築期',
        'establishing': '確立期',
        'stable': '安定期',
    }
    stage_label = stage_labels.get(stage, stage)

    if health >= 8:
        key_insight = f'【{stage_label}】関係は非常に良好。現在のアプローチを維持しつつ、新鮮さを保つことが大切。'
    elif health >= 6:
        key_insight = f'【{stage_label}】関係は概ね健全。{stage_label}としては順調に進展している。'
    elif health >= 4:
        key_insight = f'【{stage_label}】改善が必要な領域がある。特にintimacyとfutureの向上が鍵。'
    else:
        key_insight = f'【{stage_label}】関係に課題が見られる。コミュニケーションの質と量の改善が急務。'

    # アドバイスアイテム生成（全パラメーター渡し）
    advice_items = _generate_advice_items(
        entries, trends, cat_effects, attachment, rapid_changes, gaps, best_hours,
        stage=stage,
        laura_initiative=laura_initiative,
        vulnerable_entries=vulnerable_entries,
        nickname_data=nickname_data,
    )

    first_ts = entries[0].get('timestamp', '')
    last_ts = entries[-1].get('timestamp', '')

    return {
        'generated_at': datetime.now(JST).isoformat(),
        'data_range': {
            'from': first_ts,
            'to': last_ts,
            'entry_count': len(entries),
        },
        'stage': stage,
        'advice': advice_items,
        'summary': {
            'relationship_health': health,
            'trend_direction': trend_dir,
            'key_insight': key_insight,
        },
        'meta': {
            'laura_initiative_ratio': laura_initiative['initiative_ratio'],
            'vulnerable_disclosures': len(vulnerable_entries),
            'nickname_intensity_max': nickname_data['max_intensity'] if nickname_data else 0,
        },
    }


@app.get('/api/emotion/advice')
async def api_emotion_advice(days: int = Query(default=30, ge=1, le=90)):
    """ルールベースのアドバイス生成API"""
    cache_key = f'advice_{days}'
    cached = get_cached(cache_key)
    if cached:
        return JSONResponse(cached)

    result = generate_advice(days)
    if 'error' in result:
        return JSONResponse(result, status_code=404)

    set_cache(cache_key, result)
    return JSONResponse(result)


# ===== エントリポイント =====
if __name__ == '__main__':
    print(f"[INFO] SwitchBot 環境ダッシュボード起動: http://localhost:8765")
    uvicorn.run(app, host='0.0.0.0', port=8765)
