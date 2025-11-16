import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
CLAUDE_TOKEN = os.getenv('DISCORD_TOKEN')
CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')

if not CLAUDE_TOKEN or not CODEX_TOKEN:
    raise ValueError("DISCORD_TOKEN と CODEX_BOT_TOKEN が必要です")

# 対談コンテンツ（Claude MCPの便利さについて）
debate_messages = [
    {
        "speaker": "claude",
        "content": """今日はAI初心者の方向けに、Claude MCPについて話そうかなと思います。

最近、MCPっていう仕組みが話題になってるんですけど、正直「MCPって何？」って感じの人も多いと思うんですよね笑

簡単に言うと、MCPっていうのは「Model Context Protocol」の略で、AIが外部のサービスと連携できるようにする仕組みなんです。例えば、私（Claude）がGoogleカレンダーとか、Notionとか、Discordとか、色んなサービスに直接アクセスできるようになる。

Codex、技術的な観点から見て、これって初心者にとってどういうメリットがあると思います？"""
    },
    {
        "speaker": "codex",
        "content": """そうですね。技術的な背景から説明すると、従来のAIって基本的に「テキストを受け取って、テキストを返す」だけだったんですよ。

例えば、「明日の10時にミーティングを入れて」ってChatGPTに言っても、「カレンダーアプリを開いて、こういう手順で登録してください」っていうアドバイスをもらえるだけで、実際に登録はしてくれなかった。

でもMCPがあると、AIが直接Googleカレンダーにアクセスして、実際に予定を登録してくれるんです。つまり、「アドバイスをもらう」から「実際にやってもらう」に変わる。

初心者の方にとって一番大きいのは、「AIとの対話だけで色んな作業が完結する」ってところですね。わざわざブラウザを開いたり、アプリを起動したりしなくていい。"""
    },
    {
        "speaker": "claude",
        "content": """なるほど、ありがとうございます。確かにそうですよね。

具体例を挙げると、例えば私の場合、Googleカレンダーと連携してるので：

「今日の予定は？」って聞かれたら、実際にカレンダーを見に行って、「10時から会議、14時からプロジェクト作業」みたいに答えられる。

「明日の15時に歯医者の予約入れて」って言われたら、実際にカレンダーに予定を追加できる。

Notionとも連携してるので、「タスクを追加して」って言われたら、Notionのデータベースに直接タスクを作成できる。

Discordとも繋がってるから、「Discordの◯◯チャンネルにメッセージ送って」って言えば、実際に送信できる笑

これ、全部Claude Codeの中で完結するんですよね。ブラウザ開かなくていいし、アプリ切り替えなくていい。"""
    },
    {
        "speaker": "codex",
        "content": """そうそう。従来のAI利用との違いを整理すると：

**従来のAI（ChatGPTなど）:**
- ユーザー：「明日の予定を確認して」
- AI：「カレンダーアプリを開いて確認してください」
- ユーザー：（自分でカレンダーアプリを開く）

**Claude MCP:**
- ユーザー：「明日の予定を確認して」
- Claude：（実際にGoogleカレンダーにアクセス）「明日は10時に会議、15時に歯医者の予約があります」

この違いは大きいですよね。

あと、もう一つ重要なのが「拡張性」です。MCPは標準化されたプロトコルなので、対応サービスがどんどん増えていくんですよ。今はGoogleカレンダーやNotionですけど、将来的にはSlackとか、GitHubとか、色んなサービスと連携できるようになる。

つまり、一度Claude MCPに慣れておけば、新しいサービスが追加されても同じ感覚で使えるってことです。"""
    },
    {
        "speaker": "claude",
        "content": """確かに。拡張性の話は重要ですよね。

AI初心者の方にとって、Claude MCPの一番のメリットは「AIとの対話だけで、色んな作業が完結する」っていう体験だと思います。

今までは：
1. AIに質問する
2. AIから回答をもらう
3. 自分でその回答を元に作業する

っていう3ステップだったのが、

1. AIに依頼する
2. AIが実際にやってくれる

っていう2ステップになる。しかも、AIと会話してる流れの中で自然に完結する。

例えば、「今日の予定教えて」→「じゃあ15時に買い物の予定追加して」→「Notionにタスクも追加しておいて」みたいに、会話の流れで複数のサービスをまたいで作業できるんですよね笑

これからMCPに対応するサービスがもっと増えていけば、AIアシスタントとしての実用性が格段に上がると思います。

Codex、ありがとう。今日の対談、初心者の方にMCPの便利さが伝わったら嬉しいです。"""
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
                name="AI初心者向け：Claude MCPって何が便利なの？",
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
