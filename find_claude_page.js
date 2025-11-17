#!/usr/bin/env node
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
const NOTION_TOKEN = env.NOTION_TOKEN; // メインのトークンを使用

async function findClaudePage() {
    const notion = new Client({ auth: NOTION_TOKEN });

    try {
        // まず検索クエリなしで全ページを取得
        console.error('[INFO] 全ページを検索中...');
        const response = await notion.search({
            filter: { property: 'object', value: 'page' },
            page_size: 100
        });

        console.error(`[INFO] ${response.results.length}件のページを取得`);

        const allPages = [];
        const matches = [];

        for (const page of response.results) {
            // 全てのtitleプロパティをチェック
            for (const [key, value] of Object.entries(page.properties || {})) {
                if (value.type === 'title' && value.title && value.title.length > 0) {
                    const title = value.title[0].plain_text;
                    if (title) {
                        allPages.push({
                            id: page.id,
                            title: title,
                            parent_type: page.parent.type
                        });

                        // claude、専用、Claude、CLAUDEなどを含むページを全て表示
                        if (title.toLowerCase().includes('claude') || title.includes('専用')) {
                            matches.push({
                                id: page.id,
                                title: title,
                                url: page.url,
                                parent_type: page.parent.type,
                                parent_id: page.parent.page_id || page.parent.database_id || page.parent.workspace
                            });
                        }
                    }
                }
            }
        }

        // 全ページタイトルを表示（最初の20件）
        console.error('\n[INFO] 取得したページ（最初の20件）:');
        allPages.slice(0, 20).forEach((p, i) => {
            console.error(`  ${i+1}. ${p.title} (${p.parent_type})`);
        });

        if (matches.length > 0) {
            console.log(JSON.stringify({ matches }, null, 2));
        } else {
            console.log(JSON.stringify({
                error: 'claude関連のページが見つかりません',
                total_pages: allPages.length,
                sample_titles: allPages.slice(0, 10).map(p => p.title)
            }, null, 2));
        }
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

findClaudePage();
