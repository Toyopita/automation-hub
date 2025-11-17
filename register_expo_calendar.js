#!/usr/bin/env node
/**
 * 大阪関西万博カレンダー登録スクリプト
 *
 * expo_calendar_pending.json から待機中のイベントを読み込み、
 * MCPでGoogleカレンダー（関西イベント情報）に登録する
 *
 * 5分ごとにlaunchdで実行
 */

const fs = require('fs');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

const PENDING_FILE = '/Users/minamitakeshi/discord-mcp-server/expo_calendar_pending.json';
const LOG_FILE = '/Users/minamitakeshi/discord-mcp-server/expo_calendar_register.log';

// ログ出力関数
function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    console.log(logMessage.trim());
    fs.appendFileSync(LOG_FILE, logMessage);
}

// MCPでGoogleカレンダーにイベント登録（Claude Code経由）
async function registerEventToCalendar(eventData) {
    log(`イベント登録開始: ${eventData.summary}`);

    // Claude Code MCP の mcp__google-calendar__create-event を使用
    // しかし、Node.jsから直接MCPを呼び出すことはできないため、
    // claude cliを使用するか、REST APIを使う必要がある

    // 代わりに、Google Calendar APIを直接使用する方法に変更
    // または、MCPサーバーを経由する方法を検討

    // 一旦、Node.jsのGoogle Calendar APIクライアントを使用
    const { google } = require('googleapis');
    const path = require('path');

    // OAuth2クライアント設定
    // ※ 認証情報が必要ですが、MCPが既に認証済みなので、
    // MCPのトークンを再利用する方法を探す必要があります

    // 問題: Node.jsから直接MCPを呼び出す標準的な方法がない
    // 解決策: Google Calendar APIを直接使用するため、認証情報をセットアップ

    log('⚠️  MCP経由のカレンダー登録は未実装');
    log('Google Calendar API直接使用への移行が必要です');

    return false;
}

// 待機中のイベントを処理
async function processPendingEvents() {
    log('=== カレンダー登録処理開始 ===');

    // pending_fileの存在確認
    if (!fs.existsSync(PENDING_FILE)) {
        log('待機中のイベントはありません');
        return;
    }

    let pendingEvents;
    try {
        const data = fs.readFileSync(PENDING_FILE, 'utf-8');
        pendingEvents = JSON.parse(data);
    } catch (error) {
        log(`エラー: pending_file読み込み失敗 - ${error.message}`);
        return;
    }

    if (!Array.isArray(pendingEvents) || pendingEvents.length === 0) {
        log('待機中のイベントはありません');
        return;
    }

    log(`待機中のイベント数: ${pendingEvents.length}`);

    // 登録成功したイベントのインデックス
    const successIndexes = [];

    for (let i = 0; i < pendingEvents.length; i++) {
        const event = pendingEvents[i];

        try {
            // Google Calendar APIで直接登録
            const success = await registerEventDirectly(event);

            if (success) {
                log(`✅ 登録成功: ${event.summary}`);
                successIndexes.push(i);

                // macOS通知
                const notifyCmd = `osascript -e 'display notification "${event.summary} をカレンダーに登録しました" with title "万博カレンダー"'`;
                await execPromise(notifyCmd);
            } else {
                log(`❌ 登録失敗: ${event.summary}`);
            }
        } catch (error) {
            log(`エラー: ${event.summary} - ${error.message}`);
        }

        // API制限対策で1秒待機
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // 登録成功したイベントをpending_fileから削除
    if (successIndexes.length > 0) {
        const remainingEvents = pendingEvents.filter((_, index) => !successIndexes.includes(index));

        if (remainingEvents.length === 0) {
            // すべて登録完了したらファイル削除
            fs.unlinkSync(PENDING_FILE);
            log('すべてのイベントを登録しました（pending_file削除）');
        } else {
            // 残りのイベントを保存
            fs.writeFileSync(PENDING_FILE, JSON.stringify(remainingEvents, null, 2));
            log(`残り ${remainingEvents.length} 件のイベントが待機中`);
        }
    }

    log('=== カレンダー登録処理完了 ===');
}

// Google Calendar APIで直接登録（要認証設定）
async function registerEventDirectly(eventData) {
    // Google Calendar API v3を使用
    // 認証にはサービスアカウントまたはOAuth2が必要

    // まず、googleapis パッケージが必要
    try {
        const { google } = require('googleapis');

        // OAuth2認証（トークンが必要）
        // または、サービスアカウント認証

        // ここでは一旦、実装をスキップして手動対応
        log('Google Calendar API認証未設定');
        return false;

    } catch (error) {
        log(`Google Calendar API使用不可: ${error.message}`);
        return false;
    }
}

// メイン処理
async function main() {
    try {
        await processPendingEvents();
    } catch (error) {
        log(`致命的エラー: ${error.message}`);
        console.error(error);
        process.exit(1);
    }
}

// 実行
main();
