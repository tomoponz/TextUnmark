import assert from "node:assert/strict";
import test from "node:test";

import { analyzeText, inspectText, runDetectors, sanitizeText } from "./engine.mjs";

test("inspectText reports code-point, UTF-16, UTF-8, line and column positions", () => {
  const report = inspectText("😀A\u200bB");
  assert.equal(report.finding_count, 1);
  const finding = report.findings[0];
  assert.equal(finding.index, 2);
  assert.equal(finding.utf16_index, 3);
  assert.equal(finding.utf8_offset, 5);
  assert.equal(finding.line, 1);
  assert.equal(finding.column, 3);
  assert.equal(finding.codepoint, "U+200B");
});

test("generic Unicode format controls are detected", () => {
  const report = inspectText("A\u2061B");
  assert.equal(report.finding_count, 1);
  assert.equal(report.findings[0].reason, "format-control");
});

test("inspect profile never mutates text", () => {
  const source = "A\u200bB";
  const result = sanitizeText(source, "inspect");
  assert.equal(result.text, source);
  assert.equal(result.changed, false);
  assert.deepEqual(result.mutations, []);
});

test("standard profile records exact removals and replacements", () => {
  const result = sanitizeText("A\u200bB\u00a0C", "standard");
  assert.equal(result.text, "AB C");
  assert.equal(result.changed, true);
  assert.equal(result.mutations.length, 2);
  assert.equal(result.mutations[0].type, "remove");
  assert.equal(result.mutations[1].type, "replace");
});

test("aggressive profile removes context-sensitive ZWJ", () => {
  const result = sanitizeText("A\u200dB", "aggressive");
  assert.equal(result.text, "AB");
  assert.equal(result.mutations.length, 1);
});

test("detector registry keeps Anthropic detector explicitly unavailable", () => {
  const results = runDetectors("plain text");
  const anthropic = results.find((result) => result.id === "anthropic");
  assert.ok(anthropic);
  assert.equal(anthropic.available, false);
  assert.equal(anthropic.detected, null);
});

test("analysis reports output and changes without probability-like watermark score", () => {
  const report = analyzeText("A\u200bB", "standard");
  assert.equal(report.output_text, "AB");
  assert.equal(report.changed, true);
  assert.equal(report.mutations.length, 1);
  const unicodeDetector = report.detectors_before.find((result) => result.id === "unicode-artifact");
  assert.equal(unicodeDetector.metrics.finding_count, 1);
  assert.ok("artifact_density" in unicodeDetector.metrics);
  assert.equal("score" in unicodeDetector, false);
});
