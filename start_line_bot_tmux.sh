#!/bin/bash
# LINE Bot テンプレート tmux ランチャー
#
# 使い方:
#   ./start_line_bot_tmux.sh <config.json> [session_name]
#
# 例:
#   ./start_line_bot_tmux.sh alex_config.json alex-bot
#   ./start_line_bot_tmux.sh sarah_config.json
#
# 停止:
#   tmux kill-session -t <session_name>
#
# ログ確認:
#   tmux attach -t <session_name>

set -euo pipefail

CONFIG="${1:?Usage: $0 <config.json> [session_name]}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="${SCRIPT_DIR}/${CONFIG}"

# configファイルの存在確認
if [ ! -f "$CONFIG_PATH" ]; then
    echo "❌ Config file not found: $CONFIG_PATH"
    exit 1
fi

# configからnameを取得してデフォルトセッション名に使用
NAME=$(python3 -c "import json; print(json.load(open('${CONFIG_PATH}'))['name'])" 2>/dev/null || echo "line_bot")
SESSION="${2:-${NAME}-bot}"

# 既存セッション確認
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "⚠️  tmux session '$SESSION' already exists."
    echo "   Attach: tmux attach -t $SESSION"
    echo "   Kill:   tmux kill-session -t $SESSION"
    exit 1
fi

# tmuxセッション起動
tmux new-session -d -s "$SESSION" \
    "cd ${SCRIPT_DIR} && source .venv/bin/activate && python3 line_bot_template.py --config ${CONFIG_PATH} 2>&1 | tee ${NAME}_line_bot.log"

echo "✅ tmux session '$SESSION' started."
echo "   Config:  $CONFIG"
echo "   Attach:  tmux attach -t $SESSION"
echo "   Kill:    tmux kill-session -t $SESSION"
echo "   Log:     tail -f ${SCRIPT_DIR}/${NAME}_line_bot.log"
