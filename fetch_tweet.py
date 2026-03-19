"""
抓取单条 X/Twitter 推文完整内容
使用 FxTwitter API 和 VxTwitter API（免费，无需 API key）

用法:
    python fetch_tweet.py <tweet_url_or_id> [--md] [--save] [--translate]

示例:
    python fetch_tweet.py https://x.com/trq212/status/2033949937936085378
    python fetch_tweet.py 2033949937936085378 --md
    python fetch_tweet.py 2033949937936085378 --md --translate
    python fetch_tweet.py 2033949937936085378 --md -o article.md --translate
"""

import sys
import io
import os

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import re
import urllib.request
import urllib.error


def _load_env():
    """从脚本同目录加载 .env"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def translate_markdown(md_content: str) -> str:
    """使用 OpenRouter API 将 Markdown 内容翻译为中文"""
    _load_env()
    api_key = os.environ.get("openrouter_api_key")
    model = os.environ.get("model", "openai/gpt-4o-mini")
    if not api_key:
        raise ValueError("未找到 openrouter_api_key，请在 .env 中配置")

    # 若 .env 中模型名不包含 /，补全为 openai/ 前缀
    if model and "/" not in model:
        model = f"openai/{model}"
    # 区域限制时可尝试: anthropic/claude-3-haiku, google/gemini-2.0-flash-exp

    prompt_template = """You are a professional {{to}} native translator who needs to fluently translate text into {{to}}.

