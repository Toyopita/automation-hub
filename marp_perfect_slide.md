---
marp: true
theme: gaia
paginate: true
backgroundColor: #fff
style: |
  section {
    font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
  }
  h1 {
    color: #2c3e50;
    border-bottom: 4px solid #3498db;
    padding-bottom: 10px;
  }
  h2 {
    color: #34495e;
    border-left: 5px solid #3498db;
    padding-left: 15px;
  }
  code {
    background: #f8f9fa;
    padding: 2px 8px;
    border-radius: 4px;
  }
  strong {
    color: #e74c3c;
  }
---

<!-- _class: lead -->
# 📊 Marp完全ガイド

**Markdownで作る、プロフェッショナルなスライド**

---

<!-- _backgroundColor: #ecf0f1 -->

## 🤔 Marpって何？

**Markdown Presentation Ecosystem**の略

普段使っているMarkdownで、美しいスライドが作れるツール

- 📝 テキストエディタで編集
- 🎨 テーマ・CSS自由自在
- 📤 HTML/PDF/PPTXで書き出し
- 🆓 完全無料・オープンソース

---

## 🎯 誰のためのツール？

### ✅ こんな人にピッタリ

- **エンジニア** → コードを含むプレゼンが多い
- **研究者** → 数式や図表を綺麗に見せたい
- **ドキュメント管理好き** → Gitで管理したい
- **効率重視** → GUIより速く作りたい

### ❌ 向いていない人

- PowerPointのアニメーションが必須
- マウスでポチポチ編集したい

---

<!-- _backgroundColor: #fff5e1 -->

## 🆚 PowerPointとの違い

| 項目 | Marp | PowerPoint |
|------|------|-----------|
| 編集方法 | テキスト | GUI |
| バージョン管理 | ✅ Git対応 | ❌ 差分管理が困難 |
| 共同編集 | ✅ GitHub | △ OneDrive必須 |
| 軽さ | ✅ 超軽量 | ❌ 重い |
| デザイン自由度 | △ CSS必要 | ✅ 直感的 |
| 価格 | 🆓 無料 | 💰 Microsoft 365 |

---

## 🚀 始め方（3つの選択肢）

### 1️⃣ **Web版**（一番簡単）
https://web.marp.app/
- インストール不要
- ブラウザだけでOK
- オフラインでも動作

### 2️⃣ **VS Code拡張機能**（おすすめ）
- リアルタイムプレビュー
- 最も多機能

### 3️⃣ **Marp CLI**（自動化向け）
```bash
npm install -g @marp-team/marp-cli
```

---

<!-- _backgroundColor: #e8f5e9 -->

## ✍️ 基本的な書き方

```markdown
---
marp: true
theme: gaia
---

# タイトルスライド

これが最初のスライドです

---

## 次のスライド

- 箇条書き1
- 箇条書き2

---

## コードも書ける

\```python
def hello():
    print("Hello, Marp!")
\```
```

**たったこれだけ！**

---

## 🎨 テーマの選択

### 組み込みテーマ3種類

1. **default** - シンプル・万能
2. **gaia** - モダン・洗練（このスライドで使用中）
3. **uncover** - プレゼン向け・インパクト大

```markdown
---
marp: true
theme: gaia
---
```

カスタムCSSも自由に追加可能！

---

<!-- _backgroundColor: #fce4ec -->

## 🖼️ 画像の挿入

### サイズ指定

```markdown
![width:500px](image.png)
```

### 背景画像

```markdown
![bg](background.jpg)
```

### 複数画像を並べる

```markdown
![width:300px](img1.png) ![width:300px](img2.png)
```

---

## 📊 表・リスト・コード

### 表
| 項目 | 内容 |
|------|------|
| Markdown | 対応 |
| 数式 | KaTeX |

### リスト
- 箇条書き
  - ネスト可能

### コード
```javascript
const marp = require('@marp-team/marp-core');
```

---

<!-- _backgroundColor: #e3f2fd -->

## 🧮 数式も書ける（KaTeX）

インライン数式: $E = mc^2$

ブロック数式:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

```markdown
インライン: $E = mc^2$

ブロック:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$
```

---

## 📤 エクスポート方法

### 1. **HTML形式**
```bash
marp slide.md -o slide.html
```
→ ブラウザで表示・共有

### 2. **PDF形式**
```bash
marp slide.md --pdf
```
→ 印刷・配布用

### 3. **PowerPoint形式**
```bash
marp slide.md --pptx
```
→ PowerPointで最終調整も可能

---

<!-- _backgroundColor: #fff3e0 -->

## 🎛️ カスタマイズ例

### 背景色を変更

```markdown
<!-- backgroundColor: #f0f8ff -->
```

### ページごとにスタイル

```markdown
<!-- _class: lead -->
# センター揃えの大きな文字
```

### カスタムCSS

```markdown
<style>
h1 { color: #e74c3c; }
</style>
```

---

## 💡 実用的な使い方

### 1. **技術勉強会**
- コード例を豊富に含むスライド
- GitHubで公開・共有

### 2. **社内報告**
- テンプレート化して効率化
- チームで共同編集

### 3. **論文発表**
- 数式・図表を美しく表示
- LaTeXライクな体験

---

<!-- _backgroundColor: #f3e5f5 -->

## 🛠️ 実際のワークフロー

1. **VS Codeで編集**
   - リアルタイムプレビューで確認

2. **Gitでバージョン管理**
   ```bash
   git add slide.md
   git commit -m "Update slide"
   ```

3. **自動ビルド（CI/CD）**
   - GitHub Actionsで自動PDF生成

4. **共有**
   - HTML版をWeb公開、またはPDF配布

---

## ⚡ Tips & Tricks

### スピーカーノート
```markdown
<!--
これは表示されないメモ
-->
```

### ページ番号を表示
```yaml
---
paginate: true
---
```

### フッター
```yaml
---
footer: '© 2025 Your Name'
---
```

---

<!-- _backgroundColor: #e8f5e9 -->

## 🎓 学習リソース

### 公式サイト
https://marp.app/

### VS Code拡張機能
https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode

### GitHub
https://github.com/marp-team/marp

### サンプル集
https://github.com/marp-team/marp-core/tree/main/themes

---

## 🏁 まとめ

### Marpの魅力

✅ **効率的** - Markdownで高速作成
✅ **管理しやすい** - Gitでバージョン管理
✅ **柔軟** - CSS・HTMLで自由自在
✅ **無料** - オープンソース

### 始めるなら今！

```bash
# VS Codeで拡張機能をインストール
# または
npm install -g @marp-team/marp-cli
```

---

<!-- _class: lead -->
<!-- _backgroundColor: #2c3e50 -->
<!-- _color: #fff -->

# 🎉 ありがとうございました！

**さあ、Marpでスライドを作ろう！**

📧 お問い合わせ: example@example.com
🐙 GitHub: @yourusername
