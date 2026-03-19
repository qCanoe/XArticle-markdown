/**
 * X/Twitter Article to Markdown - Background Service Worker
 * Listens for bookmarks, fetches tweet, downloads markdown.
 */

const TWEET_URL_RE = /(?:x\.com|twitter\.com)\/(\w+)\/status\/(\d+)/;

function extractTweetInfo(url) {
  const match = url.match(TWEET_URL_RE);
  if (match) return { screenName: match[1], tweetId: match[2] };
  return null;
}

function isTweetUrl(url) {
  return TWEET_URL_RE.test(url);
}

async function fetchFxTwitter(screenName, tweetId) {
  const res = await fetch(`https://api.fxtwitter.com/${screenName}/status/${tweetId}`, {
    headers: { "User-Agent": "TweetFetcher/1.0" }
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (data?.code === 200) return { data, source: "FxTwitter" };
  return null;
}

async function fetchVxTwitter(screenName, tweetId) {
  const res = await fetch(`https://api.vxtwitter.com/${screenName}/status/${tweetId}`, {
    headers: { "User-Agent": "TweetFetcher/1.0" }
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (data?.text) return { data, source: "VxTwitter" };
  return null;
}

function syndicationToken(tweetId) {
  let token = String(Math.PI * (parseInt(tweetId, 10) / 1e15));
  token = (parseInt(parseFloat(token) * 1e10, 10)).toString(16).slice(0, 12);
  return token;
}

async function fetchSyndication(tweetId) {
  const token = syndicationToken(tweetId);
  const res = await fetch(
    `https://cdn.syndication.twimg.com/tweet-result?id=${tweetId}&token=${token}`,
    { headers: { "User-Agent": "Mozilla/5.0" } }
  );
  if (!res.ok) return null;
  const data = await res.json();
  if (data?.text) return { data, source: "Syndication" };
  return null;
}

function buildArticleMediaMap(article) {
  const entityMap = article?.content?.entityMap || [];
  const mediaEntities = article?.media_entities || [];
  const midToUrl = {};
  for (const m of mediaEntities) {
    if (m.media_id) {
      midToUrl[m.media_id] = m.media_info?.original_img_url || "";
    }
  }
  const keyToUrl = {};
  for (const ent of entityMap) {
    if (ent?.value?.type !== "MEDIA") continue;
    const items = ent.value?.data?.mediaItems || [];
    if (items[0]?.mediaId) {
      keyToUrl[String(ent.key)] = midToUrl[String(items[0].mediaId)] || "";
    }
  }
  return keyToUrl;
}

function buildArticleEntityMap(article) {
  const entityList = article.content?.entityMap || [];
  const result = {};
  for (const ent of entityList) {
    if (ent && typeof ent === "object" && ent.key) {
      result[String(ent.key)] = ent.value || {};
    }
  }
  return result;
}

function extractFxTwitterText(tweet, asMarkdown = false) {
  let text = (tweet.text || "").trim();
  if (text) return text;

  const article = tweet.article || {};
  const blocks = article.content?.blocks || [];
  if (blocks.length === 0) {
    const raw = tweet.raw_text;
    return (typeof raw === "object" && raw?.text) ? raw.text.trim() : "(无内容)";
  }

  const mediaMap = buildArticleMediaMap(article);
  const entityMap = buildArticleEntityMap(article);
  const parts = [];

  for (const b of blocks) {
    const blockType = b.type || "";
    const t = (b.text || "").trim();
    if (blockType === "atomic") {
      let resolved = false;
      for (const er of b.entityRanges || []) {
        const k = String(er.key || "");
        const ent = entityMap[k] || {};
        const entType = ent.type || "";
        if (entType === "MARKDOWN") {
          const mdContent = (ent.data?.markdown || "").trim();
          if (mdContent) {
            parts.push(`\n${mdContent}\n`);
            resolved = true;
            break;
          }
        } else if (entType === "MEDIA") {
          const imgUrl = mediaMap[k] || "";
          if (asMarkdown && imgUrl) {
            parts.push(`\n![图片](${imgUrl})\n`);
          } else {
            parts.push(imgUrl ? `\n[图片] ${imgUrl}\n` : "\n[图片]\n");
          }
          resolved = true;
          break;
        }
      }
      if (!resolved) parts.push("\n[图片]\n");
    } else if (t) {
      if (blockType === "header-one") parts.push(`\n# ${t}\n`);
      else if (blockType === "header-two") parts.push(`\n## ${t}\n`);
      else if (blockType === "unordered-list-item" || blockType === "ordered-list-item") {
        parts.push(`- ${t}\n`);
      } else {
        parts.push(t + "\n");
      }
    }
  }
  return parts.join("").trim() || "(无内容)";
}

function toMarkdown(result) {
  const { data, source } = result;
  const lines = [];

  if (source === "FxTwitter") {
    const tweet = data.tweet || {};
    const author = tweet.author || {};
    const name = author.name || "?";
    const screenName = author.screen_name || "?";
    const url = tweet.url || "";
    const article = tweet.article || {};
    const title = (article.title || "").trim();
    if (title) lines.push(`# ${title}\n\n`);
    lines.push(`**作者:** ${name} (@${screenName})\n`);
    if (url) lines.push(`**链接:** ${url}\n`);
    lines.push("\n---\n\n");
    lines.push(extractFxTwitterText(tweet, true));
  } else if (source === "VxTwitter") {
    lines.push(`**作者:** ${data.user_name || "?"} (@${data.user_screen_name || "?"})\n`);
    lines.push("\n---\n\n");
    lines.push(data.text || "(无内容)");
  } else if (source === "Syndication") {
    const user = data.user || {};
    lines.push(`**作者:** ${user.name || "?"} (@${user.screen_name || "?"})\n`);
    lines.push("\n---\n\n");
    lines.push(data.text || "(无内容)");
  }
  return lines.join("");
}

async function translateMarkdown(mdContent) {
  const { openrouter_api_key, model = "openai/gpt-4o-mini", translate_to = "Chinese" } =
    await chrome.storage.sync.get(["openrouter_api_key", "model", "translate_to"]);
  if (!openrouter_api_key) throw new Error("未配置 OpenRouter API Key，请在扩展选项中设置");

  const fullModel = model && !model.includes("/") ? `openai/${model}` : model;
  const prompt = `You are a professional ${translate_to} native translator who needs to fluently translate text into ${translate_to}.

## Translation Rules
1. Output only the translated content. No explanations, no "Here's the translation:", no markdown code block wrappers (\`\`\`).
2. Maintain exactly the same structure: paragraphs, headers (# ##), lists (-), line breaks. Preserve Markdown syntax - only translate text content.
3. Do NOT translate: URLs, file paths, code, commands, placeholders like <service> or <framework>, product names (Claude Code, Skills, Slack, GitHub).
4. For technical terms use common ${translate_to} equivalents when they exist. Otherwise keep English.
5. Keep link URLs unchanged: [text](url) - only translate "text", never modify "url".

Translate the following Markdown into ${translate_to}:

${mdContent}`;

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${openrouter_api_key}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://github.com"
    },
    body: JSON.stringify({
      model: fullModel,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.3
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `HTTP ${res.status}`);
  }
  const json = await res.json();
  const content = json?.choices?.[0]?.message?.content?.trim();
  if (!content) throw new Error("API 返回为空");
  return content;
}

function safeFilename(str) {
  return str.replace(/[<>:"/\\|?*]/g, "_").slice(0, 80);
}

async function processTweetAndDownload(url, options = {}) {
  const info = extractTweetInfo(url);
  if (!info) return { ok: false, error: "无法解析推文 URL" };

  const { screenName, tweetId } = info;
  let result = null;

  result = await fetchFxTwitter(screenName, tweetId);
  if (!result) result = await fetchVxTwitter(screenName, tweetId);
  if (!result) result = await fetchSyndication(tweetId);

  if (!result) {
    return { ok: false, error: "所有 API 均未能获取到推文内容" };
  }

  let md = toMarkdown(result);
  let filename = "";
  const tweet = result.source === "FxTwitter" ? result.data.tweet : {};
  const title = tweet.article?.title?.trim() || "";
  if (title) {
    filename = `${safeFilename(title)}_${tweetId}.md`;
  } else {
    filename = `tweet_${tweetId}.md`;
  }

  const doTranslate = options.translate ?? false;
  if (doTranslate) {
    try {
      md = await translateMarkdown(md);
      filename = filename.replace(".md", "_zh.md");
    } catch (e) {
      return { ok: false, error: `翻译失败: ${e.message}` };
    }
  }

  // Service Worker 中无 URL.createObjectURL，改用 data URL
  const base64 = btoa(unescape(encodeURIComponent(md)));
  const dataUrl = "data:text/markdown;charset=utf-8;base64," + base64;
  await chrome.downloads.download({
    url: dataUrl,
    filename,
    saveAs: options.saveAs ?? false
  });

  return { ok: true, filename };
}

// --- Bookmark listener ---
chrome.bookmarks.onCreated.addListener(async (id, bookmark) => {
  const url = bookmark.url || "";
  if (!isTweetUrl(url)) return;

  const { autoDownloadOnBookmark = true, translateOnBookmark = false } =
    await chrome.storage.sync.get(["autoDownloadOnBookmark", "translateOnBookmark"]);

  if (!autoDownloadOnBookmark) return;

  try {
    const res = await processTweetAndDownload(url, {
      translate: translateOnBookmark,
      saveAs: false
    });
    if (res.ok) {
      console.log("[X2MD] Downloaded:", res.filename);
    } else {
      console.error("[X2MD]", res.error);
    }
  } catch (e) {
    console.error("[X2MD]", e);
  }
});

// --- Message handler for popup ---
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "FETCH_AND_DOWNLOAD") {
    processTweetAndDownload(msg.url, {
      translate: msg.translate,
      saveAs: false
    })
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, error: e.message }));
    return true; // async response
  }
});
