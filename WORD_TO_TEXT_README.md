# 📝 Word→テキスト一括変換ツール

WindowsのPowerShellでWord文書を一括でプレーンテキストに変換するツールです。

## 🚀 使い方（Windows PowerShell）

### 1. Pythonのインストール確認

```powershell
python --version
```

Python 3.6以上が必要です。インストールされていない場合は[python.org](https://www.python.org/downloads/)からダウンロードしてください。

### 2. 必要なライブラリをインストール

```powershell
pip install python-docx
```

### 3. スクリプトをダウンロード

このスクリプト（`word_to_text.py`）をWindowsに転送してください。

**Tailscale経由でMacから転送する方法:**

```powershell
# MacのIPアドレスを確認（Macで実行）
# 100.102.220.16

# WindowsでSCP転送
scp ユーザー名@100.102.220.16:/Users/minamitakeshi/discord-mcp-server/word_to_text.py C:\Users\ユーザー名\Downloads\
```

### 4. スクリプトを実行

```powershell
# カレントフォルダ内の全.docxファイルを変換
python word_to_text.py .

# 特定のフォルダを指定
python word_to_text.py C:\Users\Documents\WordFiles

# サブフォルダも含めて変換
python word_to_text.py C:\Users\Documents
```

## 📊 実行例

```powershell
PS C:\Users\Documents> python word_to_text.py .

📁 検索中: C:\Users\Documents

📄 3個のWordファイルが見つかりました

[1/3] 報告書.docx ... ✅ 完了
[2/3] 議事録.docx ... ✅ 完了
[3/3] 企画書.docx ... ✅ 完了

==================================================
✅ 成功: 3件
==================================================
```

## 📁 出力形式

元のWordファイルと同じフォルダに、同じファイル名で`.txt`拡張子のファイルが作成されます。

**例:**
```
報告書.docx  →  報告書.txt
議事録.docx  →  議事録.txt
```

## ⚙️ 仕様

- **対応形式**: `.docx`（Word 2007以降）
- **検索**: サブフォルダも再帰的に検索
- **抽出内容**:
  - 本文の全段落
  - 表（テーブル）内のテキスト
- **エンコーディング**: UTF-8
- **一時ファイル**: `~$`で始まるファイルは除外

## 🔧 トラブルシューティング

### python-docxがインストールできない

```powershell
# pipをアップグレード
python -m pip install --upgrade pip

# 再度インストール
pip install python-docx
```

### 古い.docファイル（Word 2003以前）を変換したい

古い`.doc`形式は`python-docx`では対応していません。Wordで一度`.docx`に変換してから使用してください。

**Word一括変換（PowerShell）:**
```powershell
# Word経由で.docを.docxに一括変換（Wordがインストールされている場合）
$word = New-Object -ComObject Word.Application
$word.Visible = $false

Get-ChildItem -Path . -Filter *.doc | ForEach-Object {
    $doc = $word.Documents.Open($_.FullName)
    $docx = $_.FullName -replace '\.doc$', '.docx'
    $doc.SaveAs([ref]$docx, [ref]16)  # 16 = wdFormatXMLDocument
    $doc.Close()
}

$word.Quit()
```

## 📞 サポート

問題が発生した場合は、エラーメッセージをコピーしてClaudeに相談してください。

---

**最終更新**: 2025-11-17
