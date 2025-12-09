#!/usr/bin/env node
/**
 * プライベートカレンダーをチェックして休日かを判定
 * 今日の0:00〜23:59の範囲に「休み」イベントがあればexit code 1（休日）
 * 予定がなければexit code 0（通常日）
 */

const { google } = require('googleapis');
const path = require('path');
const fs = require('fs');

const CALENDAR_ID = 'primary';  // プライベートカレンダー
const CREDENTIALS_PATH = path.join(process.env.HOME, 'shared-google-calendar', 'credentials.json');
const TOKEN_PATH = path.join(process.env.HOME, 'discord-mcp-server', 'google_calendar_token.json');

async function checkHoliday() {
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

        // 今日の日付（YYYY-MM-DD形式、日本時間）
        const now = new Date();
        const jstDate = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
        const year = jstDate.getFullYear();
        const month = String(jstDate.getMonth() + 1).padStart(2, '0');
        const day = String(jstDate.getDate()).padStart(2, '0');
        const todayStr = `${year}-${month}-${day}`;

        // 過去1週間から未来1週間の範囲で検索（終日イベントを確実に拾うため）
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        const timeMin = weekAgo.toISOString();

        const weekLater = new Date(now);
        weekLater.setDate(weekLater.getDate() + 7);
        const timeMax = weekLater.toISOString();

        console.log(`[INFO] 検索範囲: ${timeMin} - ${timeMax}`);
        console.log(`[INFO] 今日の日付: ${todayStr}`);

        // カレンダーから予定を取得
        const res = await calendar.events.list({
            calendarId: CALENDAR_ID,
            timeMin: timeMin,
            timeMax: timeMax,
            singleEvents: true,
            orderBy: 'startTime',
        });

        const events = res.data.items;

        // 「休み」イベントを探す
        const holidayEvents = events.filter(event =>
            event.summary && event.summary.includes('休み')
        );

        // 今日が休日に該当するかチェック（終日イベント＋時間指定イベント両対応）
        const todaysHolidays = holidayEvents.filter(event => {
            // 1. 終日イベント（event.start.date が存在）
            if (event.start.date) {
                const startDate = event.start.date;
                const endDate = event.end.date;
                // start.date <= today < end.date（end.dateは排他的）
                return startDate <= todayStr && todayStr < endDate;
            }

            // 2. 時間指定イベント（event.start.dateTime が存在）
            if (event.start.dateTime) {
                // dateTimeから日付部分を抽出（例: 2025-12-09T00:00:00+09:00 → 2025-12-09）
                const eventDate = event.start.dateTime.split('T')[0];
                return eventDate === todayStr;
            }

            return false;
        });

        if (todaysHolidays && todaysHolidays.length > 0) {
            console.log(`[INFO] 今日は休日（${todaysHolidays.length}件）:`);
            todaysHolidays.forEach(event => {
                const start = event.start.date;
                const end = event.end.date;
                console.log(`  - ${event.summary} (${start} - ${end})`);
            });
            process.exit(1); // 休日
        } else {
            console.log('[INFO] 今日は休日ではありません');
            process.exit(0); // 通常日
        }

    } catch (error) {
        console.error(`[ERROR] カレンダーチェックエラー: ${error.message}`);
        process.exit(2); // エラー
    }
}

checkHoliday();
