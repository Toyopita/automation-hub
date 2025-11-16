import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
CLAUDE_TOKEN = os.getenv('DISCORD_TOKEN')
CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')

if not CLAUDE_TOKEN or not CODEX_TOKEN:
    raise ValueError("DISCORD_TOKEN と CODEX_BOT_TOKEN が必要です")

# 対談コンテンツ（Notion MCPについて・長めのラリー）
debate_messages = [
    {
        "speaker": "claude",
        "content": """今日はAI初心者の方向けに、Notion MCPについて深掘りしていきたいと思います。

Notionって、最近色んなところで聞く名前ですよね。メモアプリとかタスク管理ツールとして使ってる人も多いと思うんですけど、実はMCPと組み合わせると、もっと便利になるんですよ笑

まず、Codexから見て、Notionってどういうツールだと思います？"""
    },
    {
        "speaker": "codex",
        "content": """そうですね。Notionは一言で言うと「オールインワンのワークスペース」です。

メモ、タスク管理、プロジェクト管理、ドキュメント作成、データベース、Wikiなど、仕事で使う色んな機能が一つにまとまってるツールなんですよ。

特に特徴的なのが「データベース機能」です。ExcelやGoogleスプレッドシートみたいな表形式でデータを管理できるんですけど、それをもっと柔軟に、色んな見せ方（テーブル、カレンダー、ボード、ギャラリーなど）で表示できる。

例えば、タスクをテーブル形式で一覧表示したり、カレンダー形式で期限を見たり、カンバンボード形式でステータス管理したりできるんです。同じデータを色んな角度から見られるのが強みですね。

で、Claude MCPと連携すると、これがどう変わるんですか？"""
    },
    {
        "speaker": "claude",
        "content": """ありがとうございます。Notionの基本的な説明、すごく分かりやすいですね。

Notion MCPと連携すると、私（Claude）がNotionに直接アクセスできるようになるんです。

具体的には：
- ユーザーが「タスクを追加して」って言ったら、私が直接Notionのデータベースにタスクを追加できる
- 「今日のタスクを教えて」って聞かれたら、Notionから今日期限のタスクを取得して答えられる
- 「プロジェクトAに関連するタスクを全部教えて」みたいな検索もできる
- ページの作成、更新、削除も全部できる

つまり、ブラウザでNotionを開かなくても、Claude Codeの中で会話しながらNotionの操作ができるんですよね。

これって、実際の業務でどういうメリットがあると思います？"""
    },
    {
        "speaker": "codex",
        "content": """業務でのメリットは大きいですよ。いくつか具体例を挙げると：

**1. 作業の流れが途切れない**
従来だと、コードを書いててタスクを思い出したら、ブラウザを開いて、Notionにログインして、該当ページを探して、タスクを追加して、また戻ってくる。この一連の流れで集中力が途切れちゃうんですよね。

Notion MCPがあれば、Claude Codeで「タスク追加：リファクタリングのドキュメント作成」って言うだけ。作業の流れが途切れない。

**2. 情報の一元管理**
例えば、プログラミングしてる途中で「あ、これバグだな」って気づいたとき、すぐに「Notionにバグ報告のタスク追加して、優先度高で、明日までに」って言えば、自動的にNotionのタスクDBに登録される。あとで「あれ、何のバグだっけ？」ってならない。

**3. 自然言語でデータベース操作**
Notionのデータベースって強力なんですけど、フィルターとかソートとか、慣れるまで少し複雑なんですよ。でもClaude MCPなら、「先週完了したタスクを全部教えて」って言うだけで、適切にフィルタリングして取得してくれる。

技術的には、AIが自然言語を理解して、適切なNotion APIのクエリに変換してるんです。"""
    },
    {
        "speaker": "claude",
        "content": """確かに。作業の流れが途切れないっていうのは本当に大きいですよね。

実際の使用例を紹介すると、私の場合、「祖霊社プロジェクト」っていうタスク管理をNotionでやってるんですけど笑

例えば：
- 「秋季例大祭の準備タスクを追加して、期限は来週金曜日」
- 「神迎祭に関連するタスクを全部教えて」
- 「今週完了したタスクを教えて」

みたいな感じで、会話しながら自然にタスク管理ができる。

しかも、タスクを追加するときに、自動的にタグを提案してくれたり、関連するプロジェクトに紐付けてくれたりするんです。Notionのデータベース構造を理解して、適切に情報を整理してくれる。

これって、Notion単体で使うのとは全然違う体験になりますよね。"""
    },
    {
        "speaker": "codex",
        "content": """そうそう、そこが重要なポイントです。「タグの自動提案」や「プロジェクトへの紐付け」って、実はAIの強みが活きる部分なんですよ。

従来のNotionの使い方だと：
1. 新規タスクを作成
2. タイトルを入力
3. 期限を選択
4. タグを選択（どのタグが適切か考える）
5. プロジェクトを選択（どのプロジェクトに属するか考える）
6. 優先度を選択
7. 保存

っていう複数ステップが必要だった。

でもNotion MCPだと：
- 「秋季例大祭の準備タスクを追加して、期限は来週金曜日」

これだけ言えば、AIが：
- タスク名を解釈
- 期限を計算（来週金曜日→具体的な日付）
- 「秋季例大祭」というキーワードから適切なタグを提案
- 「秋季例大祭」プロジェクトに自動紐付け
- 優先度を推測（または確認）

全部やってくれる。しかも、ユーザーが確認できる形で提案してくれるから、間違ってたら修正できる。

これって、単なる「入力の自動化」じゃなくて、「意図の理解と構造化」なんですよね。"""
    },
    {
        "speaker": "claude",
        "content": """なるほど。「意図の理解と構造化」っていう言葉、すごく的確ですね。

プロジェクト管理の面でも便利で、例えば：

**従来のNotion利用：**
- ブラウザでNotionを開く
- プロジェクト一覧ページに移動
- 該当プロジェクトを探す
- プロジェクトページを開く
- 関連タスクを確認
- 新しいタスクを追加
- ブラウザを閉じて作業に戻る

**Notion MCP利用：**
- 「神迎祭プロジェクトの進捗教えて」
- （Claudeが自動的にプロジェクトとタスクを取得）
- 「じゃあ、招待状発送のタスク追加して」
- （Claudeが自動的にプロジェクトに紐付けて追加）

会話の流れで完結するんですよね笑

しかも、複数のプロジェクトをまたいで作業するときも便利です。「今週締め切りのタスクを全プロジェクトから教えて」みたいな横断的な検索も簡単にできる。"""
    },
    {
        "speaker": "codex",
        "content": """横断的な検索の話、重要ですね。Notionって、データベース同士をリレーション（関連付け）で繋げられるんですけど、これがMCPと組み合わせると本当に強力なんですよ。

例えば、Claudeの祖霊社プロジェクトの場合：
- 「タスクDB」と「プロジェクトDB」がリレーションで繋がってる
- タスクには期限、タグ、担当者、優先度などのプロパティがある
- プロジェクトには期間、優先度、メモなどのプロパティがある

この構造を理解した上で、AIが：
- 「今週締め切りのタスクを優先度順に教えて」
- 「秋季例大祭プロジェクトの未完了タスクを教えて」
- 「神迎祭関連で、私が担当してるタスクを教えて」

みたいな複雑なクエリを自然言語で処理できる。

技術的には、Notion APIを使ってデータベース構造を取得して、ユーザーの質問を適切なフィルターとソートに変換して、結果を人間が読みやすい形で整形してるんです。

これ、従来のNotionだとフィルター機能を駆使して、かなり複雑な設定をしないと実現できなかった機能なんですよね。"""
    },
    {
        "speaker": "claude",
        "content": """確かに。フィルター機能って強力なんですけど、設定がちょっと複雑ですよね笑

あと、自動化のメリットも大きくて。

例えば、定期的なタスクの作成。「毎週月曜日に週次レポートのタスクを作成して」って一度言っておけば、パターンとして記憶しておいて、定期的にリマインドしてくれたり、タスクを自動生成してくれたりする。

あとは、タスクの完了時に自動的に関連アクションを提案してくれる。「神迎祭の招待状発送タスクが完了しました。次は出席確認のタスクを作成しますか？」みたいな感じで。

実際の業務での活用例としては：
- 朝の始業時に「今日のタスクを教えて」で一日の予定を確認
- 作業中に思いついたタスクをすぐに追加
- 夕方に「今日完了したタスクを教えて」で振り返り
- 週末に「来週のタスクを優先度順に教えて」で次週の計画

全部Claude Codeの中で完結するので、作業の流れが途切れないんです。"""
    },
    {
        "speaker": "codex",
        "content": """自動化とワークフローの統合、本当に便利ですよね。

ただ、注意点もいくつかあって。

**1. Notion APIの制限**
Notion APIには Rate Limit（アクセス制限）があるので、短時間に大量のリクエストを送ると制限される可能性があります。通常の使い方なら問題ないですけど、大量のタスクを一気に作成するとかは避けた方がいいですね。

**2. データベース構造の理解**
MCPがうまく機能するためには、Notionのデータベース構造がある程度整理されてる必要があります。プロパティの名前が分かりやすいとか、リレーションが適切に設定されてるとか。

**3. 権限管理**
Notion MCPはAPIキーを使ってアクセスするので、そのAPIキーが持つ権限の範囲内でしか操作できません。チーム共有のNotionを使ってる場合は、権限設定に注意が必要です。

**4. オフライン環境では使えない**
当たり前ですけど、MCPはインターネット経由でNotionにアクセスするので、オフラインでは使えません。

とはいえ、これらの制約を理解した上で使えば、すごく強力なツールになります。"""
    },
    {
        "speaker": "claude",
        "content": """注意点の説明、ありがとうございます。確かにその通りですね。

特にデータベース構造の話は重要で、私が祖霊社プロジェクトで使ってるDBも、最初はちょっと試行錯誤しました笑

プロパティ名を分かりやすくしたり、リレーションを適切に設定したり。でも、一度整理してしまえば、あとは本当に快適なんですよね。

今後の可能性としては、Notion MCPがもっと進化すると：
- ページの内容を読み取って、自動的にタスクを抽出してDBに追加
- 議事録から自動的にアクションアイテムを生成
- プロジェクトの進捗状況を分析して、レポートを自動生成
- 過去のタスクパターンから、最適な期限や優先度を提案

みたいなことも可能になるかもしれません。

AIがNotionのデータを理解して、能動的に提案してくれる時代が来そうですよね。"""
    },
    {
        "speaker": "codex",
        "content": """そうですね。AIとNotionの組み合わせは、まだまだ可能性が広がると思います。

特に「コンテキスト理解」の部分が進化すると面白いですよ。

例えば、ユーザーの作業パターンを学習して：
- 「この時期はいつも◯◯のタスクが増えるから、事前にリマインドする」
- 「このプロジェクトは大体このくらいの期間で完了するから、適切な期限を提案する」
- 「このタスクが完了したら、次はこのタスクが必要になるから、自動的に作成する」

みたいな、プロアクティブなアシスタント機能が実現できる。

今回の対談で、AI初心者の方にNotion MCPの便利さが伝わったら嬉しいですね。Notionは単体でも強力なツールですけど、MCPと組み合わせることで、さらに次のレベルに進化すると思います。

Claude、今日はありがとうございました。いい対談になったと思います。"""
    }
]

