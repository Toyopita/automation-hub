#!/usr/bin/env node
/**
 * Google Calendar MCPを使って今日のイベントを取得するスクリプト
 */
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

const CALENDAR_IDS = [
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com',
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com',
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com',
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com',
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com',
    'izumooyashiro.osaka.takeshi@gmail.com',
    'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com',
];

const CALENDAR_NAMES = {
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com': '六曜カレンダー',
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com': '祖霊社',
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com': '本社',
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com': '年祭',
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com': '冥福祭',
    'izumooyashiro.osaka.takeshi@gmail.com': 'プライベート',
    'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com': '関西イベント情報',
};

async function getTodayEvents() {
    // 日本時間の今日の範囲を取得
    const now = new Date();
    const jstNow = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));

    const today = new Date(jstNow);
    today.setHours(0, 0, 0, 0);

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    // 日本時間をUTCに変換
    const timeMin = new Date(today.getTime() - (9 * 60 * 60 * 1000)).toISOString().replace(/\.000Z$/, '');
    const timeMax = new Date(tomorrow.getTime() - (9 * 60 * 60 * 1000)).toISOString().replace(/\.000Z$/, '');

    const allEvents = [];

    // ここでGoogle Calendar APIを直接呼び出す代わりに、
    // google-auth-library と google-apis を使います
    const { google } = require('googleapis');
    const fs = require('fs').promises;
    const path = require('path');

    // 既存のトークンを読み込む
    const tokenPath = path.join(process.env.HOME, '.config/google-calendar-mcp/tokens.json');
    const tokenData = JSON.parse(await fs.readFile(tokenPath, 'utf-8'));

    const { access_token } = tokenData.normal;

    // OAuth2クライアントを作成
    const oauth2Client = new google.auth.OAuth2();
    oauth2Client.setCredentials({ access_token });

    const calendar = google.calendar({ version: 'v3', auth: oauth2Client });

    for (const calendarId of CALENDAR_IDS) {
        try {
            const response = await calendar.events.list({
                calendarId,
                timeMin,
                timeMax,
                singleEvents: true,
                orderBy: 'startTime',
            });

            const events = response.data.items || [];
            const calendarName = CALENDAR_NAMES[calendarId] || calendarId;

            for (const event of events) {
                const start = event.start.dateTime || event.start.date;
                const end = event.end.dateTime || event.end.date;

                let startTime = '';
                let endTime = '';

                if (event.start.dateTime) {
                    const startDt = new Date(start);
                    const endDt = new Date(end);
                    startTime = `${String(startDt.getHours()).padStart(2, '0')}:${String(startDt.getMinutes()).padStart(2, '0')}`;
                    endTime = `${String(endDt.getHours()).padStart(2, '0')}:${String(endDt.getMinutes()).padStart(2, '0')}`;
                }

                allEvents.push({
                    title: event.summary || '（タイトルなし）',
                    start,
                    end,
                    start_time: startTime,
                    end_time: endTime,
                    calendar_name: calendarName,
                });
            }
        } catch (error) {
            console.error(`Error fetching calendar ${calendarId}:`, error.message);
        }
    }

    return allEvents;
}

getTodayEvents()
    .then((events) => {
        console.log(JSON.stringify({ events }));
    })
    .catch((error) => {
        console.error('Error:', error);
        process.exit(1);
    });
