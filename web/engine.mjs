const KNOWN = new Map([
  [0x00a0, { name: "NO-BREAK SPACE", reason: "non-standard-space", contextSensitive: true }],
  [0x00ad, { name: "SOFT HYPHEN", reason: "invisible-format", contextSensitive: true }],
  [0x061c, { name: "ARABIC LETTER MARK", reason: "bidi-control", contextSensitive: true }],
  [0x2007, { name: "FIGURE SPACE", reason: "non-standard-space", contextSensitive: true }],
  [0x200b, { name: "ZERO WIDTH SPACE", reason: "zero-width", contextSensitive: true }],
  [0x200c, { name: "ZERO WIDTH NON-JOINER", reason: "join-control", contextSensitive: true }],
  [0x200d, { name: "ZERO WIDTH JOINER", reason: "join-control", contextSensitive: true }],
  [0x200e, { name: "LEFT-TO-RIGHT MARK", reason: "bidi-control", contextSensitive: true }],
  [0x200f, { name: "RIGHT-TO-LEFT MARK", reason: "bidi-control", contextSensitive: true }],
  [0x202f, { name: "NARROW NO-BREAK SPACE", reason: "non-standard-space", contextSensitive: true }],
  [0x2060, { name: "WORD JOINER", reason: "invisible-format", contextSensitive: true }],
  [0xfeff, { name: "ZERO WIDTH NO-BREAK SPACE / BOM", reason: "zero-width", contextSensitive: true }],
]);

const STANDARD_REMOVALS = new Set([0x00ad, 0x200b, 0x2060, 0xfeff]);
const STANDARD_SPACE_REPLACEMENTS = new Set([0x00a0, 0x2007, 0x202f]);

const formatRegex = /\p{Cf}/u;
const controlRegex = /\p{Cc}/u;

function utf8Length(cp) {
  if (cp <= 0x7f) return 1;
  if (cp <= 0x7ff) return 2;
  if (cp <= 0xffff) return 3;
  return 4;
}

function isBidi(cp) {
  return (cp >= 0x202a && cp <= 0x202e) || (cp >= 0x2066 && cp <= 0x2069);
}

function isVariationSelector(cp) {
  return (cp >= 0xfe00 && cp <= 0xfe0f) || (cp >= 0xe0100 && cp <= 0xe01ef);
}

function isUnicodeTag(cp) {
  return cp >= 0xe0000 && cp <= 0xe007f;
}

function genericName(cp, reason) {
  if (reason === "variation-selector") return `VARIATION SELECTOR ${formatCodePoint(cp)}`;
  if (reason === "unicode-tag") return `UNICODE TAG ${formatCodePoint(cp)}`;
  if (reason === "bidi-control") return `BIDI CONTROL ${formatCodePoint(cp)}`;
  if (reason === "format-control") return `FORMAT CONTROL ${formatCodePoint(cp)}`;
  if (reason === "control-character") return `CONTROL CHARACTER ${formatCodePoint(cp)}`;
  return formatCodePoint(cp);
}

export function formatCodePoint(cp) {
  return `U+${cp.toString(16).toUpperCase().padStart(cp > 0xffff ? 6 : 4, "0")}`;
}

export function classifyCharacter(ch) {
  const cp = ch.codePointAt(0);
  const known = KNOWN.get(cp);
  if (known) return { ...known, codePoint: cp };
  if (isBidi(cp)) {
    return { name: genericName(cp, "bidi-control"), reason: "bidi-control", contextSensitive: true, codePoint: cp };
  }
  if (isVariationSelector(cp)) {
    return { name: genericName(cp, "variation-selector"), reason: "variation-selector", contextSensitive: true, codePoint: cp };
  }
  if (isUnicodeTag(cp)) {
    return { name: genericName(cp, "unicode-tag"), reason: "unicode-tag", contextSensitive: true, codePoint: cp };
  }
  if (formatRegex.test(ch)) {
    return { name: genericName(cp, "format-control"), reason: "format-control", contextSensitive: true, codePoint: cp };
  }
  if (controlRegex.test(ch) && ch !== "\n" && ch !== "\r" && ch !== "\t") {
    return { name: genericName(cp, "control-character"), reason: "control-character", contextSensitive: true, codePoint: cp };
  }
  return null;
}

function contextSnippet(text, utf16Index, utf16Length) {
  const before = text.slice(Math.max(0, utf16Index - 28), utf16Index);
  const after = text.slice(utf16Index + utf16Length, utf16Index + utf16Length + 28);
  return { before, after };
}

export function inspectText(text) {
  const findings = [];
  const byReason = {};
  const byCodePoint = {};
  let codePointIndex = 0;
  let utf16Index = 0;
  let utf8Offset = 0;
  let line = 1;
  let column = 1;

  for (const ch of text) {
    const cp = ch.codePointAt(0);
    const classification = classifyCharacter(ch);
    if (classification) {
      const codepoint = formatCodePoint(cp);
      const snippet = contextSnippet(text, utf16Index, ch.length);
      const finding = {
        index: codePointIndex,
        utf16_index: utf16Index,
        utf8_offset: utf8Offset,
        line,
        column,
        codepoint,
        name: classification.name,
        reason: classification.reason,
        context_sensitive: classification.contextSensitive,
        context_before: snippet.before,
        context_after: snippet.after,
      };
      findings.push(finding);
      byReason[finding.reason] = (byReason[finding.reason] || 0) + 1;
      byCodePoint[finding.codepoint] = (byCodePoint[finding.codepoint] || 0) + 1;
    }

    codePointIndex += 1;
    utf16Index += ch.length;
    utf8Offset += utf8Length(cp);
    if (ch === "\n") {
      line += 1;
      column = 1;
    } else {
      column += 1;
    }
  }

  return {
    length: codePointIndex,
    utf16_length: text.length,
    utf8_bytes: utf8Offset,
    line_count: text.length === 0 ? 0 : line,
    finding_count: findings.length,
    context_sensitive_count: findings.filter((item) => item.context_sensitive).length,
    by_reason: Object.fromEntries(Object.entries(byReason).sort(([a], [b]) => a.localeCompare(b))),
    by_codepoint: Object.fromEntries(Object.entries(byCodePoint).sort(([a], [b]) => a.localeCompare(b))),
    findings,
  };
}

