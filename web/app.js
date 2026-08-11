const KNOWN = new Map([
  [0x00A0, ["NO-BREAK SPACE", "non-standard-space", false]],
  [0x00AD, ["SOFT HYPHEN", "invisible-format", false]],
  [0x061C, ["ARABIC LETTER MARK", "bidi-control", true]],
  [0x2007, ["FIGURE SPACE", "non-standard-space", false]],
  [0x200B, ["ZERO WIDTH SPACE", "zero-width", false]],
  [0x200C, ["ZERO WIDTH NON-JOINER", "join-control", true]],
  [0x200D, ["ZERO WIDTH JOINER", "join-control", true]],
  [0x200E, ["LEFT-TO-RIGHT MARK", "bidi-control", true]],
  [0x200F, ["RIGHT-TO-LEFT MARK", "bidi-control", true]],
  [0x202F, ["NARROW NO-BREAK SPACE", "non-standard-space", false]],
  [0x2060, ["WORD JOINER", "invisible-format", false]],
  [0xFEFF, ["ZERO WIDTH NO-BREAK SPACE / BOM", "zero-width", false]],
]);

const CONSERVATIVE_REMOVALS = new Set([0x00AD, 0x200B, 0x2060, 0xFEFF]);
const SPACE_REPLACEMENTS = new Set([0x00A0, 0x2007, 0x202F]);

function isBidi(cp) {
  return (cp >= 0x202A && cp <= 0x202E) || (cp >= 0x2066 && cp <= 0x2069);
}
function isVariation(cp) {
  return (cp >= 0xFE00 && cp <= 0xFE0F) || (cp >= 0xE0100 && cp <= 0xE01EF);
}
function classify(cp) {
  if (KNOWN.has(cp)) return KNOWN.get(cp);
  if (isBidi(cp)) return ["BIDI CONTROL", "bidi-control", true];
  if (isVariation(cp)) return ["VARIATION SELECTOR", "variation-selector", true];
  if (cp >= 0xE0000 && cp <= 0xE007F) return ["UNICODE TAG", "unicode-tag", true];
  return null;
}

function inspect(text) {
  const findings = [];
  let utf16Index = 0;
  for (const ch of text) {
    const cp = ch.codePointAt(0);
    const info = classify(cp);
    if (info) {
      findings.push({
        index: utf16Index,
        codepoint: `U+${cp.toString(16).toUpperCase().padStart(4, "0")}`,
        name: info[0],
        reason: info[1],
        context_sensitive: info[2],
      });
    }
    utf16Index += ch.length;
  }
  return {
    length: [...text].length,
    finding_count: findings.length,
    context_sensitive_count: findings.filter(x => x.context_sensitive).length,
    findings,
  };
}

function sanitize(text, strict = false) {
  let out = "";
  const normalized = text.replace(/\r\n?/g, "\n").normalize("NFC");
  for (const ch of normalized) {
    const cp = ch.codePointAt(0);
    if (SPACE_REPLACEMENTS.has(cp)) {
      out += " ";
      continue;
    }
    if (CONSERVATIVE_REMOVALS.has(cp)) continue;
    if (strict) {
      if (cp === 0x061C || cp === 0x200C || cp === 0x200D || cp === 0x200E || cp === 0x200F || isBidi(cp) || isVariation(cp)) continue;
    }
    out += ch;
  }
  return out;
}

const input = document.querySelector("#input");
const output = document.querySelector("#output");
const body = document.querySelector("#findingsBody");
const status = document.querySelector("#status");
let lastReport = null;

function render(text, resultText = null) {
  const report = inspect(text);
  document.querySelector("#charCount").textContent = report.length;
  document.querySelector("#findingCount").textContent = report.finding_count;
  document.querySelector("#contextCount").textContent = report.context_sensitive_count;
  document.querySelector("#changed").textContent = resultText === null ? "—" : (text === resultText ? "no" : "yes");
  status.textContent = report.finding_count ? `${report.finding_count} finding(s)` : "No findings";

  if (!report.findings.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty">疑わしいUnicodeは見つかりませんでした。</td></tr>';
  } else {
    body.replaceChildren(...report.findings.map(item => {
      const tr = document.createElement("tr");
      for (const value of [item.index, item.codepoint, item.name, item.reason, item.context_sensitive ? "yes" : "no"]) {
        const td = document.createElement("td");
        td.textContent = String(value);
        tr.appendChild(td);
      }
      return tr;
    }));
  }
  lastReport = { inspected_at: new Date().toISOString(), ...report, result_changed: resultText === null ? null : text !== resultText };
  return report;
}

function runSanitize(strict) {
  const cleaned = sanitize(input.value, strict);
  output.value = cleaned;
  render(input.value, cleaned);
}

function download(name, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

document.querySelector("#inspectBtn").addEventListener("click", () => { output.value = input.value; render(input.value, input.value); });
document.querySelector("#sanitizeBtn").addEventListener("click", () => runSanitize(false));
document.querySelector("#strictBtn").addEventListener("click", () => runSanitize(true));
document.querySelector("#sampleBtn").addEventListener("click", () => {
  input.value = "Visible\u200Btext with\u00A0NBSP and emoji 👩‍💻";
  output.value = "";
  render(input.value);
});
document.querySelector("#copyBtn").addEventListener("click", async () => {
  await navigator.clipboard.writeText(output.value);
  status.textContent = "Copied";
});
document.querySelector("#downloadBtn").addEventListener("click", () => download("textunmark-result.txt", output.value, "text/plain;charset=utf-8"));
document.querySelector("#jsonBtn").addEventListener("click", () => {
  render(input.value, output.value || null);
  download("textunmark-report.json", JSON.stringify(lastReport, null, 2), "application/json");
});
input.addEventListener("input", () => {
  document.querySelector("#charCount").textContent = [...input.value].length;
});
