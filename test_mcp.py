import subprocess
import json
import time

# FastMCPサーバーを起動
proc = subprocess.Popen(
    ['.venv/bin/fastmcp', 'run', 'server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# initializeリクエストを送信
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}

proc.stdin.write(json.dumps(init_request) + '\n')
proc.stdin.flush()

# レスポンスを読む
time.sleep(2)
output = proc.stdout.readline()
print("Initialize response:", output.strip())

# tools/listリクエストを送信
tools_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

proc.stdin.write(json.dumps(tools_request) + '\n')
proc.stdin.flush()

# レスポンスを読む
time.sleep(2)
output = proc.stdout.readline()
print("Tools list response:", output.strip()[:500])

# プロセスを終了
proc.terminate()
proc.wait()
