import json
from pathlib import Path
import tempfile
import unittest

from textunmark.batch import process_path
from textunmark.compare import compare_texts
from textunmark.detectors.registry import available_detectors, run_detectors
from textunmark.pipeline import analyze_text
from textunmark.report import render_analysis_html
from textunmark.sanitize import sanitize_text
from textunmark.sarif import scan_to_sarif
from textunmark.unicode_scan import inspect_text


class UnicodeInspectionTests(unittest.TestCase):
    def test_detects_known_invisible_and_nonstandard_space(self):
        report = inspect_text("A\u200bB\u00a0C")
        self.assertEqual(report["finding_count"], 2)
        self.assertEqual(report["by_reason"]["zero-width"], 1)
        self.assertEqual(report["by_reason"]["non-standard-space"], 1)

    def test_clean_ascii_has_no_findings(self):
        report = inspect_text("plain text\n")
        self.assertEqual(report["finding_count"], 0)

    def test_joiner_is_context_sensitive(self):
        report = inspect_text("A\u200dB")
        self.assertEqual(report["finding_count"], 1)
        self.assertTrue(report["findings"][0]["context_sensitive"])


class SanitizationTests(unittest.TestCase):
    def test_conservative_removes_zero_width_and_normalizes_nbsp(self):
        result = sanitize_text("A\u200bB\u00a0C")
        self.assertEqual(result.text, "AB C")
        self.assertTrue(result.changed)
        self.assertEqual(result.after["finding_count"], 0)

    def test_conservative_preserves_zwj(self):
        result = sanitize_text("A\u200dB", profile="conservative")
        self.assertEqual(result.text, "A\u200dB")
        self.assertFalse(result.changed)

    def test_strict_removes_zwj(self):
        result = sanitize_text("A\u200dB", profile="strict")
        self.assertEqual(result.text, "AB")
        self.assertTrue(result.changed)

    def test_nfkc_is_opt_in(self):
        source = "ＡＢＣ"
        nfc = sanitize_text(source, normalization="NFC")
        nfkc = sanitize_text(source, normalization="NFKC")
        self.assertEqual(nfc.text, source)
        self.assertEqual(nfkc.text, "ABC")


class ComparisonTests(unittest.TestCase):
    def test_compare_reports_hashes_and_findings(self):
        report = compare_texts("A\u200bB", "AB")
        self.assertFalse(report["identical"])
        self.assertNotEqual(report["before_sha256"], report["after_sha256"])
        self.assertEqual(report["before_inspection"]["finding_count"], 1)
        self.assertEqual(report["after_inspection"]["finding_count"], 0)


class DetectorTests(unittest.TestCase):
    def test_registry_exposes_unicode_detector(self):
        ids = {item["id"] for item in available_detectors()}
        self.assertIn("unicode-artifact", ids)

    def test_unicode_detector_is_explicitly_artifact_based(self):
        result = run_detectors("A\u200bB")[0]
        self.assertTrue(result.detected)
        self.assertGreater(result.score, 0)
        self.assertIsNone(result.confidence)
        self.assertIn("not watermark probability", result.details["note"])


class PipelineTests(unittest.TestCase):
    def test_analysis_contains_before_after_detector_results(self):
        result = analyze_text("A\u200bB")
        data = result.to_dict(include_text=True)
        self.assertEqual(data["inspection"]["finding_count"], 1)
        self.assertEqual(data["sanitized"]["text"], "AB")
        self.assertEqual(data["comparison"]["after_inspection"]["finding_count"], 0)
        self.assertEqual(len(data["detectors_before"]), 1)
        self.assertEqual(len(data["detectors_after"]), 1)

    def test_analysis_can_omit_sanitized_text(self):
        data = analyze_text("plain").to_dict(include_text=False)
        self.assertNotIn("text", data["sanitized"])


class BatchTests(unittest.TestCase):
    def test_dry_run_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.txt"
            source.write_text("A\u200bB", encoding="utf-8")
            report = process_path(root, dry_run=True)
            self.assertEqual(report["file_count"], 1)
            self.assertEqual(report["changed_count"], 1)
            self.assertEqual(source.read_text(encoding="utf-8"), "A\u200bB")

    def test_output_dir_preserves_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            out = Path(tmp) / "out"
            nested = root / "docs"
            nested.mkdir(parents=True)
            (nested / "a.md").write_text("A\u200bB", encoding="utf-8")
            report = process_path(root, output_dir=out)
            self.assertEqual(report["changed_count"], 1)
            self.assertEqual((out / "docs" / "a.md").read_text(encoding="utf-8"), "AB")


class SarifTests(unittest.TestCase):
    def test_sarif_contains_location_and_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("line1\nA\u200bB", encoding="utf-8")
            sarif = scan_to_sarif(root)
            results = sarif["runs"][0]["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["ruleId"], "unicode/zero-width")
            region = results[0]["locations"][0]["physicalLocation"]["region"]
            self.assertEqual(region["startLine"], 2)


class ReportTests(unittest.TestCase):
    def test_html_report_is_standalone_and_escaped(self):
        analysis = analyze_text("<script>\u200b</script>").to_dict(include_text=False)
        html = render_analysis_html("<demo>", analysis)
        self.assertIn("&lt;demo&gt;", html)
        self.assertIn("TextUnmark", html)
        self.assertIn("Unicode findings", html)


if __name__ == "__main__":
    unittest.main()
