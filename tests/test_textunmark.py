import unittest

from textunmark.compare import compare_texts
from textunmark.sanitize import sanitize_text
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


if __name__ == "__main__":
    unittest.main()
