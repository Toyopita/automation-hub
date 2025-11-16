import os
import requests
from dotenv import load_dotenv

load_dotenv()
notion_token = os.getenv("NOTION_TOKEN_TASK")
NOTION_PROJECT_DB_ID = "1c800160-1818-8004-9609-c1250a7e3478"

headers = {
    'Authorization': f'Bearer {notion_token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

payload = {
    "page_size": 100
}

response = requests.post(
    f'https://api.notion.com/v1/databases/{NOTION_PROJECT_DB_ID}/query',
    headers=headers,
    json=payload
)

data = response.json()
projects = []
completed_count = 0

for page in data.get('results', []):
    title_prop = page['properties'].get('プロジェクト名', {})
    title_array = title_prop.get('title', [])
    project_name = title_array[0].get('plain_text', '無題') if title_array else '無題'
    
    status_prop = page['properties'].get('進捗', {})
    status = status_prop.get('status', {})
    status_name = status.get('name', '不明')
    
    if status_name == '完了':
        completed_count += 1
    else:
        projects.append({'name': project_name, 'status': status_name})

print(f"全プロジェクト数: {len(data.get('results', []))}件")
print(f"完了プロジェクト: {completed_count}件")
print(f"未完了プロジェクト: {len(projects)}件")
print(f"\n未完了プロジェクト一覧:")
for i, p in enumerate(projects[:20], 1):
    print(f"{i}. {p['name']} (状態: {p['status']})")