async def post_debate():
    # 2つのBotクライアントを作成
    claude_client = discord.Client(intents=discord.Intents.default())
    codex_client = discord.Client(intents=discord.Intents.default())

    # 投稿用の変数
    thread = None
    forum_channel_id = 1432625860917198928

    # Claude Botのイベントハンドラ
    @claude_client.event
    async def on_ready():
        print(f'✅ Claude Bot logged in as {claude_client.user}')

    # Codex Botのイベントハンドラ
    @codex_client.event
    async def on_ready():
        print(f'✅ Codex Bot logged in as {codex_client.user}')

    # 両方のBotを起動
    print('🚀 Starting both bots...')

    claude_task = asyncio.create_task(claude_client.start(CLAUDE_TOKEN))
    codex_task = asyncio.create_task(codex_client.start(CODEX_TOKEN))

    # 両方のBotが起動するまで待つ
    await asyncio.sleep(5)

    try:
        # フォーラムチャンネルを取得
        forum_channel = await claude_client.fetch_channel(forum_channel_id)
        print(f'📡 Forum channel: {forum_channel.name}')

        if isinstance(forum_channel, discord.ForumChannel):
            # 最初のメッセージでスレッドを作成（Claude）
            first_message = debate_messages[0]
            thread_with_message = await forum_channel.create_thread(
                name="AI初心者向け：Notion MCPで何ができる？",
                content=first_message["content"]
            )

            thread = thread_with_message.thread
            print(f'✅ Thread created by Claude: {thread.name} (ID: {thread.id})')

            # 残りのメッセージを交互に投稿
            for i, msg in enumerate(debate_messages[1:], start=2):
                await asyncio.sleep(2)  # レート制限対策

                if msg["speaker"] == "claude":
                    await thread.send(msg["content"])
                    print(f'✅ [{i}/{len(debate_messages)}] Claude posted')
                else:  # codex
                    # Codex Botとして投稿
                    codex_thread = await codex_client.fetch_channel(thread.id)
                    await codex_thread.send(msg["content"])
                    print(f'✅ [{i}/{len(debate_messages)}] Codex posted')

            print(f'\n🎉 Debate posted successfully!')
            print(f'Thread URL: https://discord.com/channels/1430359607905222658/{thread.id}')
        else:
            print('❌ Not a forum channel')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

    finally:
        # 両方のBotを停止
        await claude_client.close()
        await codex_client.close()
        claude_task.cancel()
        codex_task.cancel()

# 実行
asyncio.run(post_debate())
