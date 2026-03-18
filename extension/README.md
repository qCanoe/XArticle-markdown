# X/Twitter Article to Markdown - Chrome 扩展

将 `fetch_tweet.py` 的功能封装为 Chrome 扩展：书签推文后自动下载 Markdown，支持可选翻译。

## 功能

- **书签触发**：在 Chrome 中收藏（Bookmark）一条 X/Twitter 推文链接时，自动获取内容并下载为 Markdown 文件
- **手动下载**：点击扩展图标，粘贴或自动识别当前页推文链接，一键下载
- **可选翻译**：勾选后通过 OpenRouter API 将内容翻译为中文（需在选项中配置 API Key）

## 安装

1. 打开 Chrome，进入 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目的 `extension` 文件夹

## 配置（翻译功能）

1. 点击扩展图标 → 底部「设置」
2. 填写 **OpenRouter API Key**（在 [openrouter.ai](https://openrouter.ai/keys) 获取）
3. 可选：修改模型（默认 `openai/gpt-4o-mini`）、翻译目标语言（默认 `Chinese`）
4. 勾选「书签时同时翻译为中文」可在书签时自动翻译

## 使用

- **自动**：在 X/Twitter 打开任意推文 → 按 `Ctrl+D` 或点击地址栏星标收藏 → 扩展会自动下载 Markdown
- **手动**：点击扩展图标 → 输入或自动填充推文链接 → 勾选是否翻译 → 点击「下载 Markdown」

## 图标

若图标显示异常，可打开 `gen_icons.html` 在浏览器中生成并下载 `icon16.png`、`icon48.png`、`icon128.png`，放入 `icons/` 文件夹。
