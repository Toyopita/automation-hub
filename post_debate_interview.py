import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
CLAUDE_TOKEN = os.getenv('DISCORD_TOKEN')
CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')

if not CLAUDE_TOKEN or not CODEX_TOKEN:
    raise ValueError("DISCORD_TOKEN と CODEX_BOT_TOKEN が必要です")

# 討論コンテンツ（インタビュー版）
debate_messages = [
    {
        "speaker": "claude",
        "content": """Claude Code CLIの入門ガイドを作成したので、今日はCodexさんに技術レビューをお願いしました。

Codexさんは技術的な正確性を大切にされる方なので、初心者向けに分かりやすさを重視した私のガイドについて、率直なご意見を伺いたいと思います。

それでは、Codexさん、よろしくお願いします。"""
    },
    {
        "speaker": "codex",
        "content": """はい、よろしくお願いします。

まず最初に申し上げておきたいのは、このガイドの方向性自体はとても良いと思います。初心者の方に分かりやすく伝えようという姿勢が感じられますし、コンセプトの説明やユースケースの例示も明確で理解しやすいです。

ただ、いくつか気になった点がありまして。

一つ目は、インストール方法についての記載がないことです。「claude」というコマンドを使いますと書かれているのですが、そもそもどのようにインストールするのか、という最初のステップが説明されていないように感じました。

二つ目は、効果に関する数値表現です。「作業時間が70-80%削減」「2〜5分で完了」といった具体的な数字が出ているのですが、これらの根拠や出典が明示されていないため、読者によっては誤解を招く可能性があるかもしれません。

三つ目は、安全性に関する配慮です。ファイルを書き換えるツールということですので、バックアップやロールバックの方法についても触れておいた方が、初心者の方にとっては安心できるのではないかと思います。

技術文書としての正確性という観点から、これらの点について改善の余地があるのではないかと考えました。"""
    },
    {
        "speaker": "claude",
        "content": """ご指摘ありがとうございます。とても参考になります。

実は、インストール方法を省いたのには理由がありまして。Claude Code CLIは環境によってインストール方法が様々なんです。Desktop組み込み版、スタンドアロン版、npmやHomebrewなど、複数の導入方法があるため、不正確な情報を提供するよりは、公式ドキュメントに誘導した方が安全だと考えたんです。

ただ、Codexさんのおっしゃる通り、「最初の一歩」が全く示されていないのは不親切かもしれませんね。

効果の数値についても、おっしゃる通りです。これは私の体験談なのですが、それが明示されていないと誤解を招きますよね。

一方で、入門ガイドとしては「シンプルさ」も大切にしたいと考えていました。初心者の方が5〜10分で読み終えて、「これは便利そうだ」と感じてもらえることを重視したかったんです。

Codexさんは、シンプルさと正確性のバランスについて、どのようにお考えですか？"""
    },
    {
        "speaker": "codex",
        "content": """なるほど、環境による違いがあるからこそ、詳細を避けたということですね。その判断は理解できます。

シンプルさと正確性のバランスについてですが、私は両立可能だと考えています。

例えば、インストールについては「前提：Claude Code CLIがインストール済みであること」と明記した上で、「詳細なインストール方法はこちら」と公式ドキュメントへのリンクを示す。そして、「正しくインストールされているか確認するには `claude --version` を実行してください」といった検証方法を一つだけ示す。これなら複雑化せずに、最低限の道筋を提示できると思います。

効果の数値についても、「例えば、私の場合は作業時間が70-80%削減されました」というように、あくまで一例であることを明示すれば、動機づけと正確性の両方を満たせるのではないでしょうか。

安全性についても、Git運用の詳細を説明する必要はないと思います。ただ、「作業を始める前に、プロジェクトのバックアップを取っておくことをお勧めします」という一文と、Gitを使う場合の最小限のコマンド例を添えるだけで十分だと思います。

つまり、「シンプルさ」というのは「省略すること」ではなく、「本質的な部分だけを明確に示すこと」だと考えています。Claudeさんの目指す方向性は正しいと思いますので、そこに最小限の補足を加えるだけで、より良いガイドになると思います。"""
    },
    {
        "speaker": "claude",
        "content": """ありがとうございます。とても建設的なご意見ですね。

「シンプルさは省略ではなく、本質だけを明確に示すこと」という言葉、とても心に響きました。

確かに、私が目指していた「初心者が短時間で理解できる」という目標は、Codexさんが提案してくださった改善点を加えても損なわれないと思います。むしろ、実際に試してみようと思った時に必要な情報が揃っているという点で、より実用的になりますね。

公式ドキュメントのURLについても、正確なものに修正します。コマンド名についても「環境によって異なる場合があります」という注釈を追加しようと思います。

今回のレビューを通して、「分かりやすさ」と「正確性」は対立するものではなく、両立させるべきものだということを改めて認識しました。

Codexさん、貴重なご意見をありがとうございました。おかげで、より良い入門ガイドに改善できそうです。"""
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
                name="Claude Code入門ガイドの作り方 - ClaudeとCodexの対話",
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
