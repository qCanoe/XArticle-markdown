// --- 标签切换 ---
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.remove("active");
      t.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    tab.setAttribute("aria-selected", "true");
    document.getElementById("panel-" + tab.dataset.panel).classList.add("active");
  });
});

// --- 下载 ---
document.getElementById("download").addEventListener("click", async () => {
  const urlInput = document.getElementById("url");
  const translateCheck = document.getElementById("translate");
  const btn = document.getElementById("download");
  const msgEl = document.getElementById("msg");

  const url = (urlInput.value || "").trim();
  if (!url) {
    showMsg("请输入推文链接", "error");
    return;
  }

  if (!/x\.com|twitter\.com/.test(url)) {
    showMsg("请输入有效的 X/Twitter 链接", "error");
    return;
  }

  btn.disabled = true;
  btn.classList.add("is-loading");
  msgEl.textContent = "";
  msgEl.className = "msg";
  msgEl.removeAttribute("role");

  try {
    const res = await chrome.runtime.sendMessage({
      type: "FETCH_AND_DOWNLOAD",
      url,
      translate: translateCheck.checked,
      saveAs: false
    });
    if (res?.ok) {
      showMsg(`已下载: ${res.filename}`, "success");
    } else {
      showMsg(res?.error || "下载失败", "error");
    }
  } catch (e) {
    showMsg(e?.message || "请求失败", "error");
  } finally {
    btn.disabled = false;
    btn.classList.remove("is-loading");
  }
});

function showMsg(text, type) {
  const el = document.getElementById("msg");
  el.textContent = text;
  el.className = `msg ${type}`;
  el.setAttribute("role", type === "error" ? "alert" : "status");
}

// --- 设置 ---
document.getElementById("save").addEventListener("click", async () => {
  const data = {
    autoDownloadOnBookmark: document.getElementById("autoDownloadOnBookmark").checked,
    translateOnBookmark: document.getElementById("translateOnBookmark").checked,
    openrouter_api_key: document.getElementById("openrouter_api_key").value.trim(),
    model: document.getElementById("model").value.trim() || "openai/gpt-4o-mini",
    translate_to: document.getElementById("translate_to").value.trim() || "Chinese"
  };
  await chrome.storage.sync.set(data);
  showToast("已保存");
});

function showToast(text) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  toast.setAttribute("aria-hidden", "false");
  toast.classList.add("is-visible");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.classList.remove("is-visible");
    toast.setAttribute("aria-hidden", "true");
  }, 2000);
}

// --- 加载设置 ---
async function loadSettings() {
  const keys = [
    "autoDownloadOnBookmark",
    "translateOnBookmark",
    "openrouter_api_key",
    "model",
    "translate_to"
  ];
  const data = await chrome.storage.sync.get(keys);
  document.getElementById("autoDownloadOnBookmark").checked =
    data.autoDownloadOnBookmark !== false;
  document.getElementById("translateOnBookmark").checked =
    !!data.translateOnBookmark;
  document.getElementById("openrouter_api_key").value =
    data.openrouter_api_key || "";
  document.getElementById("model").value = data.model || "openai/gpt-4o-mini";
  document.getElementById("translate_to").value = data.translate_to || "Chinese";
}

loadSettings();

// --- 从当前标签页获取 URL ---
chrome.tabs?.query({ active: true, currentWindow: true }, (tabs) => {
  const url = tabs?.[0]?.url || "";
  if (/x\.com|twitter\.com.*\/status\//.test(url)) {
    document.getElementById("url").value = url;
  }
});