function addMutation(mutations, mutation) {
  mutations.push({ id: mutations.length + 1, ...mutation });
}

function transformCharacters(text, profile, mutations) {
  if (profile === "inspect") return text;

  let output = "";
  let codePointIndex = 0;
  let line = 1;
  let column = 1;

  for (const ch of text) {
    const cp = ch.codePointAt(0);
    const classification = classifyCharacter(ch);
    let replacement = ch;
    let action = null;

    if (STANDARD_SPACE_REPLACEMENTS.has(cp)) {
      replacement = " ";
      action = "replace";
    } else if (STANDARD_REMOVALS.has(cp)) {
      replacement = "";
      action = "remove";
    } else if (profile === "aggressive" && classification) {
      replacement = "";
      action = "remove";
    }

    if (action) {
      addMutation(mutations, {
        type: action,
        stage: "character-cleanup",
        index: codePointIndex,
        line,
        column,
        codepoint: formatCodePoint(cp),
        name: classification?.name || formatCodePoint(cp),
        reason: classification?.reason || "normalization",
        before: ch,
        after: replacement,
      });
    }

    output += replacement;
    codePointIndex += 1;
    if (ch === "\n") {
      line += 1;
      column = 1;
    } else {
      column += 1;
    }
  }
  return output;
}

function normalizeNewlines(text, mutations) {
  if (!text.includes("\r")) return text;
  const converted = text.replace(/\r\n?/g, "\n");
  if (converted !== text) {
    addMutation(mutations, {
      type: "normalize",
      stage: "newline-normalization",
      index: null,
      line: null,
      column: null,
      codepoint: null,
      name: "LINE ENDING NORMALIZATION",
      reason: "newline-normalization",
      before: "CRLF/CR",
      after: "LF",
    });
  }
  return converted;
}

export function sanitizeText(text, profile = "standard") {
  if (!new Set(["inspect", "standard", "aggressive"]).has(profile)) {
    throw new Error(`Unknown cleanup profile: ${profile}`);
  }

  if (profile === "inspect") {
    return { text, changed: false, mutations: [], profile, before: inspectText(text), after: inspectText(text) };
  }

  const mutations = [];
  let working = normalizeNewlines(text, mutations);
  working = transformCharacters(working, profile, mutations);
  const normalized = working.normalize("NFC");
  if (normalized !== working) {
    addMutation(mutations, {
      type: "normalize",
      stage: "unicode-normalization",
      index: null,
      line: null,
      column: null,
      codepoint: null,
      name: "UNICODE NFC NORMALIZATION",
      reason: "unicode-normalization",
      before: null,
      after: null,
    });
    working = normalized;
  }

  return {
    text: working,
    changed: working !== text,
    mutations,
    profile,
    before: inspectText(text),
    after: inspectText(working),
  };
}

export const detectorRegistry = [
  {
    id: "unicode-artifact",
    label: "Unicode artifacts",
    description: "Counts explicit invisible/control Unicode findings. This is not an AI-watermark probability.",
    available: true,
    detect(text) {
      const report = inspectText(text);
      return {
        id: this.id,
        label: this.label,
        available: true,
        detected: report.finding_count > 0,
        metrics: {
          finding_count: report.finding_count,
          context_sensitive_count: report.context_sensitive_count,
          artifact_density: report.length ? report.finding_count / report.length : 0,
        },
        note: "Artifact density is descriptive only; it does not prove AI authorship or a provider watermark.",
      };
    },
  },
  {
    id: "anthropic",
    label: "Anthropic model-level watermark",
    description: "Reserved adapter for a reproducible public detector/specification.",
    available: false,
    detect() {
      return {
        id: this.id,
        label: this.label,
        available: false,
        detected: null,
        metrics: {},
        note: "Not available: no reproducible public detector is integrated.",
      };
    },
  },
];

export function runDetectors(text) {
  return detectorRegistry.map((detector) => detector.detect(text));
}

export function analyzeText(text, profile = "inspect") {
  const sourceInspection = inspectText(text);
  const sanitation = sanitizeText(text, profile);
  return {
    schema_version: 1,
    analyzed_at: new Date().toISOString(),
    profile,
    source: sourceInspection,
    result: sanitation.after,
    changed: sanitation.changed,
    mutations: sanitation.mutations,
    output_text: sanitation.text,
    detectors_before: runDetectors(text),
    detectors_after: runDetectors(sanitation.text),
  };
}

export function visibleFindingToken(finding) {
  return `⟦${finding.codepoint} ${finding.name}⟧`;
}
