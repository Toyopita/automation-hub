---
marp: true
theme: uncover
paginate: true
style: |
  section {
    font-family: 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif;
    font-size: 28px;
    padding: 60px;
  }
  h1 {
    font-size: 64px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 30px;
    line-height: 1.2;
  }
  h2 {
    font-size: 48px;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 25px;
    line-height: 1.3;
  }
  h3 {
    font-size: 36px;
    color: #34495e;
    margin-bottom: 20px;
  }
  p {
    font-size: 24px;
    line-height: 1.6;
    margin-bottom: 20px;
  }
  ul, ol {
    font-size: 24px;
    line-height: 1.8;
  }
  code {
    background: #f8f9fa;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 22px;
  }
  strong {
    color: #e74c3c;
    font-weight: 700;
  }
  table {
    font-size: 20px;
  }
  img[alt~="center"] {
    display: block;
    margin: 0 auto;
  }
---

<!-- _class: lead -->
<!-- _paginate: false -->

![bg brightness:0.4](https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1600)

# 📊 **Marp**

**Markdownから生まれる**
**プロフェッショナルスライド**

---

<!-- _class: lead -->

# 🤔 なぜMarp？

PowerPointはもう古い

---

![bg right:40%](https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800)

## **エンジニアの課題**

- コードの挿入が面倒
- Gitで管理できない
- デザイン調整に時間がかかる
- チーム共同編集が困難

**Marpが全て解決**

---

<!-- _class: lead -->
<!-- _backgroundColor: #3498db -->
<!-- _color: white -->

# ✨ Marpの魔法

---

![bg left:45%](https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=800)

## **3つの強み**

### 📝 Markdownで書く
テキストエディタで完結

### 🎨 美しいデザイン
テーマ選択 + CSS自由

### 🚀 即座に共有
HTML / PDF / PPTX

---

## **比較表**

|  | **Marp** | **PowerPoint** |
|:---:|:---:|:---:|
| 編集 | テキスト | GUI |
| Git管理 | ✅ | ❌ |
| 軽量性 | ✅ | ❌ |
| 共同編集 | ✅ | △ |
| 価格 | 🆓 無料 | 💰 有料 |

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600)

# 🚀 始め方

---

![bg right:35%](https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800)

## **3つの方法**

### 1️⃣ Web版
https://web.marp.app
**インストール不要**

### 2️⃣ VS Code
拡張機能で快適編集

### 3️⃣ CLI
自動化・CI/CD対応

---

## **CLI インストール**

```bash
npm install -g @marp-team/marp-cli
```

```bash
# HTML生成
marp slide.md -o slide.html

# PDF生成
marp slide.md --pdf

# PowerPoint生成
marp slide.md --pptx
```

---

<!-- _class: lead -->
<!-- _backgroundColor: #2ecc71 -->
<!-- _color: white -->

# ✍️ 書き方

---

## **基本構文**

```markdown
---
marp: true
theme: uncover
---

# タイトル

内容

---

## 次のスライド

- 箇条書き1
- 箇条書き2
```

**`---` でスライド区切り**

---

![bg left:40%](https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=800)

## **コードも美しく**

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

シンタックスハイライト自動

---

## **画像の配置**

### サイズ指定

```markdown
![width:500px](image.png)
```

### 背景画像

```markdown
![bg](background.jpg)
![bg right:40%](side.jpg)
```

### センター配置

```markdown
![center width:600px](diagram.png)
```

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1600)

# 🎨 デザイン

---

## **3つのテーマ**

### **default**
シンプル・万能

### **gaia**
モダン・洗練

### **uncover** ← いま使用中
プレゼン向け・インパクト大

---

