#!/bin/bash
# Laura LINE Bot用 Cloudflare Tunnel 起動スクリプト
# Tunnel起動 → URL取得 → LINE Webhook URL自動更新

LOG_DIR="/Users/minamitakeshi/discord-mcp-server"
TUNNEL_LOG="$LOG_DIR/cloudflare_tunnel.log"
ENV_FILE="$LOG_DIR/.env"

# .envからLINE Access Tokenを取得
LINE_TOKEN=$(grep '^LINE_LAURA_ACCESS_TOKEN=' "$ENV_FILE" | cut -d'=' -f2)

# 既存のcloudflaredを停止
pkill -f "cloudflared tunnel --url http://localhost:8787" 2>/dev/null
sleep 2

# Tunnel起動（バックグラウンド）
/usr/local/bin/cloudflared tunnel --url http://localhost:8787 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"

# URL取得を待つ（最大30秒）
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
echo "LINE Webhook updated successfully"

# Tunnelプロセスをフォアグラウンドで維持
wait $TUNNEL_PID
