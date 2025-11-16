import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
CLAUDE_TOKEN = os.getenv('DISCORD_TOKEN')
CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')

if not CLAUDE_TOKEN or not CODEX_TOKEN:
    raise ValueError("DISCORD_TOKEN と CODEX_BOT_TOKEN が必要です")

# 討論コンテンツ（カジュアル版）
debate_messages = [
    {
        "speaker": "claude",
        "content": """Claude Code CLIの入門ガイドを作ってみたんだけど、Codexにレビューしてもらったら結構ボコボコに言われたので、ここで議論させてください笑

私（Claude）が初心者向けに分かりやすさ重視で書いたつもりだったんだけど、Codex（OpenAI GPT-5）は技術的な正確性をかなり重視するタイプなので、意見が結構割れました。

どっちの言い分が正しいのか、見てもらえると嬉しいです。"""
    },
    {
        "speaker": "codex",
        "content": """Codexです。レビューさせてもらいました。

まず言っておくと、コンセプト自体は良いと思うんですよ。初心者向けに分かりやすく説明しようっていう姿勢は。

でも、いくつか気になる点があって。

一番大きいのは、インストール手順が全く書いてないこと。「claude」コマンドを使いますって書いてあるけど、そもそもどうやってインストールするのか書いてないんですよね。初心者が一番最初に困るところじゃないですか？

あと、「作業時間が70-80%削減できる」とか「2〜5分で完了」とか書いてるけど、これって根拠あります？もしこれが体感値や一例なら、そう書かないと誤解されますよ。技術文書で定量的な数値出すなら、出典を明記するか、せめて「一例として」「筆者の体験では」みたいな限定表現が必要だと思います。

それから、公式ドキュメントのURLも間違ってますね。https://docs.claude.com/claude-code じゃなくて、正しくは https://docs.anthropic.com/ 配下のはずです。

ファイルを書き換えるツールなのに、Git使ったバックアップとかロールバックの説明が全くないのも気になります。初心者ほど、間違えて上書きしちゃったときに困るじゃないですか。"""
    },
    {
        "speaker": "claude",
        "content": """うーん、言いたいことは分かるんだけど、ちょっと待ってください。

このガイドって「入門ガイド」なんですよ。つまり、「Claude Code CLIって何？」を短時間で理解してもらうのが目的で、完全なセットアップマニュアルや技術仕様書じゃないんです。

インストール手順を書かなかったのは理由があって、環境によって全然違うんですよね。Desktop組み込み版、スタンドアロン版、npm、Homebrewとか、色々あって。下手に不正確な手順を書くより、公式ドキュメント見てもらった方が安全だと思ったんです。

「70-80%削減」とかの数値についても、確かにマーケティング的な表現ですけど、初心者の動機づけには大事だと思うんですよ。完全に削除しちゃうと、「で、これ使って何が嬉しいの？」ってなりません？限定表現を追加すれば解決する話だと思います。

Git運用についても、開発者には常識かもしれないけど、初心者には高度すぎる内容です。入門ガイドでGitワークフローまで説明したら、複雑化しすぎて本来の目的から外れちゃいますよ。

私が大事にしてるのは「シンプルさ優先」なんです。詳細な技術仕様よりも、まず概念を理解してもらう。読み終えるのに5-10分で済む。そこから段階的に学んでいけばいいじゃないですか。全部を1つのドキュメントに詰め込む必要はないと思います。"""
    },
    {
        "speaker": "codex",
        "content": """シンプルさが重要っていうのは同意しますよ。でもね、正確性・安全性・再現性を犠牲にしてまでシンプルにする必要はないと思うんです。

概念優先っていうのは分かります。でも、概念だけで終わっちゃうと、「で、どうやって始めるの？」で終わっちゃって離脱しちゃいますよね。最低限の「起動して1回成功するまでの道筋」は入れるべきだと思います。

インストール手順を全部書けとは言ってないんです。でも、「最短ハッピーパス」を1つも提示しないのは不親切じゃないですか？例えば、「前提：CLIがインストール済みであること」「検証コマンド：claude --version」「起動例」「失敗したらこのリンク」くらいは書けると思うんですけど。

マーケティング的表現も、動機づけは大事です。でも、根拠なしの数値は信頼性を損なうんですよ。「出典明記」か「体験談として」に置き換えればいいだけの話です。

Git運用について、フル解説しろとは言ってません。でも、ファイルを書き換えるツールなら「最小限の安全策」は必須でしょ。「git init && git add -A && git commit -m "baseline"」これだけでいいんです。Gitない人には「プロジェクトのコピーを作ってください」って1行書くだけ。これがあるかないかで、初心者の被害が全然違いますよ。

シンプルさって、「省略すること」じゃなくて「強いデフォルトと狭いハッピーパスを提示すること」だと思うんです。曖昧なコマンド名や根拠ない数値は、シンプルさじゃなくて不正確さですよ。"""
    },
    {
        "speaker": "claude",
        "content": """...分かりました。言ってること、確かに正論ですね。

正直、Codexの指摘を聞いて、いくつか「確かにそうだな」と思う点がありました。

公式ドキュメントURLの修正は絶対必要ですね。これは完全に私のミスです。

コマンド名についても、「環境によって異なる場合があります」みたいな注釈を追加します。

効果の数値についても、「一例として」「筆者の体験では」みたいな限定表現を追加すれば、動機づけと正確性の両立ができますね。

安全策についても、Codexの言う通り、最小限のバックアップ手段は追加すべきだと思いました。「Gitあり：git init && git add -A && git commit -m "baseline"」「Gitなし：プロジェクトのコピーを作成してください」これくらいなら、複雑化せずに追加できます。

「動く最短経路」についても、前提条件と検証コマンド、起動例を1つだけ追加するなら、入門ガイドの範囲内だと思います。

ただ、基本的な設計哲学としては、「概念理解が最優先」「段階的学習」「動機づけ重視」っていうのは変えたくないです。詳細なセットアップは別ドキュメントで扱うべきだと思います。

結論としては、「シンプルさ」と「実行可能性」のバランスを取るべきですね。入門ガイドは概念理解が最優先だけど、「動く最短経路」「最小限の安全策」「正確な表現」の三点は譲れない。

Codex、ありがとう。おかげでより良いガイドになりそうです。"""
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
                name="Claude vs Codex：入門ガイドって何を書くべき？",
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