![bg right:45%](https://images.unsplash.com/photo-1561998338-13ad7883b20f?w=800)

## **背景色変更**

```markdown
<!-- _backgroundColor: #3498db -->
<!-- _color: white -->

# 青背景スライド
```

**スライドごとに自由自在**

---

## **カスタムCSS**

```markdown
<style>
section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
h1 {
  color: white;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
</style>
```

**完全にカスタマイズ可能**

---

<!-- _class: lead -->
<!-- _backgroundColor: #e74c3c -->
<!-- _color: white -->

# 🧮 数式対応

---

## **KaTeX サポート**

インライン: $E = mc^2$

ブロック数式:
$$
\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$

**LaTeXと同じ記法**

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1600)

# 💼 実用例

---

![bg left:40%](https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800)

## **技術勉強会**

- コード例豊富
- GitHubで公開
- チーム共有簡単

**エンジニアに最適**

---

![bg right:40%](https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800)

## **社内プレゼン**

- テンプレート化
- バージョン管理
- 効率的な更新

**生産性UP**

---

![bg left:40%](https://images.unsplash.com/photo-1532619675605-1ede6c2ed2b0?w=800)

## **学術発表**

- 数式・図表美しく
- 論文からそのまま
- LaTeXライク

**研究者向け**

---

<!-- _class: lead -->

# 🛠️ ワークフロー

---

## **実際の流れ**

### 1. 📝 VS Codeで編集
リアルタイムプレビュー

### 2. 🔄 Gitでバージョン管理
変更履歴を記録

### 3. 🤖 CI/CDで自動ビルド
GitHub Actions連携

### 4. 📤 共有
HTML公開 or PDF配布

---

![bg right:50%](https://images.unsplash.com/photo-1556761175-b413da4baf72?w=800)

## **GitHub連携**

```yaml
# .github/workflows/marp.yml
name: Marp Build
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: npm install -g @marp-team/marp-cli
      - run: marp slide.md --pdf
```

**自動PDF生成**

---

<!-- _class: lead -->
<!-- _backgroundColor: #9b59b6 -->
<!-- _color: white -->

# ⚡ Tips

---

## **便利な機能**

### ページ番号

```markdown
---
paginate: true
---
```

### フッター

```markdown
---
footer: '© 2025 Your Company'
---
```

### スピーカーノート

```markdown
<!-- これは表示されないメモ -->
```

---

![bg left:40%](https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?w=800)

## **エクスポート詳細**

### HTML
ブラウザで表示
→ Webサイトに埋め込み

### PDF
印刷・配布用
→ 高品質出力

### PPTX
PowerPointで最終調整
→ 互換性確保

---

<!-- _class: lead -->

# 📚 リソース

---

## **学習サイト**

### 🌐 公式サイト
https://marp.app

### 📘 ドキュメント
https://marpit.marp.app

### 💻 VS Code拡張
https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode

### 🐙 GitHub
https://github.com/marp-team/marp

---

<!-- _class: lead -->

![bg](https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=1600)

# 🎯 まとめ

---

![bg right:45%](https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=800)

## **Marpの価値**

✅ **効率的**
Markdown → 即スライド

✅ **管理しやすい**
Git完全対応

✅ **柔軟**
デザイン自由自在

✅ **無料**
オープンソース

---

<!-- _class: lead -->
<!-- _backgroundColor: #1a1a1a -->
<!-- _color: white -->

# 🎓 誰におすすめ？

---

![bg left:40%](https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=800)

## ✅ **向いている人**

- エンジニア
- 研究者
- ドキュメント管理好き
- 効率重視
- Git愛用者

---

![bg right:40%](https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=800)

## ❌ **向いていない人**

- GUIが好き
- PowerPoint愛用者
- アニメーション多用
- デザイン凝りたい
- CLI苦手

---

<!-- _class: lead -->
<!-- _paginate: false -->

![bg brightness:0.3](https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1600)

# 🎉 今すぐ始めよう！

```bash
npm install -g @marp-team/marp-cli
marp --version
```

**Markdownでスライド革命を**

---

<!-- _class: lead -->
<!-- _backgroundColor: #2c3e50 -->
<!-- _color: white -->
<!-- _paginate: false -->

# ありがとうございました

**Happy Presenting! 🚀**

---
