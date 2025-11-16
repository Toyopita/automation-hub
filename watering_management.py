#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桜の水やり管理システム (GASからの移行版)
- Notion桜の木管理DBから前回水やり日時を取得
- OpenWeather APIで降雨量・最高気温を取得
- 水やり必要判定
- LINE通知送信
- Notion水やり記録DBへの記録
"""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()


class Config:
    """設定クラス"""
    # Notion
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN_WATERING')
    WATERING_MASTER_DB_ID = os.environ.get('WATERING_MASTER_DB_ID')
    WATERING_LOG_DB_ID = os.environ.get('WATERING_LOG_DB_ID')

    # OpenWeather API
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
    LATITUDE = float(os.environ.get('WATERING_LATITUDE', '34.5544'))
    LONGITUDE = float(os.environ.get('WATERING_LONGITUDE', '135.5284'))

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_USER_ID = os.environ.get('LINE_USER_ID')

    # その他
    WATER_MANUAL_URL = os.environ.get('WATER_MANUAL_URL')

    # 判定閾値
    HIGH_TEMP_THRESHOLD = 30  # 高温判定（℃）
    RAIN_THRESHOLD = 5  # 雨判定（mm）
    INTERVAL_WITH_LEAF = 2  # 葉ありの水やり間隔（日）
    INTERVAL_WITHOUT_LEAF = 7  # 葉なしの水やり間隔（日）
    RAIN_FORECAST_THRESHOLD = 5  # 雨予報判定（mm）
    RAIN_FORECAST_DAYS = 5  # 雨予報確認日数


class NotionAPI:
    """Notion API操作クラス"""

    BASE_URL = "https://api.notion.com/v1"
    HEADERS = {
        "Authorization": f"Bearer {Config.NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    @classmethod
    def query_database(cls, database_id: str, filter_params: Dict = None) -> List[Dict]:
        """データベースクエリ"""
        url = f"{cls.BASE_URL}/databases/{database_id}/query"
        payload = {}
        if filter_params:
            payload['filter'] = filter_params

        response = requests.post(url, headers=cls.HEADERS, json=payload)
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            print(f"[ERROR] Notion query failed: {response.status_code} - {response.text}")
            return []

    @classmethod
    def create_page(cls, database_id: str, properties: Dict) -> bool:
        """ページ作成（記録）"""
        url = f"{cls.BASE_URL}/pages"
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }

        response = requests.post(url, headers=cls.HEADERS, json=payload)
        if response.status_code == 200:
            return True
        else:
            print(f"[ERROR] Notion create page failed: {response.status_code} - {response.text}")
            return False

    @classmethod
    def update_page(cls, page_id: str, properties: Dict) -> bool:
        """ページ更新（最終水やり日更新）"""
        url = f"{cls.BASE_URL}/pages/{page_id}"
        payload = {"properties": properties}

        response = requests.patch(url, headers=cls.HEADERS, json=payload)
        if response.status_code == 200:
            return True
        else:
            print(f"[ERROR] Notion update page failed: {response.status_code} - {response.text}")
            return False


class WeatherAPI:
    """OpenWeather API操作クラス"""

    @staticmethod
    def get_daily_rain(date: datetime, lat: float, lon: float, api_key: str) -> float:
        """指定日の降雨量取得（mm）"""
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"[ERROR] Weather API failed: {response.status_code}")
            return 0.0

        data = response.json()
        target_date_str = date.strftime('%Y-%m-%d')
        total_rain = 0.0

        for entry in data.get('list', []):
            forecast_dt = datetime.fromtimestamp(entry['dt'])
            forecast_date_str = forecast_dt.strftime('%Y-%m-%d')

            if forecast_date_str == target_date_str:
                rain_3h = entry.get('rain', {}).get('3h', 0)
                total_rain += rain_3h

        return round(total_rain, 1)

    @staticmethod
    def get_daily_max_temperature(date: datetime, lat: float, lon: float, api_key: str) -> Optional[float]:
        """指定日の最高気温取得（℃）"""
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"[ERROR] Weather API failed: {response.status_code}")
            return None

        data = response.json()
        target_date_str = date.strftime('%Y-%m-%d')
        max_temp = -float('inf')

        for entry in data.get('list', []):
            forecast_dt = datetime.fromtimestamp(entry['dt'])
            forecast_date_str = forecast_dt.strftime('%Y-%m-%d')

            if forecast_date_str == target_date_str:
                temp_max = entry.get('main', {}).get('temp_max')
                if temp_max is not None:
                    max_temp = max(max_temp, temp_max)

        return round(max_temp, 1) if max_temp != -float('inf') else None

    @staticmethod
    def get_rain_forecast_details(lat: float, lon: float, api_key: str, days: int, threshold: float) -> Dict[str, float]:
        """今後N日間の雨予報取得（閾値以上の日のみ）"""
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"[ERROR] Weather API failed: {response.status_code}")
            return {}

        data = response.json()
        today = datetime.now().date()

        # 日別雨量データ（合計と回数）
        rain_data_by_day = {}

        for entry in data.get('list', []):
            forecast_dt = datetime.fromtimestamp(entry['dt'])
            forecast_date = forecast_dt.date()
            forecast_date_str = forecast_date.strftime('%Y-%m-%d')

            days_diff = (forecast_date - today).days

            # 明日から指定日数以内のデータのみ
            if 1 <= days_diff <= days:
                if forecast_date_str not in rain_data_by_day:
                    rain_data_by_day[forecast_date_str] = {'total': 0.0, 'count': 0}

                rain_3h = entry.get('rain', {}).get('3h', 0)
                rain_data_by_day[forecast_date_str]['total'] += rain_3h
                rain_data_by_day[forecast_date_str]['count'] += 1

        # 平均雨量計算と閾値フィルタリング
        filtered = {}
        for date_str, data in rain_data_by_day.items():
            avg_rain = data['total'] / data['count'] if data['count'] > 0 else 0
            avg_rain = round(avg_rain, 1)

            if avg_rain >= threshold:
                filtered[date_str] = avg_rain

        return filtered


class LINEAPI:
    """LINE Messaging API操作クラス"""

    @staticmethod
    def send_message(message: str) -> bool:
        """LINEメッセージ送信"""
        if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_USER_ID:
            print("[WARN] LINE設定が不完全なため、通知をスキップします")
            return False

        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}"
        }

        # 複数ユーザーID対応
        user_ids = [uid.strip() for uid in Config.LINE_USER_ID.split(',')]

        success = True
        for user_id in user_ids:
            payload = {
                "to": user_id,
                "messages": [{"type": "text", "text": message}]
            }

            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"[ERROR] LINE送信失敗: {response.status_code} - {response.text}")
                success = False
            else:
                print(f"[INFO] LINE送信成功: {user_id}")

        return success


class WateringManager:
    """水やり管理クラス"""

    def __init__(self):
        self.today = datetime.now()
        self.today_str = self.today.strftime('%Y-%m-%d')
        self.jst = timezone(timedelta(hours=9))

    def get_tree_data_from_notion(self) -> List[Dict]:
        """Notionマスタ DBから桜の木データ取得"""
        print("[INFO] Notionマスタ DBから桜の木データ取得中...")

        pages = NotionAPI.query_database(Config.WATERING_MASTER_DB_ID)

        trees = []
        for page in pages:
            props = page['properties']

            # ID（selectプロパティ）
            tree_id = props.get('ID', {}).get('select', {}).get('name', '')

            # 名前（titleプロパティ）
            name_prop = props.get('名前', {}).get('title', [])
            name = name_prop[0]['text']['content'] if name_prop else ''

            # 最終水やり日（dateプロパティ）
            last_watering_prop = props.get('最後に水やりをした日付', {}).get('date', {})
            last_watering_str = last_watering_prop.get('start', '') if last_watering_prop else ''

            # 花や葉の状態（selectプロパティ）
            leaf_state = props.get('花や葉の状態', {}).get('select', {}).get('name', '')

            if not tree_id or not name:
                continue

            trees.append({
                'page_id': page['id'],
                'id': tree_id,
                'name': name,
                'last_watering': last_watering_str,
                'leaf_state': leaf_state
            })

        print(f"[INFO] {len(trees)}件の桜データ取得完了")
        return trees

    def check_watering_needed(self, tree: Dict, today_rain: float, today_max_temp: Optional[float]) -> Tuple[str, bool]:
        """水やり必要判定

        Returns:
            (判定結果メッセージ, 自動更新フラグ)
        """
        # 最終水やり日解析
        if tree['last_watering']:
            last_watering_date = datetime.strptime(tree['last_watering'], '%Y-%m-%d')
        else:
            last_watering_date = self.today

        days_elapsed = (self.today - last_watering_date).days

        # 水やり間隔（葉の状態による）
        interval = Config.INTERVAL_WITH_LEAF if tree['leaf_state'] == 'あり' else Config.INTERVAL_WITHOUT_LEAF

        # 判定ロジック
        verdict = "水やりは不要です"
        should_auto_update = False

        # 1. 高温判定
        if today_max_temp and today_max_temp >= Config.HIGH_TEMP_THRESHOLD and today_rain < Config.RAIN_THRESHOLD:
            verdict = "高温のため水やりしてください（自動更新）"
            should_auto_update = True

        # 2. 雨判定（みなし水やり）
        elif today_rain >= Config.RAIN_THRESHOLD:
            verdict = "雨のため水やり不要（みなし）"
            should_auto_update = True  # 雨の場合も自動更新

        # 3. 間隔到達判定
        elif days_elapsed >= interval:
            verdict = "今日水やりしてください（自動更新）"
            should_auto_update = True

        return verdict, should_auto_update

    def update_last_watering_date(self, page_id: str, date_str: str) -> bool:
        """Notionの最終水やり日を更新"""
        properties = {
            "最後に水やりをした日付": {
                "date": {"start": date_str}
            }
        }
        return NotionAPI.update_page(page_id, properties)

    def record_to_notion(self, tree: Dict, today_rain: float, today_max_temp: Optional[float],
                         verdict: str, days_elapsed: int, next_watering: str,
                         rain_forecast_date: Optional[str], rain_forecast_value: Optional[float]) -> bool:
        """Notion記録DBに記録"""
        properties = {
            "日付": {"date": {"start": self.today_str}},
            "ID": {"select": {"name": str(tree['id'])}},
            "名前": {"title": [{"text": {"content": tree['name']}}]},
            "降水量（mm）": {"number": today_rain},
            "花や葉の状態": {"select": {"name": tree['leaf_state']}},
            "最後に水やりをした日付": {"date": {"start": tree['last_watering'] or self.today_str}},
            "経過日数": {"number": days_elapsed},
            "判定結果": {"select": {"name": verdict}},
            "次回水やり予定日": {"date": {"start": next_watering}}
        }

        # 最高気温
        if today_max_temp is not None:
            properties["最高気温（℃）"] = {"number": today_max_temp}

        # 雨予報
        if rain_forecast_date:
            properties["今後の雨予報"] = {"select": {"name": "あり"}}
            properties["今後5日間で雨予報の日"] = {"date": {"start": rain_forecast_date}}
            properties["その日の予報雨量"] = {"number": rain_forecast_value}
        else:
            properties["今後の雨予報"] = {"select": {"name": "なし"}}

        return NotionAPI.create_page(Config.WATERING_LOG_DB_ID, properties)

    def run(self):
        """メイン処理"""
        print(f"=== 水やりチェック開始: {self.today_str} ===")

        try:
            # 季節判定（10月〜3月は水やりシーズンオフ）
            current_month = self.today.month
            is_watering_season = current_month >= 4 and current_month <= 9

            # 1. 天気情報取得
            today_rain = WeatherAPI.get_daily_rain(
                self.today, Config.LATITUDE, Config.LONGITUDE, Config.OPENWEATHER_API_KEY
            )
            today_max_temp = WeatherAPI.get_daily_max_temperature(
                self.today, Config.LATITUDE, Config.LONGITUDE, Config.OPENWEATHER_API_KEY
            )
            rain_forecast = WeatherAPI.get_rain_forecast_details(
                Config.LATITUDE, Config.LONGITUDE, Config.OPENWEATHER_API_KEY,
                Config.RAIN_FORECAST_DAYS, Config.RAIN_FORECAST_THRESHOLD
            )

            print(f"[INFO] 天気情報: 雨量={today_rain}mm, 最高気温={today_max_temp}℃")
            print(f"[INFO] 雨予報: {rain_forecast}")

            # 最も近い雨予報
            nearest_rain_date = None
            nearest_rain_value = None
            if rain_forecast:
                sorted_dates = sorted(rain_forecast.keys())
                nearest_rain_date = sorted_dates[0]
                nearest_rain_value = rain_forecast[nearest_rain_date]
                print(f"[INFO] 最も近い雨予報: {nearest_rain_date} - {nearest_rain_value}mm")

            # 2. 桜の木データ取得
            trees = self.get_tree_data_from_notion()

            if not trees:
                print("[WARN] 桜データが取得できませんでした")
                return

            # シーズンオフの場合は記録のみ行う
            if not is_watering_season:
                print(f"[INFO] 水やりシーズンオフ（10月〜3月）: 記録のみ実行")
                print(f"[INFO] 現在の月: {current_month}月")

                for tree in trees:
                    print(f"\n[INFO] 処理中: {tree['name']} (ID: {tree['id']})")

                    # 経過日数
                    if tree['last_watering']:
                        last_watering_date = datetime.strptime(tree['last_watering'], '%Y-%m-%d')
                        days_elapsed = (self.today - last_watering_date).days
                    else:
                        days_elapsed = 0

                    # 次回水やり予定日（参考値）
                    interval = Config.INTERVAL_WITH_LEAF if tree['leaf_state'] == 'あり' else Config.INTERVAL_WITHOUT_LEAF
                    next_watering_date = self.today + timedelta(days=interval)
                    next_watering_str = next_watering_date.strftime('%Y-%m-%d')

                    # Notion記録（判定結果は「水やりは不要です（シーズンオフ）」）
                    self.record_to_notion(
                        tree, today_rain, today_max_temp,
                        "水やりは不要です（シーズンオフ）",
                        days_elapsed, next_watering_str,
                        nearest_rain_date, nearest_rain_value
                    )

                print("\n[INFO] シーズンオフ記録完了")
                print("=== 水やりチェック完了（シーズンオフ） ===")
                return

            # 3. 各木について判定（シーズン中のみ）
            need_watering_trees = []
            auto_updated_trees = []

            for tree in trees:
                print(f"\n[INFO] 処理中: {tree['name']} (ID: {tree['id']})")

                # 判定
                verdict, should_auto_update = self.check_watering_needed(tree, today_rain, today_max_temp)

                # 最終水やり日からの経過日数
                if tree['last_watering']:
                    last_watering_date = datetime.strptime(tree['last_watering'], '%Y-%m-%d')
                    days_elapsed = (self.today - last_watering_date).days
                else:
                    days_elapsed = 0

                # 次回水やり予定日
                interval = Config.INTERVAL_WITH_LEAF if tree['leaf_state'] == 'あり' else Config.INTERVAL_WITHOUT_LEAF
                next_watering_date = self.today + timedelta(days=interval)
                next_watering_str = next_watering_date.strftime('%Y-%m-%d')

                # 自動更新処理
                if should_auto_update:
                    success = self.update_last_watering_date(tree['page_id'], self.today_str)
                    if success:
                        print(f"[INFO] 最終水やり日を自動更新: {tree['name']} → {self.today_str}")

                        if "雨のため" in verdict:
                            auto_updated_trees.append(f"{tree['name']}（雨による自動更新）")
                        else:
                            auto_updated_trees.append(f"{tree['name']}（水やり実施による自動更新）")
                            need_watering_trees.append(
                                f"・{tree['name']}（ID: {tree['id']}）最終水やり: {tree['last_watering']}（{days_elapsed}日経過） ✅自動更新済み"
                            )

                        # 更新後の値でNotion記録
                        tree['last_watering'] = self.today_str
                        days_elapsed = 0
                        next_watering_date = self.today + timedelta(days=interval)
                        next_watering_str = next_watering_date.strftime('%Y-%m-%d')

                # Notion記録DB登録
                self.record_to_notion(
                    tree, today_rain, today_max_temp, verdict, days_elapsed, next_watering_str,
                    nearest_rain_date, nearest_rain_value
                )

            # 4. LINE通知送信
            if need_watering_trees:
                print(f"\n[INFO] 水やりが必要な木: {len(need_watering_trees)}件")

                auto_update_info = ""
                if auto_updated_trees:
                    auto_update_info = "\n\n【自動更新情報】\n以下の木の最終水やり日が自動更新されました：\n" + "\n".join([f"・{t}" for t in auto_updated_trees])

                message = (
                    "🌸【水やり通知】🌸\n\n"
                    "いつも管理ありがとうございます。\n\n"
                    "今日は桜の水やり日です。\n\n"
                    "現在は水やり自動システム化により早朝4時から5時30分の90分間、自動的に水やりが行われます。\n"
                    "出勤時は水鉢が湿っているか確認いただきますようお願いいたします。\n\n"
                    "※システムにより最終水やり日は自動で本日に更新されます。"
                )
                message += auto_update_info

                LINEAPI.send_message(message)
                print("[INFO] LINE通知送信完了")
            else:
                print("[INFO] 水やりが必要な木はありませんでした")

                if auto_updated_trees:
                    print(f"[INFO] 雨による自動更新のみ: {len(auto_updated_trees)}件")

            print("\n=== 水やりチェック完了 ===")

        except Exception as e:
            print(f"[ERROR] 処理中にエラーが発生: {e}")
            import traceback
            traceback.print_exc()

            # エラー通知
            try:
                error_message = (
                    "🚨【エラー通知】水やり管理システムでエラーが発生しました\n\n"
                    f"エラー内容: {str(e)}\n"
                    f"発生日時: {datetime.now(self.jst).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    "ログを確認し、必要に応じて対応してください。"
                )
                LINEAPI.send_message(error_message)
            except:
                pass


def main():
    """エントリーポイント"""
    manager = WateringManager()
    manager.run()


if __name__ == "__main__":
    main()