## Translation Rules
1. Output only the translated content. No explanations, no "Here's the translation:", no markdown code block wrappers (```).
2. Maintain exactly the same structure: paragraphs, headers (# ##), lists (-), line breaks. Preserve Markdown syntax - only translate text content.
3. Do NOT translate: URLs, file paths, code, commands, placeholders like <service> or <framework>, product names (Claude Code, Skills, Slack, GitHub).
4. For technical terms use common {{to}} equivalents when they exist (e.g. Runbook, Gotchas, standup, PR). Otherwise keep English.
5. If input contains %%, use %% in output; if not, do not use %%.
6. Keep link URLs unchanged: [text](url) - only translate "text", never modify "url".

Translate the following Markdown into {{to}}:

"""
    to_lang = os.environ.get("translate_to", "Chinese")
    prompt = prompt_template.replace("{{to}}", to_lang)
    if to_lang.lower() in ("chinese", "中文", "简体中文"):
        prompt += "\n[术语参考：Runbook→运维手册, Gotchas→坑点, standup→站会, PR→拉取请求]\n\n"
    prompt += md_content
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        err_msg = f"HTTP {e.code}: {e.reason}"
        try:
            err_json = json.loads(body)
            err_msg = err_json.get("error", {}).get("message", err_msg)
        except Exception:
            pass
        raise RuntimeError(f"OpenRouter API 调用失败: {err_msg}\n提示: 请检查 .env 中 model 是否为有效模型，如 openai/gpt-4o-mini")
    choices = resp_data.get("choices", [])
    if not choices:
        raise RuntimeError(resp_data.get("error", {}).get("message", "API 返回为空"))
    return choices[0].get("message", {}).get("content", "").strip()


def extract_tweet_info(url_or_id: str) -> tuple[str, str]:
    """从 URL 或纯 ID 中提取 screen_name 和 tweet_id"""
    # 纯数字 ID
    if url_or_id.strip().isdigit():
        return "_", url_or_id.strip()
    
    # URL 格式: https://x.com/user/status/123456 或 https://twitter.com/user/status/123456
    match = re.search(r"(?:x\.com|twitter\.com)/(\w+)/status/(\d+)", url_or_id)
    if match:
        return match.group(1), match.group(2)
    
    raise ValueError(f"无法解析: {url_or_id}")


def fetch_fxtwitter(screen_name: str, tweet_id: str) -> dict | None:
    """通过 FxTwitter API 获取推文"""
    url = f"https://api.fxtwitter.com/{screen_name}/status/{tweet_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "TweetFetcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[FxTwitter] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[FxTwitter] Error: {e}")
        return None


def fetch_vxtwitter(screen_name: str, tweet_id: str) -> dict | None:
    """通过 VxTwitter API 获取推文"""
    url = f"https://api.vxtwitter.com/{screen_name}/status/{tweet_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "TweetFetcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[VxTwitter] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[VxTwitter] Error: {e}")
        return None


def fetch_syndication(tweet_id: str) -> dict | None:
    """通过 Twitter Syndication API（react-tweet 方案）获取推文"""
    import math
    token = str(math.pi * (int(tweet_id) / 1e15))
    # 转为 base 36
    token = format(int(float(token) * 1e10), 'x')[:12]
    
    url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token={token}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[Syndication] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[Syndication] Error: {e}")
        return None


def _build_article_media_map(article: dict) -> dict:
    """构建 entity_key -> 图片URL 的映射（用于 Article 内嵌图片）"""
    entity_map = article.get("content", {}).get("entityMap", [])
    media_entities = article.get("media_entities", [])
    # media_entities: [{media_id, original_img_url}, ...]
    mid_to_url = {m.get("media_id"): m.get("media_info", {}).get("original_img_url", "")
                  for m in media_entities if m.get("media_id")}
    # entityMap 是 list，每项 {key, value: {type, data: {mediaItems: [{mediaId}]}}}
    key_to_url = {}
    for ent in entity_map:
        if not isinstance(ent, dict):
            continue
        key = str(ent.get("key", ""))
        val = ent.get("value", {})
        if val.get("type") != "MEDIA":
            continue
        items = val.get("data", {}).get("mediaItems", [])
        if items and items[0].get("mediaId"):
            mid = str(items[0]["mediaId"])
            key_to_url[key] = mid_to_url.get(mid, "")
    return key_to_url


def _build_article_entity_map(article: dict) -> dict:
    """构建 entity_key -> entity 的映射（用于 Article 内嵌 MARKDOWN 代码块等）"""
    entity_list = article.get("content", {}).get("entityMap", [])
    result = {}
    for ent in entity_list:
        if not isinstance(ent, dict):
            continue
        key = str(ent.get("key", ""))
        val = ent.get("value", {})
        if key:
            result[key] = val
    return result


def _extract_fxtwitter_text(tweet: dict, as_markdown: bool = False) -> str:
    """从 FxTwitter 的 tweet 对象中提取完整文本（含 Article 长文、图片占位）"""
    text = tweet.get("text", "").strip()
    if text:
        return text
    # Article 类型：内容在 article.content.blocks 中
    article = tweet.get("article", {})
    blocks = article.get("content", {}).get("blocks", [])
    if blocks:
        media_map = _build_article_media_map(article)
        entity_map = _build_article_entity_map(article)
        parts = []
        for b in blocks:
            block_type = b.get("type", "")
            t = b.get("text", "").strip()
            # atomic 类型：可能是内嵌图片(MEDIA)或代码块(MARKDOWN)，通过 entityRanges 关联
            if block_type == "atomic":
                entity_ranges = b.get("entityRanges", [])
                resolved = False
                for er in entity_ranges:
                    k = str(er.get("key", ""))
                    ent = entity_map.get(k, {})
                    ent_type = ent.get("type", "")
                    if ent_type == "MARKDOWN":
                        md_content = ent.get("data", {}).get("markdown", "").strip()
                        if md_content:
                            parts.append(f"\n{md_content}\n")
                            resolved = True
                            break
                    elif ent_type == "MEDIA":
                        img_url = media_map.get(k, "")
                        if as_markdown and img_url:
                            parts.append(f"\n![图片]({img_url})\n")
                        else:
                            parts.append(f"\n[图片] {img_url}\n" if img_url else "\n[图片]\n")
                        resolved = True
                        break
                if not resolved:
                    parts.append("\n[图片]\n")
            elif t:
                if block_type == "header-one":
                    parts.append(f"\n# {t}\n")
                elif block_type == "header-two":
                    parts.append(f"\n## {t}\n")
                elif block_type in ("unordered-list-item", "ordered-list-item"):
                    parts.append(f"- {t}\n")
                else:
                    parts.append(t + "\n")
        return "".join(parts).strip() if parts else ""
    # 仅链接时用 raw_text
    raw = tweet.get("raw_text", {})
    raw_text = raw.get("text", "").strip() if isinstance(raw, dict) else ""
    return raw_text or "(无内容)"


def display_tweet(data: dict, source: str):
    """格式化显示推文内容"""
    print(f"\n{'='*60}")
    print(f"数据来源: {source}")
    print(f"{'='*60}")
    
    if source == "FxTwitter":
        tweet = data.get("tweet", {})
        print(f"作者: {tweet.get('author', {}).get('name', '?')} (@{tweet.get('author', {}).get('screen_name', '?')})")
        print(f"时间: {tweet.get('created_at', '?')}")
        print(f"点赞: {tweet.get('likes', '?')} | 转发: {tweet.get('retweets', '?')} | 回复: {tweet.get('replies', '?')} | 浏览: {tweet.get('views', '?')}")
        article = tweet.get("article", {})
        if article:
            print(f"类型: Article | 标题: {article.get('title', '?')}")
        print(f"\n--- 推文内容 ---\n")
        print(_extract_fxtwitter_text(tweet))
    
    elif source == "VxTwitter":
        print(f"作者: {data.get('user_name', '?')} (@{data.get('user_screen_name', '?')})")
        print(f"时间: {data.get('date', '?')}")
        print(f"点赞: {data.get('likes', '?')} | 转发: {data.get('retweets', '?')} | 回复: {data.get('replies', '?')}")
        print(f"\n--- 推文内容 ---\n")
        print(data.get("text", "(无内容)"))
    
    elif source == "Syndication":
        print(f"作者: {data.get('user', {}).get('name', '?')} (@{data.get('user', {}).get('screen_name', '?')})")
        print(f"时间: {data.get('created_at', '?')}")
        print(f"\n--- 推文内容 ---\n")
        print(data.get("text", "(无内容)"))
    
    print(f"\n{'='*60}")


def save_json(data: dict, tweet_id: str, source: str):
    """保存原始 JSON"""
    filename = f"tweet_{tweet_id}_{source.lower()}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"原始 JSON 已保存至: {filename}")


def to_markdown(data: dict, source: str) -> str:
    """将推文内容转为 Markdown 格式"""
    lines = []
    if source == "FxTwitter":
        tweet = data.get("tweet", {})
        author = tweet.get("author", {})
        name = author.get("name", "?")
        screen_name = author.get("screen_name", "?")
        url = tweet.get("url", "")
        created = tweet.get("created_at", "?")
        likes = tweet.get("likes", "?")
        retweets = tweet.get("retweets", "?")
        replies = tweet.get("replies", "?")
        views = tweet.get("views", "?")
        article = tweet.get("article", {})
        title = article.get("title", "").strip() if article else ""
        if title:
            lines.append(f"# {title}\n")
        lines.append(f"\n**作者:** {name} (@{screen_name})\n")
        lines.append(f"**时间:** {created}\n")
        lines.append(f"**点赞:** {likes} | **转发:** {retweets} | **回复:** {replies} | **浏览:** {views}\n")
        if url:
            lines.append(f"**链接:** {url}\n")
        lines.append("\n---\n\n")
        lines.append(_extract_fxtwitter_text(tweet, as_markdown=True))
    elif source == "VxTwitter":
        lines.append(f"**作者:** {data.get('user_name', '?')} (@{data.get('user_screen_name', '?')})\n")
        lines.append(f"**时间:** {data.get('date', '?')}\n")
        lines.append(f"**点赞:** {data.get('likes', '?')} | **转发:** {data.get('retweets', '?')} | **回复:** {data.get('replies', '?')}\n")
        lines.append("\n---\n\n")
        lines.append(data.get("text", "(无内容)"))
    elif source == "Syndication":
        user = data.get("user", {})
        lines.append(f"**作者:** {user.get('name', '?')} (@{user.get('screen_name', '?')})\n")
        lines.append(f"**时间:** {data.get('created_at', '?')}\n")
        lines.append("\n---\n\n")
        lines.append(data.get("text", "(无内容)"))
    return "".join(lines)


def save_markdown(data: dict, source: str, tweet_id: str, filename: str | None = None) -> str:
    """保存为 Markdown 文件，返回保存路径"""
    if not filename:
        tweet = data.get("tweet", {}) if source == "FxTwitter" else {}
        article = tweet.get("article", {})
        title = article.get("title", "").strip() if article else ""
        if title:
            safe = re.sub(r'[<>:"/\\|?*]', "_", title)[:80]
            filename = f"{safe}_{tweet_id}.md"
        else:
            filename = f"tweet_{tweet_id}.md"
    md = to_markdown(data, source)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    return filename


def translate_and_save(md_path: str) -> str:
    """将 Markdown 文件翻译为中文并保存，返回中文文件路径"""
    with open(md_path, encoding="utf-8") as f:
        content = f.read()
    print("正在调用 API 翻译为中文...")
    translated = translate_markdown(content)
    base, ext = os.path.splitext(md_path)
    zh_path = f"{base}_zh{ext}"
    with open(zh_path, "w", encoding="utf-8") as f:
        f.write(translated)
    return zh_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    args = sys.argv[1:]
    input_str = args[0]
    save_raw = "--save" in args
    save_md = "--md" in args
    do_translate = "--translate" in args
    out_file = None
    if "-o" in args:
        i = args.index("-o")
        if i + 1 < len(args):
            out_file = args[i + 1]
    
    try:
        screen_name, tweet_id = extract_tweet_info(input_str)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"正在获取推文: {tweet_id} (用户: {screen_name})")
    
    def on_success(data: dict, source: str):
        if not save_md:
            display_tweet(data, source)
        if save_md:
            path = save_markdown(data, source, tweet_id, out_file)
            print(f"\nMarkdown 已保存至: {path}")
            if do_translate:
                try:
                    zh_path = translate_and_save(path)
                    print(f"中文版已保存至: {zh_path}")
                except Exception as e:
                    print(f"翻译失败: {e}")
            if not save_raw:
                return
        if save_raw:
            save_json(data, tweet_id, source)
    
    # 尝试 FxTwitter
    print("\n[1/3] 尝试 FxTwitter API...")
    data = fetch_fxtwitter(screen_name, tweet_id)
    if data and data.get("code") == 200:
        on_success(data, "FxTwitter")
        return
    
    # 尝试 VxTwitter
    print("\n[2/3] 尝试 VxTwitter API...")
    data = fetch_vxtwitter(screen_name, tweet_id)
    if data and data.get("text"):
        on_success(data, "VxTwitter")
        return
    
    # 尝试 Syndication
    print("\n[3/3] 尝试 Twitter Syndication API...")
    data = fetch_syndication(tweet_id)
    if data and data.get("text"):
        on_success(data, "Syndication")
        return
    
    print("\n所有 API 均未能获取到推文内容。可能原因：")
    print("- 推文已被删除或设为私密")
    print("- API 服务暂时不可用")
    print("- 网络连接问题")


if __name__ == "__main__":
    main()