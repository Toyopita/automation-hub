#!/usr/bin/env python3
"""
JAXA GSMaP降水量画像をDiscordに投稿するスクリプト
"""
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from jaxa.earth import je
from datetime import datetime, timedelta
import pytz
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_IZUMO')  # IZUMOサーバー用トークン

# IZUMOサーバーのJAXAチャンネル
JAXA_CHANNEL_ID = 1465949147549925396

# 日本時間
JST = pytz.timezone('Asia/Tokyo')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def generate_precipitation_image():
    """JAXA GSMaPから降水量画像を生成"""
    # 日本時間で昨日の日付を取得（最新データは通常1-2日遅れ）
    now = datetime.now(JST)
    target_date = now - timedelta(days=5)  # 5日前のデータを使用（データ遅延を考慮）
    date_str = target_date.strftime("%Y-%m-%dT00:00:00")

    print(f"取得対象日: {target_date.strftime('%Y-%m-%d')}")

    # GSMaP日別降水量データを取得
    collection = "JAXA.EORC_GSMaP_standard.Gauge.00Z-23Z.v6_daily"
    band = "PRECIP"
    bbox = [129, 31, 146, 46]  # 日本列島
    dlim = [date_str, date_str]
    ppu = 10  # pixels per unit (degree)

    print("JAXA Earth APIからデータを取得中...")

    try:
        ic = je.ImageCollection(collection=collection, ssl_verify=True)\
            .filter_date(dlim=dlim)\
            .filter_resolution(ppu=ppu)\
            .filter_bounds(bbox=bbox)\
            .select(band=band)\
            .get_images()

        # Rasterオブジェクトから画像データを取得
        img_data = ic.raster.img
        lonlim = ic.raster.lonlim
        latlim = ic.raster.latlim

        print(f"データ取得完了: shape={img_data.shape}")
        print(f"lonlim: {lonlim}, latlim: {latlim}")

        # 4次元配列から2次元に変換 (1, H, W, 1) -> (H, W)
        img_2d = img_data[0, :, :, 0]

        # 画像を保存
        output_path = "/tmp/jaxa_precipitation.png"

        fig, ax = plt.subplots(figsize=(10, 8))
        extent = [bbox[0], bbox[2], bbox[1], bbox[3]]  # [lon_min, lon_max, lat_min, lat_max]
        im = ax.imshow(img_2d, extent=extent, cmap='jet', vmin=0, vmax=0.5, origin='upper')

        # 日本の都道府県境界を追加
        japan_geojson_path = "/tmp/japan.geojson"
        if os.path.exists(japan_geojson_path):
            with open(japan_geojson_path, 'r') as f:
                japan = json.load(f)
            for feature in japan['features']:
                geom = feature['geometry']
                if geom['type'] == 'MultiPolygon':
                    for polygon in geom['coordinates']:
                        for ring in polygon:
                            coords = list(zip(*ring))
                            ax.plot(coords[0], coords[1], 'k-', linewidth=0.5)
                elif geom['type'] == 'Polygon':
                    for ring in geom['coordinates']:
                        coords = list(zip(*ring))
                        ax.plot(coords[0], coords[1], 'k-', linewidth=0.5)

        ax.set_xlim(bbox[0], bbox[2])
        ax.set_ylim(bbox[1], bbox[3])
        ax.set_xlabel('経度')
        ax.set_ylabel('緯度')
        ax.set_title(f'JAXA GSMaP 日別降水量 - {target_date.strftime("%Y-%m-%d")}')
        plt.colorbar(im, ax=ax, label='降水量 [mm/hr]')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"画像を保存しました: {output_path}")
        return output_path, target_date.strftime("%Y-%m-%d")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    channel = bot.get_channel(JAXA_CHANNEL_ID)
    if channel:
        result = generate_precipitation_image()
        if result:
            image_path, date_str = result

            # 画像をDiscordに投稿
            with open(image_path, 'rb') as f:
                file = discord.File(f, filename='precipitation.png')
                await channel.send(
                    content=f"🛰️ **JAXA GSMaP 日別降水量データ**\n"
                            f"📅 日付: {date_str}\n"
                            f"📍 範囲: 日本列島\n"
                            f"📊 データソース: GSMaP Gauge v6",
                    file=file
                )
            print('画像を投稿しました！')
        else:
            await channel.send("⚠️ JAXA GSMaPデータの取得に失敗しました")
            print('データ取得失敗')
    else:
        print('チャンネルが見つかりません')

    await bot.close()

if __name__ == "__main__":
    if not TOKEN:
        # IZUMOトークンがない場合は通常のトークンを使用
        TOKEN = os.getenv('DISCORD_TOKEN')

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("DISCORD_TOKENが設定されていません")
