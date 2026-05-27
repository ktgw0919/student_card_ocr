const fileInput = document.getElementById("file-input");
const previewWrap = document.getElementById("preview-wrap");
const preview = document.getElementById("preview");
const submitBtn = document.getElementById("submit-btn");
const statusLine = document.getElementById("status-line");
const resultSection = document.getElementById("result-section");
const summaryEl = document.getElementById("summary");
const resultJsonEl = document.getElementById("result-json");
const apiKeySection = document.getElementById("api-key-section");
const apiKeyInput = document.getElementById("api-key-input");

const API_KEY_STORAGE = "student_card_ocr_api_key";

let selectedFile = null;
let previewUrl = null;

function show(el) {
  el.hidden = false;
  el.classList.remove("hidden");
}

function hide(el) {
  el.hidden = true;
  el.classList.add("hidden");
}

function setStatus(text, kind = "") {
  statusLine.textContent = text;
  statusLine.className = "status-line";
  if (kind) {
    statusLine.classList.add(kind);
  }
}

function revokePreview() {
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }
}

function formatField(fields, key) {
  const field = fields?.[key];
  if (!field) {
    return "—";
  }
  const value = field.normalized_value ?? field.value;
  if (!value) {
    return `（${field.status}）`;
  }
  return value;
}

function badgeClass(status) {
  if (status === "success") {
    return "badge badge-success";
  }
  if (status === "warning") {
    return "badge badge-warning";
  }
  return "badge badge-error";
}

function renderSummary(data) {
  summaryEl.innerHTML = "";

  const rows = [
    ["全体ステータス", data.status],
    ["QR", data.qr_status],
    ["メッセージ", data.message],
  ];

  const structured = data.data?.structured;
  if (structured) {
    rows.push(
      ["文書種別", structured.document_type],
      ["学籍番号", formatField(structured.fields, "student_id")],
      ["氏名", formatField(structured.fields, "name")],
      ["有効期限", formatField(structured.fields, "expiry_date")]
    );
  }

  if (data.data?.error) {
    rows.push(["OCR エラー", data.data.error]);
  }

  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = label;

    const dd = document.createElement("dd");
    if (label === "全体ステータス") {
      const span = document.createElement("span");
      span.className = badgeClass(String(value));
      span.textContent = String(value);
      dd.appendChild(span);
    } else {
      dd.textContent = String(value);
    }

    summaryEl.appendChild(dt);
    summaryEl.appendChild(dd);
  }
}

async function parseErrorResponse(response) {
  try {
    const body = await response.json();
    if (body?.detail) {
      if (typeof body.detail === "string") {
        return body.detail;
      }
      return JSON.stringify(body.detail);
    }
  } catch {
    /* ignore */
  }
  return `HTTP ${response.status}`;
}

function getApiKey() {
  return apiKeyInput.value.trim();
}

async function submitVerify() {
  if (!selectedFile) {
    return;
  }

  submitBtn.disabled = true;
  hide(resultSection);
  setStatus("処理中です… OCR には数十秒かかることがあります。", "is-busy");

  const formData = new FormData();
  formData.append("file", selectedFile, selectedFile.name);

  const headers = {};
  const apiKey = getApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
    localStorage.setItem(API_KEY_STORAGE, apiKey);
  }

  const started = performance.now();

  try {
    const response = await fetch("/verify", {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      const message = await parseErrorResponse(response);
      throw new Error(message);
    }

    const data = await response.json();
    console.log("VerifyResponse:", data);

    const elapsed = ((performance.now() - started) / 1000).toFixed(1);
    setStatus(`完了（${elapsed} 秒）`, "");
    renderSummary(data);
    resultJsonEl.textContent = JSON.stringify(data, null, 2);
    show(resultSection);
  } catch (err) {
    console.error(err);
    setStatus(err instanceof Error ? err.message : "送信に失敗しました。", "is-error");
  } finally {
    submitBtn.disabled = !selectedFile;
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  revokePreview();
  selectedFile = file ?? null;

  if (!selectedFile) {
    hide(previewWrap);
    submitBtn.disabled = true;
    setStatus("");
    return;
  }

  previewUrl = URL.createObjectURL(selectedFile);
  preview.src = previewUrl;
  show(previewWrap);
  submitBtn.disabled = false;
  setStatus(`選択: ${selectedFile.name}`);
});

submitBtn.addEventListener("click", () => {
  void submitVerify();
});

const savedKey = localStorage.getItem(API_KEY_STORAGE);
if (savedKey) {
  apiKeyInput.value = savedKey;
}
show(apiKeySection);

fetch("/health")
  .then((r) => {
    if (!r.ok) {
      throw new Error("health check failed");
    }
  })
  .catch(() => {
    setStatus("API に接続できません。サーバが起動しているか確認してください。", "is-error");
  });
