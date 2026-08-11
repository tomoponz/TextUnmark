const MAX_FILE_SIZE = 10 * 1024 * 1024;
const TEXT_EXTENSIONS = new Set([
  "txt", "md", "markdown", "rst", "csv", "json", "jsonl", "yaml", "yml",
  "html", "htm", "css", "xml", "js", "mjs", "cjs", "ts", "tsx", "jsx",
  "py", "java", "kt", "kts", "c", "h", "cpp", "hpp", "cs", "go", "rs", "swift",
]);

const $ = (selector) => document.querySelector(selector);
const elements = {
  input: $("#input"),
  output: $("#output"),
  inputMeta: $("#inputMeta"),
  analyzeBtn: $("#analyzeBtn"),
  sampleBtn: $("#sampleBtn"),
  clearBtn: $("#clearBtn"),
  copyBtn: $("#copyBtn"),
  downloadBtn: $("#downloadBtn"),
  jsonBtn: $("#jsonBtn"),
  status: $("#status"),
  charCount: $("#charCount"),
  findingCount: $("#findingCount"),
  changeCount: $("#changeCount"),
  fileCount: $("#fileCount"),
  changedLabel: $("#changedLabel"),
  detectorList: $("#detectorList"),
  findingCards: $("#findingCards"),
  findingSummary: $("#findingSummary"),
  mutationList: $("#mutationList"),
  mutationSummary: $("#mutationSummary"),
  dropZone: $("#dropZone"),
  fileInput: $("#fileInput"),
  filesPanel: $("#filesPanel"),
  filesBody: $("#filesBody"),
  rescanFilesBtn: $("#rescanFilesBtn"),
};

const state = {
  report: null,
  loadedFiles: [],
  activeFileName: null,
  requestId: 0,
};

const worker = new Worker("./worker.mjs", { type: "module" });
const pending = new Map();

worker.addEventListener("message", (event) => {
  const message = event.data || {};
  const request = pending.get(message.id);
  if (!request) return;
  pending.delete(message.id);
  if (message.ok) request.resolve(message);
  else request.reject(new Error(message.error || "Worker error"));
});

worker.addEventListener("error", (event) => {
  for (const request of pending.values()) request.reject(new Error(event.message || "Worker failed"));
  pending.clear();
  setStatus("解析エンジンでエラー", "error");
});

function callWorker(type, payload = {}) {
  const id = ++state.requestId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, ...payload });
  });
}

function currentProfile() {
  return document.querySelector('input[name="profile"]:checked')?.value || "inspect";
}

function setStatus(text, kind = "") {
  elements.status.textContent = text;
  elements.status.className = `status-pill${kind ? ` ${kind}` : ""}`;
}

function setBusy(busy) {
  elements.analyzeBtn.disabled = busy;
  elements.analyzeBtn.textContent = busy ? "解析中…" : "解析する";
}

