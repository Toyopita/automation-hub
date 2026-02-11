#!/bin/bash
# LINE Bot テンプレート用 Cloudflare Tunnel 起動スクリプト
# Laura用 (start_laura_tunnel.sh / port 8787) とは独立で動作
#
# 使い方:
#   ./start_template_tunnel.sh <config.json>
#
# 例:
#   ./start_template_tunnel.sh alex_config.json

set -euo pipefail

CONFIG="${1:?Usage: $0 <config.json>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="${SCRIPT_DIR}/${CONFIG}"

if [ ! -f "$CONFIG_PATH" ]; then
    echo "❌ Config file not found: $CONFIG_PATH"
    exit 1
fi

ENV_FILE="${SCRIPT_DIR}/.env"

# configからポートとLINE token env名を取得
PORT=$(python3 -c "import json; print(json.load(open('${CONFIG_PATH}')).get('port', 8788))")
LINE_TOKEN_ENV=$(python3 -c "import json; print(json.load(open('${CONFIG_PATH}'))['env']['line_access_token'])")
NAME=$(python3 -c "import json; print(json.load(open('${CONFIG_PATH}'))['name'])")

# .envからLINE Access Tokenを取得
LINE_TOKEN=$(grep "^${LINE_TOKEN_ENV}=" "$ENV_FILE" | cut -d'=' -f2)

if [ -z "$LINE_TOKEN" ]; then
    echo "❌ ${LINE_TOKEN_ENV} not found in .env"
    exit 1
fi

TUNNEL_LOG="${SCRIPT_DIR}/${NAME}_cloudflare_tunnel.log"

echo "Starting tunnel for: ${NAME} (port ${PORT})"

# 既存の同ポートcloudflaredを停止
pkill -f "cloudflared tunnel --url http://localhost:${PORT}" 2>/dev/null || true
sleep 2

# Tunnel起動（バックグラウンド）
/usr/local/bin/cloudflared tunnel --url "http://localhost:${PORT}" > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

# URL取得を待つ（最大30秒）
TUNNEL_URL=""
for i in $(seq 1 30); do
    sleep 1
    TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "Tunnel URL: $TUNNEL_URL"
        break
    fi
done

if [ -z "$TUNNEL_URL" ]; then
    echo "ERROR: Tunnel URL not found after 30s"
    exit 1
fi

# LINE Webhook URLを自動更新
WEBHOOK_URL="${TUNNEL_URL}/callback"
echo "Setting LINE Webhook: $WEBHOOK_URL"

curl -s -X PUT \
    -H "Authorization: Bearer $LINE_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"endpoint\":\"$WEBHOOK_URL\"}" \
    https://api.line.me/v2/bot/channel/webhook/endpoint

echo ""
echo "✅ Tunnel started and LINE Webhook updated"
echo "   Name:    ${NAME}"
echo "   Port:    ${PORT}"
echo "   URL:     ${TUNNEL_URL}"
echo "   Webhook: ${WEBHOOK_URL}"
echo "   Log:     ${TUNNEL_LOG}"

# Tunnelプロセスをフォアグラウンドで維持
wait $TUNNEL_PID
