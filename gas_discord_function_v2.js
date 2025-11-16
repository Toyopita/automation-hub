/**
 * Discord Webhookにメッセージを投稿する関数（2チャンネル版）
 * GASスクリプトに追加してください
 */

/**
 * Discordに今日の予定を投稿（予定のみ）
 * @param {Array} events - カレンダーイベントの配列
 */
function sendScheduleToDiscord(events) {
  const props = PropertiesService.getScriptProperties();
  const WEBHOOK_URL = props.getProperty('DISCORD_WEBHOOK_URL_SCHEDULE');

  if (!WEBHOOK_URL) {
    Logger.log('❌ DISCORD_WEBHOOK_URL_SCHEDULEが設定されていません');
    return;
  }

  // 今日の日付を取得
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();
  const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
  const weekday = weekdays[today.getDay()];
  const todayStr = `${year}年${month}月${day}日（${weekday}）`;

  // 今日の六曜を取得
  const rokuyoEvent = events.find(e =>
    e.calendarName === '六曜カレンダー' &&
    isSameDay(new Date(e.actualStartDate), today)
  );
  const rokuyo = rokuyoEvent ? rokuyoEvent.title : '不明';

  // 今日のイベントをフィルタリング
  const todayEvents = events.filter(e => {
    if (e.calendarName === '六曜カレンダー') return false;
    return isSameDay(new Date(e.actualStartDate), today);
  });

  todayEvents.sort((a, b) => a.startTime - b.startTime);

  // 今日の予定セクションを作成
  let eventsSection = '';
  if (todayEvents.length > 0) {
    todayEvents.forEach(event => {
      const startTime = formatTime(event.startTime);
      const endTime = formatTime(event.endTime);
      const calendarName = event.calendarName;

      eventsSection += `\`${startTime} - ${endTime}\` ${event.title}（${calendarName}）\n\n`;
    });
  } else {
    eventsSection = '*本日の予定はありません*\n\n';
  }

  // メッセージを組み立て（予定のみ）
  const message = `📅 **${todayStr}の予定**

━━━━━━━━━━━━━━━━━━━━━━━━

**【六曜】** ${rokuyo}

━━━━━━━━━━━━━━━━━━━━━━━━

**【本日の予定】**

${eventsSection}━━━━━━━━━━━━━━━━━━━━━━━━
\`自動送信 | ${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')} ${String(today.getHours()).padStart(2, '0')}:${String(today.getMinutes()).padStart(2, '0')}\``;

  // Discord Webhookに投稿
  const payload = {
    content: message
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();

    if (responseCode === 204 || responseCode === 200) {
      Logger.log('✅ Discord投稿成功（予定）');
    } else {
      Logger.log(`❌ Discord投稿失敗（予定）: ${responseCode}`);
      Logger.log(response.getContentText());
    }
  } catch (error) {
    Logger.log(`❌ Discord投稿エラー（予定）: ${error}`);
  }
}

/**
 * Discordにタスク通知を投稿（タスクのみ）
 * @param {Array} tasks - Notionタスクの配列
 */
function sendTasksToDiscord(tasks) {
  const props = PropertiesService.getScriptProperties();
  const WEBHOOK_URL = props.getProperty('DISCORD_WEBHOOK_URL_TASK');

  if (!WEBHOOK_URL) {
    Logger.log('❌ DISCORD_WEBHOOK_URL_TASKが設定されていません');
    return;
  }

  // 今日の日付を取得
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();

  // 締切間近のタスクセクションを作成（最大5件表示）
  let tasksSection = '';
  const displayTasks = tasks.slice(0, 5);

  displayTasks.forEach(task => {
    const title = task.properties['タスク名']?.title?.[0]?.plain_text || '（タイトルなし）';
    const dueRaw = task.properties['期限']?.date?.start || '';
    const dueDate = new Date(dueRaw);
    const diffTime = dueDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    // プロジェクト名を取得
    const relation = task.properties['プロジェクト名']?.relation;
    let projectName = '日常業務';
    if (relation && relation.length > 0) {
      const projectId = relation[0].id;
      const fetchedName = fetchProjectNameById(projectId, props.getProperty('NOTION_TOKEN'));
      if (fetchedName) projectName = fetchedName;
    }

    // 日付フォーマット（MM/DD）
    const dueMonth = dueDate.getMonth() + 1;
    const dueDay = dueDate.getDate();
    const dueDateStr = `${dueMonth}/${dueDay}`;

    // 緊急度に応じた絵文字
    let emoji = '📌';
    let statusText = dueDateStr;

    if (diffDays < 0) {
      emoji = '🔴';
      statusText = `期限超過 ${dueDateStr}`;
    } else if (diffDays === 0) {
      emoji = '⚠️';
      statusText = `本日期限 ${dueDateStr}`;
    }

    tasksSection += `${emoji} ${title}\n\`${statusText}\` | ${projectName}\n\n`;
  });

  if (tasks.length > 5) {
    const remaining = tasks.length - 5;
    tasksSection += `*他${remaining}件の未了タスクがあります*\n\n`;
  } else if (tasks.length === 0) {
    tasksSection = '*締切間近のタスクはありません*\n\n';
  }

  // メッセージを組み立て（タスクのみ）
  const message = `📋 **締切間近のタスク**

━━━━━━━━━━━━━━━━━━━━━━━━

${tasksSection}📋 タスクDB: https://www.notion.so/1c8001601818807cb083f475eb3a07b9

━━━━━━━━━━━━━━━━━━━━━━━━
\`自動送信 | ${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')} ${String(today.getHours()).padStart(2, '0')}:${String(today.getMinutes()).padStart(2, '0')}\``;

  // Discord Webhookに投稿
  const payload = {
    content: message
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();

    if (responseCode === 204 || responseCode === 200) {
      Logger.log('✅ Discord投稿成功（タスク）');
    } else {
      Logger.log(`❌ Discord投稿失敗（タスク）: ${responseCode}`);
      Logger.log(response.getContentText());
    }
  } catch (error) {
    Logger.log(`❌ Discord投稿エラー（タスク）: ${error}`);
  }
}

/**
 * 2つの日付が同じ日かチェック
 */
function isSameDay(date1, date2) {
  return date1.getFullYear() === date2.getFullYear() &&
         date1.getMonth() === date2.getMonth() &&
         date1.getDate() === date2.getDate();
}

/**
 * スクリプトプロパティにWebhook URLを設定する関数
 * 初回のみ実行してください
 */
function setDiscordWebhookUrls() {
  const props = PropertiesService.getScriptProperties();

  // 予定用Webhook URL
  const WEBHOOK_URL_SCHEDULE = 'https://discord.com/api/webhooks/1434377710863515698/D1i7mp6Kx4pSxTUpYRLELAjQcy1LmnaDbyc8OpuTrYIUKef4-tMMzJbvWBz1cWUOLgG3';
  props.setProperty('DISCORD_WEBHOOK_URL_SCHEDULE', WEBHOOK_URL_SCHEDULE);

  // タスク用Webhook URL
  const WEBHOOK_URL_TASK = 'https://discord.com/api/webhooks/1434390893414318121/3oUOSfBookgeDuJdnuH4dRoCelnt6H1amXCtN1XYnuQhuq8LjJkG59Ca88CuEo7ETO4h';
  props.setProperty('DISCORD_WEBHOOK_URL_TASK', WEBHOOK_URL_TASK);

  Logger.log('✅ DISCORD_WEBHOOK_URL_SCHEDULEとDISCORD_WEBHOOK_URL_TASKを設定しました');
}
