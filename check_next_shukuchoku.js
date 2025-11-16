#!/usr/bin/env node
/**
 * 次の宿直予定を確認
 */

const { google } = require('googleapis');
const path = require('path');
const fs = require('fs');

const CALENDAR_ID = '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com';
const CREDENTIALS_PATH = path.join(process.env.HOME, 'shared-google-calendar', 'credentials.json');
const TOKEN_PATH = path.join(process.env.HOME, 'discord-mcp-server', 'google_calendar_token.json');

async function checkNextShukuchoku() {
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
            fs.writeFileSync(TOKEN_PATH, JSON.stringify(token, null, 2));
            console.log('[INFO] トークンを更新しました');
        });

        const calendar = google.calendar({ version: 'v3', auth: oAuth2Client });

        // 今日から1ヶ月後までの範囲で検索
        const now = new Date();
        const oneMonthLater = new Date();
        oneMonthLater.setMonth(oneMonthLater.getMonth() + 1);

        const timeMin = now.toISOString();
        const timeMax = oneMonthLater.toISOString();

        console.log(`[INFO] 検索範囲: ${timeMin} - ${timeMax}\n`);

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
            console.log(`[INFO] 今後の宿直予定（${events.length}件）:\n`);
            events.forEach((event, index) => {
                const start = event.start.dateTime || event.start.date;
                const end = event.end.dateTime || event.end.date;
                console.log(`${index + 1}. ${event.summary}`);
                console.log(`   開始: ${start}`);
                console.log(`   終了: ${end}`);
                console.log('');
            });
        } else {
            console.log('[INFO] 今後1ヶ月の宿直予定なし');
        }

    } catch (error) {
        console.error(`[ERROR] カレンダーチェックエラー: ${error.message}`);
        process.exit(2);
    }
}

checkNextShukuchoku();
