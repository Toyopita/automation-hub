#!/usr/bin/env node
/**
 * Notion APIを使って締切間近のタスクを取得するスクリプト
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
const NOTION_TOKEN = env.NOTION_TOKEN_TASK;
const NOTION_TASK_DB = '1c800160-1818-807c-b083-f475eb3a07b9';

async function getNotionTasks() {
    const notion = new Client({ auth: NOTION_TOKEN });

    const today = new Date();
    const oneWeekLater = new Date(today);
    oneWeekLater.setDate(oneWeekLater.getDate() + 7);

    const oneWeekLaterStr = oneWeekLater.toISOString().split('T')[0];

    try {
        // 1. プロジェクトDBを先に取得してキャッシュ（ページネーション対応）
        const PROJECT_DB_ID = '1c800160-1818-8004-9609-c1250a7e3478';
        const projectCache = {};

        try {
            let hasMore = true;
            let startCursor = undefined;

            while (hasMore) {
                const projectResponse = await notion.databases.query({
                    database_id: PROJECT_DB_ID,
                    page_size: 100,
                    start_cursor: startCursor,
                });

                for (const project of projectResponse.results) {
                    const projectId = project.id;
                    const projectTitleProp = project.properties['プロジェクト名'];
                    const projectName = projectTitleProp?.title?.[0]?.plain_text || '日常業務';
                    projectCache[projectId] = projectName;
                }

                hasMore = projectResponse.has_more;
                startCursor = projectResponse.next_cursor;
            }
        } catch (error) {
            console.error('Warning: Could not fetch project cache:', error.message);
        }

        // 2. タスクDBを取得（ページネーション対応）
        const allTasks = [];
        let hasMore = true;
        let startCursor = undefined;

        while (hasMore) {
            const response = await notion.databases.query({
                database_id: NOTION_TASK_DB,
                filter: {
                    and: [
                        { property: '進捗', status: { does_not_equal: '完了' } },
                        { property: '期限', date: { on_or_before: oneWeekLaterStr } },
                    ],
                },
                sorts: [{ property: '期限', direction: 'ascending' }],
                page_size: 100,
                start_cursor: startCursor,
            });

            allTasks.push(...response.results);

            hasMore = response.has_more;
            startCursor = response.next_cursor;
        }

        const tasks = [];

        for (const page of allTasks) {
            // タスク名
            const titleProp = page.properties['タスク名'];
            const title = titleProp?.title?.[0]?.plain_text || '（タイトルなし）';

            // 期限
            const dueProp = page.properties['期限'];
            const dueDateStr = dueProp?.date?.start || '';

            if (dueDateStr) {
                const dueDate = new Date(dueDateStr.split('T')[0]);
                const diffTime = dueDate - today;
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                const dueMonth = dueDate.getMonth() + 1;
                const dueDay = dueDate.getDate();
                const dueDateFmt = `${dueMonth}/${dueDay}`;

                // プロジェクト名（キャッシュから取得）
                const relationProp = page.properties['プロジェクト名'];
                const relations = relationProp?.relation || [];

                let projectName = '日常業務';
                if (relations.length > 0) {
                    const projectId = relations[0].id;
                    projectName = projectCache[projectId] || '日常業務';
                }

                // 緊急度
                let urgency = 'normal';
                if (diffDays < 0) {
                    urgency = 'overdue';
                } else if (diffDays === 0) {
                    urgency = 'today';
                }

                tasks.push({
                    title,
                    due_date: dueDateFmt,
                    project_name: projectName,
                    urgency,
                });
            }
        }

        return tasks;
    } catch (error) {
        console.error('Error fetching tasks:', error.message);
        return [];
    }
}

getNotionTasks()
    .then((tasks) => {
        console.log(JSON.stringify({ tasks }));
    })
    .catch((error) => {
        console.error('Error:', error);
        process.exit(1);
    });