function updateInputMeta() {
  const chars = Array.from(elements.input.value).length;
  const bytes = new TextEncoder().encode(elements.input.value).length;
  elements.inputMeta.textContent = `${chars.toLocaleString()}文字 · ${formatBytes(bytes)}`;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function safeFileName(name) {
  return (name || "textunmark-result.txt").replace(/[\\/:*?"<>|]+/g, "-");
}

function outputFileName() {
  if (!state.activeFileName) return "textunmark-result.txt";
  const name = state.activeFileName;
  const dot = name.lastIndexOf(".");
  return dot > 0 ? `${name.slice(0, dot)}.textunmark${name.slice(dot)}` : `${name}.textunmark.txt`;
}

function download(name, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = safeFileName(name);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function clearNode(node) {
  node.replaceChildren();
}

function emptyState(text) {
  const div = document.createElement("div");
  div.className = "empty-state";
  div.textContent = text;
  return div;
}

function renderDetectorList(report) {
  clearNode(elements.detectorList);
  for (const detector of report.detectors_before) {
    const item = document.createElement("div");
    item.className = "detector-item";

    const head = document.createElement("div");
    head.className = "detector-head";
    const label = document.createElement("span");
    label.className = "detector-label";
    label.textContent = detector.label;
    const badge = document.createElement("span");
    badge.className = `detector-state${detector.available ? " available" : ""}`;
    badge.textContent = detector.available ? (detector.detected ? "finding" : "clear") : "not available";
    head.append(label, badge);
    item.appendChild(head);

    const note = document.createElement("p");
    note.textContent = detector.note || "";
    item.appendChild(note);

    if (detector.available && Object.keys(detector.metrics || {}).length) {
      const metrics = document.createElement("div");
      metrics.className = "detector-metrics";
      for (const [key, value] of Object.entries(detector.metrics)) {
        const span = document.createElement("span");
        const printable = typeof value === "number" && !Number.isInteger(value) ? value.toFixed(6) : String(value);
        span.textContent = `${key}: ${printable}`;
        metrics.appendChild(span);
      }
      item.appendChild(metrics);
    }
    elements.detectorList.appendChild(item);
  }
}

function appendContext(parent, finding) {
  const context = document.createElement("div");
  context.className = "finding-context";
  context.appendChild(document.createTextNode(finding.context_before || ""));
  const token = document.createElement("span");
  token.className = "finding-token";
  token.textContent = finding.codepoint;
  token.title = finding.name;
  context.appendChild(token);
  context.appendChild(document.createTextNode(finding.context_after || ""));
  parent.appendChild(context);
}

function renderFindings(report) {
  clearNode(elements.findingCards);
  const findings = report.source.findings;
  elements.findingSummary.textContent = `${findings.length.toLocaleString()}件`;
  if (!findings.length) {
    elements.findingCards.appendChild(emptyState("検査対象のUnicode文字は見つかりませんでした。"));
    return;
  }

  const visible = findings.slice(0, 300);
  for (const finding of visible) {
    const card = document.createElement("div");
    card.className = "finding-card";

    const identity = document.createElement("div");
    const code = document.createElement("div");
    code.className = "finding-code";
    code.textContent = `${finding.codepoint} · ${finding.reason}`;
    const name = document.createElement("div");
    name.className = "finding-name";
    name.textContent = finding.name;
    identity.append(code, name);
    card.appendChild(identity);

    appendContext(card, finding);

    const location = document.createElement("div");
    location.className = "finding-location";
    location.textContent = `L${finding.line}:C${finding.column} · index ${finding.index}`;
    card.appendChild(location);
    elements.findingCards.appendChild(card);
  }

  if (findings.length > visible.length) {
    elements.findingCards.appendChild(emptyState(`先頭${visible.length}件を表示しています。全${findings.length}件はJSONレポートに含まれます。`));
  }
}

function mutationLabel(mutation) {
  if (mutation.type === "remove") return "削除";
  if (mutation.type === "replace") return "置換";
  return "正規化";
}

function renderMutations(report) {
  clearNode(elements.mutationList);
  const mutations = report.mutations;
  elements.mutationSummary.textContent = `${mutations.length.toLocaleString()}件`;
  if (!mutations.length) {
    elements.mutationList.appendChild(emptyState(report.profile === "inspect" ? "「検査のみ」では文章を変更しません。" : "このモードで変更される箇所はありません。"));
    return;
  }

  for (const mutation of mutations.slice(0, 300)) {
    const item = document.createElement("div");
    item.className = "mutation-item";
    const action = document.createElement("div");
    action.className = "mutation-action";
    action.textContent = `${mutationLabel(mutation)} · ${mutation.codepoint || mutation.reason}`;
    const detail = document.createElement("div");
    detail.className = "mutation-detail";
    const location = mutation.line ? `L${mutation.line}:C${mutation.column} · ` : "";
    detail.textContent = `${location}${mutation.name}`;
    const result = document.createElement("div");
    result.className = "finding-location";
    if (mutation.type === "replace") result.textContent = "→ SPACE";
    else if (mutation.type === "remove") result.textContent = "→ removed";
    else result.textContent = mutation.stage;
    item.append(action, detail, result);
    elements.mutationList.appendChild(item);
  }
}

function renderReport(report) {
  state.report = report;
  elements.output.value = report.output_text;
  elements.charCount.textContent = report.source.length.toLocaleString();
  elements.findingCount.textContent = report.source.finding_count.toLocaleString();
  elements.changeCount.textContent = report.mutations.length.toLocaleString();
  elements.fileCount.textContent = state.loadedFiles.length.toLocaleString();
  elements.changedLabel.textContent = report.changed ? `${report.mutations.length}件の変更をプレビュー` : "変更なし";

  renderDetectorList(report);
  renderFindings(report);
  renderMutations(report);

  if (report.source.finding_count) setStatus(`${report.source.finding_count}件を確認`, "warning");
  else setStatus("検査対象なし", "success");
}

async function analyze() {
  setBusy(true);
  setStatus("解析中…");
  try {
    const response = await callWorker("analyze", { text: elements.input.value, profile: currentProfile() });
    renderReport(response.report);
  } catch (error) {
    console.error(error);
    setStatus("解析に失敗", "error");
  } finally {
    setBusy(false);
  }
}

function selectProfileCard() {
  document.querySelectorAll(".profile-card").forEach((card) => {
    card.classList.toggle("selected", Boolean(card.querySelector("input")?.checked));
  });
}

function looksLikeTextFile(file) {
  if (file.type.startsWith("text/")) return true;
  const extension = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  return TEXT_EXTENSIONS.has(extension) || file.type === "application/json" || file.type === "application/xml";
}

async function readFiles(fileList) {
  const incoming = Array.from(fileList || []);
  if (!incoming.length) return;
  setStatus("ファイル読込中…");
  const loaded = [];

  for (const file of incoming) {
    if (file.size > MAX_FILE_SIZE) {
      loaded.push({ name: file.name, size: file.size, error: "10 MBを超えるためスキップ" });
      continue;
    }
    if (!looksLikeTextFile(file)) {
      loaded.push({ name: file.name, size: file.size, error: "テキスト形式として認識できません" });
      continue;
    }
    try {
      const text = await file.text();
      if (text.includes("\u0000")) {
        loaded.push({ name: file.name, size: file.size, error: "NULを含むためバイナリとしてスキップ" });
      } else {
        loaded.push({ name: file.name, size: file.size, text });
      }
    } catch (error) {
      loaded.push({ name: file.name, size: file.size, error: error instanceof Error ? error.message : String(error) });
    }
  }

  state.loadedFiles = loaded;
  elements.fileCount.textContent = loaded.length.toLocaleString();
  elements.filesPanel.hidden = false;

  const firstReadable = loaded.find((file) => typeof file.text === "string");
  if (firstReadable) openLoadedFile(firstReadable.name, false);
  await scanLoadedFiles();
}

function openLoadedFile(name, shouldAnalyze = true) {
  const file = state.loadedFiles.find((item) => item.name === name);
  if (!file || typeof file.text !== "string") return;
  state.activeFileName = file.name;
  elements.input.value = file.text;
  updateInputMeta();
  setStatus(`${file.name} を表示`);
  if (shouldAnalyze) analyze();
}

async function scanLoadedFiles() {
  const readable = state.loadedFiles.filter((file) => typeof file.text === "string");
  clearNode(elements.filesBody);
  if (!readable.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "解析可能なファイルがありません。";
    row.appendChild(cell);
    elements.filesBody.appendChild(row);
    return;
  }

  try {
    const response = await callWorker("scan-files", { files: readable });
    const byName = new Map(response.results.map((result) => [result.name, result]));
    for (const file of state.loadedFiles) {
      const row = document.createElement("tr");
      const result = byName.get(file.name);
      const values = [
        file.name,
        formatBytes(file.size),
        file.error ? file.error : String(result?.report.finding_count ?? 0),
        file.error ? "—" : String(result?.report.line_count ?? 0),
      ];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      const actionCell = document.createElement("td");
      if (!file.error) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button ghost file-open";
        button.textContent = "開く";
        button.addEventListener("click", () => openLoadedFile(file.name));
        actionCell.appendChild(button);
      }
      row.appendChild(actionCell);
      elements.filesBody.appendChild(row);
    }
    const total = response.results.reduce((sum, item) => sum + item.report.finding_count, 0);
    setStatus(`${readable.length}ファイル · ${total}件を確認`, total ? "warning" : "success");
  } catch (error) {
    console.error(error);
    setStatus("ファイル監査に失敗", "error");
  }
}

async function copyOutput() {
  if (!state.report) return setStatus("先に解析してください", "warning");
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(elements.output.value);
    } else {
      elements.output.focus();
      elements.output.select();
      document.execCommand("copy");
      elements.output.setSelectionRange(0, 0);
    }
    setStatus("コピーしました", "success");
  } catch (error) {
    console.error(error);
    setStatus("コピーできませんでした", "error");
  }
}

function clearAll() {
  elements.input.value = "";
  elements.output.value = "";
  state.report = null;
  state.loadedFiles = [];
  state.activeFileName = null;
  elements.filesPanel.hidden = true;
  elements.charCount.textContent = "0";
  elements.findingCount.textContent = "0";
  elements.changeCount.textContent = "0";
  elements.fileCount.textContent = "0";
  elements.changedLabel.textContent = "変更なし";
  elements.detectorList.replaceChildren(emptyState("解析すると検出器の状態が表示されます。"));
  elements.findingCards.replaceChildren(emptyState("まだ解析していません。"));
  elements.mutationList.replaceChildren(emptyState("「検査のみ」では文章を変更しません。"));
  elements.findingSummary.textContent = "0件";
  elements.mutationSummary.textContent = "0件";
  updateInputMeta();
  setStatus("入力待ち");
}

elements.analyzeBtn.addEventListener("click", analyze);
elements.sampleBtn.addEventListener("click", () => {
  elements.input.value = "Visible\u200Btext with\u00A0NBSP, WORD\u2060JOINER and emoji 👩‍💻.\nAnthropic detector is intentionally unavailable until a reproducible public specification exists.";
  state.activeFileName = null;
  updateInputMeta();
  analyze();
});
elements.clearBtn.addEventListener("click", clearAll);
elements.copyBtn.addEventListener("click", copyOutput);
elements.downloadBtn.addEventListener("click", () => {
  if (!state.report) return setStatus("先に解析してください", "warning");
  download(outputFileName(), elements.output.value, "text/plain;charset=utf-8");
  setStatus("TXTを保存しました", "success");
});
elements.jsonBtn.addEventListener("click", () => {
  if (!state.report) return setStatus("先に解析してください", "warning");
  const name = state.activeFileName ? `${state.activeFileName}.textunmark.json` : "textunmark-report.json";
  download(name, `${JSON.stringify(state.report, null, 2)}\n`, "application/json;charset=utf-8");
  setStatus("JSONレポートを保存しました", "success");
});
elements.rescanFilesBtn.addEventListener("click", scanLoadedFiles);
elements.input.addEventListener("input", () => {
  state.activeFileName = null;
  updateInputMeta();
});

document.querySelectorAll('input[name="profile"]').forEach((radio) => {
  radio.addEventListener("change", selectProfileCard);
});

elements.dropZone.addEventListener("click", () => elements.fileInput.click());
elements.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    elements.fileInput.click();
  }
});
elements.fileInput.addEventListener("change", () => readFiles(elements.fileInput.files));

for (const eventName of ["dragenter", "dragover"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("dragging");
  });
}
elements.dropZone.addEventListener("drop", (event) => readFiles(event.dataTransfer?.files));

selectProfileCard();
updateInputMeta();
