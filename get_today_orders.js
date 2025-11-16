#!/usr/bin/env node
/**
 * Notion APIを使って今日の発注履歴を取得するスクリプト
 */
const { Client } = require('@notionhq/client');
const fs = require('fs');
const path = require('path');

// .envファイルから環境変数を読み込み
function loadEnv() {
    const envPath = path.join(__dirname, '.env');
    const envContent = fs.readFileSync(envPath, 'utf-8');
    const env = {};

    envContent.split('\n').forEach((line) => {
        line = line.trim();
        if (line && !line.startsWith('#') && line.includes('=')) {
            const [key, ...valueParts] = line.split('=');
            env[key.trim()] = valueParts.join('=').trim();
        }
    });

    return env;
}

const env = loadEnv();
const NOTION_TOKEN = env.NOTION_TOKEN_ORDER;
const NOTION_ORDER_DB = '19800160-1818-8095-987d-eff320494e12';

async function getTodayOrders() {
    const notion = new Client({ auth: NOTION_TOKEN });

    // 今日の開始時刻と終了時刻
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString();

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString();

    try {
        const response = await notion.databases.query({
            database_id: NOTION_ORDER_DB,
            filter: {
                and: [
                    { property: '発注完了日', date: { on_or_after: todayStr } },
                    { property: '発注完了日', date: { before: tomorrowStr } },
                ],
            },
            sorts: [{ property: '発注完了日', direction: 'descending' }],
        });

        const orders = [];

        for (const page of response.results) {
            // 名前
            const titleProp = page.properties['名前'];
            const name = titleProp?.title?.[0]?.plain_text || '（タイトルなし）';

            // 発注書URL
            const urlProp = page.properties['発注書'];
            const url = urlProp?.url || '';

            // 分類
            const categoryProp = page.properties['分類'];
            const category = categoryProp?.select?.name || '';

            // 発注完了日
            const createdTimeProp = page.properties['発注完了日'];
            const createdTime = createdTimeProp?.created_time || '';

            orders.push({
                name,
                url,
                category,
                created_time: createdTime,
            });
        }

        return orders;
    } catch (error) {
        console.error('Error fetching orders:', error.message);
        return [];
    }
}

getTodayOrders()
    .then((orders) => {
        console.log(JSON.stringify({ orders }));
    })
    .catch((error) => {
        console.error('Error:', error);
        process.exit(1);
    });
