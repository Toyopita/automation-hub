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
        'gap_warning_hours': 36,       # ギャップ警告を緩和（初期はリズム未確立）
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


def _score_trends(entries: List[Dict]) -> Dict[str, Dict]:
    """各スコアキーごとにトレンドを計算"""
    trends = {}
    for key in SCORE_KEYS:
        values = [e['scores'].get(key, 0) for e in entries if e.get('scores')]
        direction, slope = _compute_trend(values)
        current = values[-1] if values else 0
        trends[key] = {'direction': direction, 'slope': slope, 'current': current,
                        'min': min(values) if values else 0, 'max': max(values) if values else 0}
    return trends


def _category_effectiveness(entries: List[Dict]) -> Dict[str, Dict]:
    """トリガーカテゴリ別の効果を集計"""
    stats: Dict[str, Dict] = {}
    for e in entries:
        trigger = e.get('trigger')
        if not trigger:
            continue
        cat = trigger.get('category', 'unknown')
        deltas = e.get('score_deltas') or {}
        if not deltas:
            continue
        if cat not in stats:
            stats[cat] = {'count': 0, 'total_positive': 0.0, 'total_negative': 0.0,
                          'response_times': [], 'hours': []}
        stats[cat]['count'] += 1
        stats[cat]['total_positive'] += sum(max(0, v) for v in deltas.values())
        stats[cat]['total_negative'] += sum(min(0, v) for v in deltas.values())
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
        result[cat] = {
            'count': n,
            'avg_positive': round(s['total_positive'] / n, 1) if n else 0,
            'avg_negative': round(s['total_negative'] / n, 1) if n else 0,
            'avg_response_min': round(sum(s['response_times']) / len(s['response_times'])) if s['response_times'] else None,
            'best_hours': s['hours'],
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


def _compute_relationship_health(trends: Dict, attachment: Dict, risk_entries: List[Dict]) -> float:
    """関係健康度スコア（0-10）を計算"""
    total_weight = sum(SCORE_WEIGHTS.values())
    weighted_sum = sum(trends[k]['current'] * SCORE_WEIGHTS[k] for k in SCORE_KEYS if k in trends)
    base_score = weighted_sum / total_weight

    # 愛着不安ペナルティ
    if attachment['anxious_count'] >= 3:
        base_score -= 1.0
    elif attachment['anxious_count'] >= 1:
        base_score -= 0.5

    # リスクペナルティ
    caution_count = sum(1 for e in risk_entries if e.get('risk') == 'caution')
    if caution_count >= 2:
        base_score -= 0.5

    return round(max(0, min(10, base_score)), 1)


def _generate_advice_items(entries: List[Dict], trends: Dict, cat_effects: Dict,
                            attachment: Dict, rapid_changes: List[Dict],
                            gaps: List[Dict], best_hours: List[int]) -> List[Dict]:
    """ルールベースでアドバイスアイテムを生成（最低20ルール）"""
    advice = []
    adv_counter = [0]

    def _add(category: str, priority: str, title: str, body: str,
             evidence: Dict, action: str):
        adv_counter[0] += 1
        advice.append({
            'id': f'adv_{adv_counter[0]:03d}',
            'category': category,
            'priority': priority,
            'title': title,
            'body': body,
            'evidence': evidence,
            'action_suggestion': action,
        })

    latest = entries[-1] if entries else {}
    latest_scores = latest.get('scores', {})

    # --- ルール1: intimacy高い + future低い → 将来の話を ---
    if trends.get('intimacy', {}).get('current', 0) >= 7 and trends.get('future', {}).get('current', 0) <= 4:
        _add('action', 'important',
             '将来の話題を増やすタイミング',
             '親密度は高いが、将来に対する意識が低い。関係を深めるには、将来のビジョンを共有する会話が効果的。',
             {'metric': 'future', 'trend': trends['future']['direction'],
              'value': trends['future']['current'], 'delta': f"{trends['future']['slope']:+.1f}"},
             '「一緒に行きたい場所」「将来やりたいこと」など未来志向の話題を振る')

    # --- ルール2: eros急変（+5以上） → エスカレーション警告 ---
    eros_spikes = [c for c in rapid_changes if c['metric'] == 'eros' and c['delta'] >= 5]
    if eros_spikes:
        _add('warning', 'urgent',
             '性的エスカレーションに注意',
             f"erosが短期間で+{eros_spikes[0]['delta']}急変。急激なエスカレーションはバーンアウトのリスクがある。",
             {'metric': 'eros', 'trend': 'spike', 'value': eros_spikes[0].get('new_value', 0),
              'delta': f"+{eros_spikes[0]['delta']}"},
             'ペースを落とし、感情面の会話も意識的に増やす')

    # --- ルール3: 24h以上ギャップ → 連絡間隔警告 ---
    long_gaps = [g for g in gaps if g['hours'] >= 24]
    if long_gaps:
        _add('warning', 'important',
             '連絡間隔が空いている',
             f"最大{max(g['hours'] for g in long_gaps):.0f}時間のギャップを検出。長い沈黙は不安を生む可能性がある。",
             {'metric': 'engagement', 'trend': 'gap',
              'value': max(g['hours'] for g in long_gaps), 'delta': 'N/A'},
             '忙しくても短いメッセージ（おはよう、おやすみ）を欠かさない')

    # --- ルール4: affectionカテゴリの効果が高い ---
    if 'affection' in cat_effects and cat_effects['affection']['avg_positive'] >= 4:
        _add('effective', 'info',
             '愛情表現が最も効果的',
             f"「affection」カテゴリの平均効果は+{cat_effects['affection']['avg_positive']}。愛情を直接伝えるメッセージが一番響いている。",
             {'metric': 'affection_effect', 'trend': 'high',
              'value': cat_effects['affection']['avg_positive'], 'delta': 'N/A'},
             '「好き」「会いたい」など直接的な愛情表現を継続する')

    # --- ルール5: anxious愛着2回以上 → 安心感 ---
    if attachment['anxious_count'] >= 2:
        _add('warning', 'urgent',
             '不安型愛着パターンを検出',
             f"不安型愛着が{attachment['anxious_count']}回出現。相手が関係の安定性に不安を感じている。",
             {'metric': 'attachment', 'trend': 'anxious',
              'value': attachment['anxious_count'], 'delta': 'N/A'},
             '安心感を与える言葉（「ずっと一緒にいたい」「大丈夫だよ」）を意識的に増やす')

    # --- ルール6: engagement下降トレンド ---
    if trends.get('engagement', {}).get('direction') == 'falling':
        _add('warning', 'important',
             'エンゲージメントが低下傾向',
             '関与度が下がっている。会話への参加意欲が減少している可能性がある。',
             {'metric': 'engagement', 'trend': 'falling',
              'value': trends['engagement']['current'], 'delta': f"{trends['engagement']['slope']:+.1f}"},
             '質問形式のメッセージや、相手の興味ある話題を振って関与を促す')

    # --- ルール7: mood上昇トレンド → ポジティブステータス ---
    if trends.get('mood', {}).get('direction') == 'rising':
        _add('status', 'info',
             '気分は上昇傾向',
             '相手のmoodが改善傾向にある。現在のコミュニケーションスタイルが功を奏している。',
             {'metric': 'mood', 'trend': 'rising',
              'value': trends['mood']['current'], 'delta': f"{trends['mood']['slope']:+.1f}"},
             '現在のアプローチを維持する')

    # --- ルール8: mood下降トレンド ---
    if trends.get('mood', {}).get('direction') == 'falling':
        _add('warning', 'urgent',
             '気分が下降傾向',
             '相手のmoodが悪化傾向にある。原因を特定し、対処が必要。',
             {'metric': 'mood', 'trend': 'falling',
              'value': trends['mood']['current'], 'delta': f"{trends['mood']['slope']:+.1f}"},
             '相手の気持ちに寄り添う会話を増やし、プレッシャーを避ける')

    # --- ルール9: energy低い（<=3） ---
    if trends.get('energy', {}).get('current', 5) <= 3:
        _add('status', 'important',
             'エネルギーが低い',
             '相手のエネルギーレベルが低い。疲労や仕事のストレスが影響している可能性。',
             {'metric': 'energy', 'trend': trends['energy']['direction'],
              'value': trends['energy']['current'], 'delta': f"{trends['energy']['slope']:+.1f}"},
             '重い話題を避け、軽い会話や癒し系のメッセージを心がける')

    # --- ルール10: intimacy上昇中 ---
    if trends.get('intimacy', {}).get('direction') == 'rising' and trends['intimacy']['current'] >= 5:
        _add('status', 'info',
             '親密度が順調に上昇中',
             f"intimacyが{trends['intimacy']['min']}→{trends['intimacy']['current']}に成長。信頼関係が着実に構築されている。",
             {'metric': 'intimacy', 'trend': 'rising',
              'value': trends['intimacy']['current'], 'delta': f"{trends['intimacy']['slope']:+.1f}"},
             '自己開示を増やし、より深い話題にも踏み込んでみる')

    # --- ルール11: sexualカテゴリの効果がマイナス ---
    if 'sexual' in cat_effects and cat_effects['sexual']['avg_negative'] < -2:
        _add('warning', 'important',
             '性的メッセージが逆効果',
             f"sexualカテゴリの平均マイナス効果が{cat_effects['sexual']['avg_negative']}。性的メッセージが関係にネガティブな影響を与えている。",
             {'metric': 'sexual_effect', 'trend': 'negative',
              'value': cat_effects['sexual']['avg_negative'], 'delta': 'N/A'},
             '性的な話題のペースを落とし、感情面の会話を優先する')

    # --- ルール12: praiseカテゴリが効果的 ---
    if 'praise' in cat_effects and cat_effects['praise']['avg_positive'] >= 3:
        _add('effective', 'info',
             '褒め言葉が効果的',
             f"praiseカテゴリの平均効果は+{cat_effects['praise']['avg_positive']}。褒めることで相手のmoodとengagementが上がる。",
             {'metric': 'praise_effect', 'trend': 'positive',
              'value': cat_effects['praise']['avg_positive'], 'delta': 'N/A'},
             '具体的な褒め言葉（「その笑顔が好き」「すごく似合ってる」）を日常的に')

    # --- ルール13: longing高い（>=7）+ 距離問題 ---
    if trends.get('longing', {}).get('current', 0) >= 7:
        _add('status', 'important',
             '強い渇望感を検出',
             '会いたい気持ちが非常に強い。長距離関係の場合、この感情が不安に転じるリスクがある。',
             {'metric': 'longing', 'trend': trends['longing']['direction'],
              'value': trends['longing']['current'], 'delta': f"{trends['longing']['slope']:+.1f}"},
             '具体的な再会プランや、一緒にできるオンライン活動を提案する')

    # --- ルール14: ds急変（+2以上） ---
    ds_spikes = [c for c in rapid_changes if c['metric'] == 'ds' and c['delta'] >= 2]
    if ds_spikes:
        _add('warning', 'important',
             'D/sダイナミクスの急変',
             f"D/sスコアが+{ds_spikes[0]['delta']}急変。支配・服従の力関係が急に強まった。相手の同意と快適さを確認すること。",
             {'metric': 'ds', 'trend': 'spike',
              'value': ds_spikes[0].get('new_value', 0), 'delta': f"+{ds_spikes[0]['delta']}"},
             '力関係について率直に話し合い、境界線を明確にする')

    # --- ルール15: 最も効果的なカテゴリ ---
    if cat_effects:
        best_cat = max(cat_effects.items(), key=lambda x: x[1]['avg_positive'])
        _add('effective', 'info',
             f'最も効果的なアプローチ: {best_cat[0]}',
             f"「{best_cat[0]}」カテゴリが平均+{best_cat[1]['avg_positive']}で最も効果的。このタイプのメッセージを中心にすると良い。",
             {'metric': 'best_category', 'trend': 'positive',
              'value': best_cat[1]['avg_positive'], 'delta': 'N/A'},
             f'「{best_cat[0]}」系のメッセージを意識的に増やす')

    # --- ルール16: 最適な時間帯 ---
    if best_hours:
        hours_str = '、'.join(f'{h}時' for h in best_hours)
        _add('timing', 'info',
             f'レスポンスが良い時間帯: {hours_str}',
             f'応答速度が最も速い時間帯は{hours_str}。この時間にメッセージを送ると反応が良い。',
             {'metric': 'response_time', 'trend': 'optimal',
              'value': best_hours[0], 'delta': 'N/A'},
             f'{hours_str}頃にメッセージを送るようにする')

    # --- ルール17: playfulness低下 ---
    if trends.get('playfulness', {}).get('direction') == 'falling':
        _add('action', 'info',
             '遊び心が減少傾向',
             '会話のplayfulness（遊び心）が下がっている。関係がルーティン化している可能性。',
             {'metric': 'playfulness', 'trend': 'falling',
              'value': trends['playfulness']['current'], 'delta': f"{trends['playfulness']['slope']:+.1f}"},
             'ジョーク、ミーム、サプライズなど遊び心のある要素を取り入れる')

    # --- ルール18: riskがcaution連続 ---
    recent_risks = [e.get('risk') for e in entries[-3:]]
    if recent_risks.count('caution') >= 2:
        _add('warning', 'urgent',
             'リスク警告が頻発',
             '直近でcautionレベルのリスクが複数回検出されている。関係の安定性に注意。',
             {'metric': 'risk', 'trend': 'elevated',
              'value': recent_risks.count('caution'), 'delta': 'N/A'},
             'エスカレーションを避け、安定した基盤を築くことを優先する')

    # --- ルール19: future下降 → 関係の方向性 ---
    if trends.get('future', {}).get('direction') == 'falling':
        _add('warning', 'important',
             '将来展望が下降傾向',
             '将来への見通しスコアが下がっている。関係の方向性に迷いが生じている可能性。',
             {'metric': 'future', 'trend': 'falling',
              'value': trends['future']['current'], 'delta': f"{trends['future']['slope']:+.1f}"},
             '直接的に「これからどうしたい？」と将来について率直に話し合う')

    # --- ルール20: 全体的に安定（全スコアstable） ---
    all_stable = all(trends[k]['direction'] == 'stable' for k in SCORE_KEYS if k in trends)
    if all_stable and len(entries) >= 5:
        _add('status', 'info',
             '関係は安定期',
             '全てのパラメーターが安定している。良い状態だが、マンネリ化しないよう新鮮さも必要。',
             {'metric': 'overall', 'trend': 'stable', 'value': 0, 'delta': 'N/A'},
             '新しい体験（オンラインゲーム、映画同時視聴など）を試してみる')

    # --- ルール21: reassuranceの効果 ---
    if 'reassurance' in cat_effects:
        eff = cat_effects['reassurance']
        if eff['avg_positive'] >= 2:
            _add('effective', 'info',
                 '安心感を与えるメッセージが有効',
                 f"reassuranceカテゴリの効果は+{eff['avg_positive']}。安心感を求めている相手には効果的。",
                 {'metric': 'reassurance_effect', 'trend': 'positive',
                  'value': eff['avg_positive'], 'delta': 'N/A'},
                 '独占性や一途さを伝えるメッセージを適度に送る')

    # --- ルール22: interestカテゴリの効果 ---
    if 'interest' in cat_effects and cat_effects['interest']['avg_positive'] >= 2:
        _add('effective', 'info',
             '興味・関心を示すことが効果的',
             '相手に対する興味や関心を示すメッセージが良い反応を得ている。',
             {'metric': 'interest_effect', 'trend': 'positive',
              'value': cat_effects['interest']['avg_positive'], 'delta': 'N/A'},
             '相手の趣味、仕事、日常について質問する機会を増やす')

    # --- ルール23: 短い連絡ギャップが多い（12-24h） ---
    medium_gaps = [g for g in gaps if 12 <= g['hours'] < 24]
    if len(medium_gaps) >= 3:
        _add('action', 'info',
             '半日以上の空白が頻発',
             f'{len(medium_gaps)}回の12-24時間ギャップを検出。定期的なコミュニケーションリズムを作ると良い。',
             {'metric': 'gap_frequency', 'trend': 'frequent',
              'value': len(medium_gaps), 'delta': 'N/A'},
             '朝と夜の挨拶を習慣化して、コミュニケーションのリズムを作る')

    # --- ルール24: intimacy低い（<=3）---
    if trends.get('intimacy', {}).get('current', 5) <= 3:
        _add('action', 'important',
             '親密度が低い',
             '親密度がまだ低い段階。自己開示や深い会話が必要。',
             {'metric': 'intimacy', 'trend': trends['intimacy']['direction'],
              'value': trends['intimacy']['current'], 'delta': f"{trends['intimacy']['slope']:+.1f}"},
             '自分のプライベートな話や感情を共有し、相手にも開示を促す')

    # --- ルール25: eros高い + intimacy低い → バランス警告 ---
    eros_val = trends.get('eros', {}).get('current', 0)
    intimacy_val = trends.get('intimacy', {}).get('current', 0)
    if eros_val >= 6 and intimacy_val <= 4:
        _add('warning', 'important',
             '性的関心と感情的親密度のアンバランス',
             f'eros({eros_val})がintimacy({intimacy_val})を大幅に上回っている。性的関心だけでなく感情的な絆も育てる必要がある。',
             {'metric': 'balance', 'trend': 'imbalanced',
              'value': eros_val - intimacy_val, 'delta': 'N/A'},
             '性的な話題を控えめにし、感情面の会話を優先する')

    # 優先度順にソート（urgent > important > info）
    priority_order = {'urgent': 0, 'important': 1, 'info': 2}
    advice.sort(key=lambda x: priority_order.get(x['priority'], 3))

    # 最低5件、最大15件に制限
    if len(advice) < 5:
        # 足りない場合は汎用アドバイスで補完
        generic_advice = [
            ('status', 'info', 'データ収集中', 'まだ十分なデータが集まっていません。継続的な記録が必要です。',
             {'metric': 'data', 'trend': 'insufficient', 'value': len(entries), 'delta': 'N/A'},
             'データが蓄積されるまで記録を続ける'),
            ('action', 'info', '多様なコミュニケーション', '様々なタイプのメッセージを試して、何が効果的かを探る段階です。',
             {'metric': 'variety', 'trend': 'exploring', 'value': 0, 'delta': 'N/A'},
             '褒め言葉、質問、愛情表現など様々なアプローチを試す'),
            ('timing', 'info', '応答パターンを観察中', '相手の応答パターンがまだ分析できるほど蓄積されていません。',
             {'metric': 'response_pattern', 'trend': 'collecting', 'value': 0, 'delta': 'N/A'},
             '応答時間を意識して、相手が活発な時間帯を探る'),
        ]
        for cat, pri, title, body, ev, act in generic_advice:
            if len(advice) >= 5:
                break
            adv_counter[0] += 1
            advice.append({
                'id': f'adv_{adv_counter[0]:03d}',
                'category': cat, 'priority': pri, 'title': title,
                'body': body, 'evidence': ev, 'action_suggestion': act,
            })

    return advice[:15]


def generate_advice(days: int) -> Dict:
    """アドバイスAPIのメインロジック"""
    if not EMOTION_DATA_FILE.exists():
        return {'error': 'no data'}

    data = json.loads(EMOTION_DATA_FILE.read_text(encoding='utf-8'))
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    entries = [normalize_entry(e) for e in data.get('entries', []) if e.get('timestamp', '') >= cutoff]

    if not entries:
        return {'error': 'no data in range'}

    # 各種分析
    trends = _score_trends(entries)
    cat_effects = _category_effectiveness(entries)
    attachment = _detect_attachment_issues(entries)
    rapid_changes = _detect_rapid_changes(entries)
    gaps = _compute_communication_gaps(entries)
    best_hours = _best_response_hours(entries)

    # 関係健康度
    health = _compute_relationship_health(trends, attachment, entries)

    # トレンド方向の決定
    rising_count = sum(1 for k in SCORE_KEYS if trends.get(k, {}).get('direction') == 'rising')
    falling_count = sum(1 for k in SCORE_KEYS if trends.get(k, {}).get('direction') == 'falling')
    if rising_count > falling_count + 2:
        trend_dir = 'improving'
    elif falling_count > rising_count + 2:
        trend_dir = 'declining'
    else:
        trend_dir = 'stable'

    # キーインサイト生成
    if health >= 8:
        key_insight = '関係は非常に良好。現在のアプローチを維持しつつ、新鮮さを保つことが大切。'
    elif health >= 6:
        key_insight = '関係は概ね健全。いくつかの改善ポイントに注意を払うとさらに良くなる。'
    elif health >= 4:
        key_insight = '改善が必要な領域がある。特に低いスコアのパラメーターに注目して行動を。'
    else:
        key_insight = '関係に課題が見られる。コミュニケーションの質と量の改善が急務。'

    # アドバイスアイテム生成
    advice_items = _generate_advice_items(entries, trends, cat_effects,
                                           attachment, rapid_changes, gaps, best_hours)

    first_ts = entries[0].get('timestamp', '')
    last_ts = entries[-1].get('timestamp', '')

    return {
        'generated_at': datetime.now(JST).isoformat(),
        'data_range': {
            'from': first_ts,
            'to': last_ts,
            'entry_count': len(entries),
        },
        'advice': advice_items,
        'summary': {
            'relationship_health': health,
            'trend_direction': trend_dir,
            'key_insight': key_insight,
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
