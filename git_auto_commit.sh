#!/bin/bash

# Git自動コミット＆プッシュスクリプト
# ファイル変更を検知して自動的にGitHubに反映

REPO_DIR="/Users/minamitakeshi/discord-mcp-server"
LOG_FILE="$REPO_DIR/git_auto_commit.log"

# ログ関数
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Git自動コミット監視開始"

# fswatch で監視（除外パターン指定）
fswatch -0 \
    --exclude '\.env' \
    --exclude '\.venv/' \
    --exclude '\.log$' \
    --exclude '\.git/' \
    --exclude '__pycache__/' \
    --exclude '\.DS_Store' \
    --exclude '\.last_order_check' \
    --exclude 'git_auto_commit\.log' \
    --exclude '\.tmp$' \
    --exclude '\.temp$' \
    --exclude '\.backup$' \
    --exclude '\.bak$' \
    --exclude 'node_modules/' \
    "$REPO_DIR" | while read -d "" changed_file
do
    # 相対パスに変換
    relative_path="${changed_file#$REPO_DIR/}"

    log_message "変更検知: $relative_path"

    # git操作
    cd "$REPO_DIR" || exit

    # 変更があるか確認
    if ! git diff --quiet || ! git diff --cached --quiet; then
        # 変更されたファイルを追加
        git add "$changed_file" 2>&1 | tee -a "$LOG_FILE"

        # コミットメッセージを生成
        commit_message="Auto-commit: $(basename "$relative_path")

File: $relative_path
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

        # コミット
        if git commit -m "$commit_message" 2>&1 | tee -a "$LOG_FILE"; then
            log_message "コミット成功: $relative_path"

            # プッシュ
            if git push 2>&1 | tee -a "$LOG_FILE"; then
                log_message "プッシュ成功: $relative_path"

                # 通知
                osascript -e "display notification \"$relative_path を GitHubに自動コミットしました\" with title \"Git自動コミット\"" 2>/dev/null
            else
                log_message "プッシュ失敗: $relative_path"
            fi
        else
            log_message "コミット失敗（変更なしの可能性）: $relative_path"
        fi
    else
        log_message "変更なし（スキップ）: $relative_path"
    fi

    # 連続実行を防ぐため少し待機
    sleep 2
done
