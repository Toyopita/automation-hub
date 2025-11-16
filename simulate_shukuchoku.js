#!/usr/bin/env node
/**
 * 11/20（水）朝6:40の宿直チェックをシミュレート
 */

const { google } = require('googleapis');
const path = require('path');
const fs = require('fs');

const CALENDAR_ID = '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com';
const CREDENTIALS_PATH = path.join(process.env.HOME, 'shared-google-calendar', 'credentials.json');
const TOKEN_PATH = path.join(process.env.HOME, 'discord-mcp-server', 'google_calendar_token.json');

async function simulateCheck() {
    try {
        const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
        const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));

        const { client_secret, client_id, redirect_uris } = credentials.installed;
        const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
        oAuth2Client.setCredentials(token);

        oAuth2Client.on('tokens', (tokens) => {
            if (tokens.refresh_token) {
                token.refresh_token = tokens.refresh_token;
            }
            token.access_token = tokens.access_token;
            token.expiry_date = tokens.expiry_date;
            fs.writeFileSync(TOKEN_PATH, JSON.stringify(token, null, 2));
        });

        const calendar = google.calendar({ version: 'v3', auth: oAuth2Client });

        // 11/20（水）6:40時点での判定をシミュレート
        // チェック範囲: 11/19（火）18:00 〜 11/20（水）09:00
        const yesterday = new Date('2025-11-19');
        yesterday.setHours(18, 0, 0, 0);
        const timeMin = yesterday.toISOString();

        const today = new Date('2025-11-20');
        today.setHours(9, 0, 0, 0);
        const timeMax = today.toISOString();

        console.log('=== 11/20（水）朝6:40時点での宿直チェックシミュレーション ===');
        console.log(`[INFO] 宿直チェック範囲: ${timeMin} - ${timeMax}\n`);

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
            console.log('\n[結果] 宿直中のため、自動化をスキップ（exit code 1）');
        } else {
            console.log('[INFO] 宿直予定なし');
            console.log('\n[結果] 宿直予定なし。自動化を実行（exit code 0）');
        }

    } catch (error) {
        console.error(`[ERROR] ${error.message}`);
    }
}

simulateCheck();
