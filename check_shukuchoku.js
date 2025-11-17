#!/usr/bin/env node
/**
 * 宿直カレンダーをチェックして宿直中かを判定
 * 前日18:00〜当日9:00の範囲に予定があればexit code 1（宿直中）
 * 予定がなければexit code 0（宿直なし）
 */

const { google } = require('googleapis');
const path = require('path');
const fs = require('fs');

const CALENDAR_ID = '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com';
const CREDENTIALS_PATH = path.join(process.env.HOME, 'shared-google-calendar', 'credentials.json');
const TOKEN_PATH = path.join(process.env.HOME, 'discord-mcp-server', 'google_calendar_token.json');

async function checkShukuchoku() {
    try {
        // 認証情報の読み込み
        const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
        const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));

        const { client_secret, client_id, redirect_uris } = credentials.installed;
        const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
        oAuth2Client.setCredentials(token);

        // トークンの自動更新を設定
        oAuth2Client.on('tokens', (tokens) => {
            if (tokens.refresh_token) {
                token.refresh_token = tokens.refresh_token;
            }
            token.access_token = tokens.access_token;
            token.expiry_date = tokens.expiry_date;

            // 更新されたトークンを保存
            fs.writeFileSync(TOKEN_PATH, JSON.stringify(token, null, 2));
            console.log('[INFO] トークンを更新しました');
        });

        const calendar = google.calendar({ version: 'v3', auth: oAuth2Client });

        // 前日18:00から当日9:00までの範囲（日本時間）
        const now = new Date();
        const jstNow = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));

        const yesterday = new Date(jstNow);
        yesterday.setDate(yesterday.getDate() - 1);
        yesterday.setHours(18, 0, 0, 0);

        const today = new Date(jstNow);
        today.setHours(9, 0, 0, 0);

        // 日本時間をUTCに変換
        const timeMin = new Date(yesterday.getTime() - (9 * 60 * 60 * 1000)).toISOString();
        const timeMax = new Date(today.getTime() - (9 * 60 * 60 * 1000)).toISOString();

        console.log(`[INFO] 宿直チェック範囲: ${timeMin} - ${timeMax}`);

        // カレンダーから予定を取得
        const res = await calendar.events.list({
            calendarId: CALENDAR_ID,
            timeMin: timeMin,
            timeMax: timeMax,
            singleEvents: true,
            orderBy: 'startTime',
        });

        const events = res.data.items;

        if (events && events.length > 0) {
            console.log(`[INFO] 宿直予定あり（${events.length}件）:`);
            events.forEach(event => {
                const start = event.start.dateTime || event.start.date;
                const end = event.end.dateTime || event.end.date;
                console.log(`  - ${event.summary} (${start} - ${end})`);
            });
            process.exit(1); // 宿直中
        } else {
            console.log('[INFO] 宿直予定なし');
            process.exit(0); // 宿直なし
        }

    } catch (error) {
        console.error(`[ERROR] カレンダーチェックエラー: ${error.message}`);
        process.exit(2); // エラー
    }
}

checkShukuchoku();
