#!/bin/bash

# Git定期バックアップスクリプト
# 1時間ごとに実行され、全ての変更をGitHubに反映

export PATH="$HOME/bin:/usr/local/bin:$PATH"

REPO_DIR="/Users/minamitakeshi/discord-mcp-server"
LOG_FILE="$REPO_DIR/git_periodic_backup.log"

# ログ関数
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "=== 定期バックアップ開始 ==="

cd "$REPO_DIR" || exit 1

# リモートから最新を取得（衝突を避けるため）
log_message "リモートから最新情報を取得..."
if ! git fetch origin 2>&1 | tee -a "$LOG_FILE"; then
    log_message "⚠️  fetch失敗（継続）"
fi

# リモートとローカルの差分確認
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null)
BASE=$(git merge-base @ @{u} 2>/dev/null)

if [ "$LOCAL" != "$REMOTE" ] && [ "$LOCAL" = "$BASE" ]; then
    log_message "リモートに新しい変更あり - pull実行"
    git pull origin master 2>&1 | tee -a "$LOG_FILE"
fi

# ステータス確認
if git diff --quiet && git diff --cached --quiet; then
    log_message "✅ 変更なし - バックアップ不要"
    log_message "=== 定期バックアップ終了 ===\n"
    exit 0
fi

# 変更されたファイル一覧
changed_files=$(git status --short | head -10)
file_count=$(git status --short | wc -l | tr -d ' ')

log_message "変更ファイル数: $file_count"
log_message "$changed_files"

# 全ての変更をステージング（除外対象は.gitignoreで管理）
git add -A 2>&1 | tee -a "$LOG_FILE"

# コミットメッセージ生成
commit_message="Periodic backup: $file_count files changed

Auto-backup at $(date '+%Y-%m-%d %H:%M:%S')

Changes:
$(git status --short | head -20)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# コミット
if git commit -m "$commit_message" 2>&1 | tee -a "$LOG_FILE"; then
    log_message "✅ コミット成功"

    # プッシュ（最大3回リトライ）
    retry_count=0
    max_retries=3

    while [ $retry_count -lt $max_retries ]; do
        if git push origin master 2>&1 | tee -a "$LOG_FILE"; then
            log_message "✅ プッシュ成功"

            # 成功通知
            osascript -e "display notification \"$file_count 個のファイルをGitHubにバックアップしました\" with title \"定期バックアップ完了\"" 2>/dev/null

            log_message "=== 定期バックアップ終了（成功） ===\n"
            exit 0
        else
            retry_count=$((retry_count + 1))
            log_message "⚠️  プッシュ失敗（リトライ $retry_count/$max_retries）"

            if [ $retry_count -lt $max_retries ]; then
                sleep 5
                # リトライ前にpull
                git pull --rebase origin master 2>&1 | tee -a "$LOG_FILE"
            fi
        fi
    done

    log_message "❌ プッシュ失敗（最大リトライ回数超過）"
    osascript -e 'display notification "GitHubへのプッシュが失敗しました" with title "バックアップエラー"' 2>/dev/null
else
    log_message "変更なし or コミット失敗"
fi

log_message "=== 定期バックアップ終了 ===\n"
