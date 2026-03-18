# XArticle-markdown

将 X/Twitter 推文抓取并转换为 Markdown，支持可选翻译为中文。


<p align="center">
  <img src="image/image.png" alt="XArticle-markdown 示例截图" width="600">
</p>



## 功能

- **命令行工具**：`fetch_tweet.py` 通过 FxTwitter/VxTwitter API 抓取推文（免费，无需 Twitter API key）
- **Chrome 扩展**：书签推文时自动下载 Markdown，或手动粘贴链接一键下载
- **可选翻译**：通过 OpenRouter API 将内容翻译为中文

## 快速开始

### 命令行

```bash
# 抓取推文并输出 Markdown
python fetch_tweet.py https://x.com/username/status/1234567890

# 输出到文件并翻译
python fetch_tweet.py 1234567890 --md --translate -o article.md
```

### Chrome 扩展

1. 打开 `chrome://extensions/`，开启「开发者模式」
2. 点击「加载已解压的扩展程序」，选择 `extension` 文件夹
3. 使用：在 X/Twitter 收藏推文（Ctrl+D）时自动下载，或点击扩展图标手动下载

> [!NOTE]
> 翻译功能需配置 OpenRouter API Key。命令行在项目根目录创建 `.env`；扩展在弹窗底部「设置」中配置。

## 配置（翻译）

创建 `.env` 文件（命令行）或通过扩展设置填写：

```
openrouter_api_key=sk-or-v1-xxx
model=openai/gpt-4o-mini
translate_to=Chinese
```

## 项目结构

```
xArticle-markdown/
├── fetch_tweet.py    # 命令行抓取工具
├── extension/        # Chrome 扩展
│   ├── manifest.json
│   ├── popup.html
│   ├── background.js
│   └── icons/
└── .env              # API 配置（不提交到 Git）
```

## 依赖

- Python 3.x（标准库，无需额外安装）
- Chrome / Edge（扩展）

