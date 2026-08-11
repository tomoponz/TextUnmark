from pathlib import Path
import tempfile
import unittest

from textunmark.config import load_config


class ConfigTests(unittest.TestCase):
    def test_defaults_without_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path.cwd()
            try:
                import os
                os.chdir(tmp)
                settings = load_config()
            finally:
                os.chdir(original)
        self.assertEqual(settings.profile, "conservative")
        self.assertEqual(settings.normalization, "NFC")
        self.assertIsNone(settings.source)

    def test_explicit_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.toml"
            path.write_text(
                '[textunmark]\nprofile = "strict"\nnormalization = "NFKC"\n'
                'detectors = ["unicode-artifact"]\nextensions = [".md", ".py"]\n',
                encoding="utf-8",
            )
            settings = load_config(str(path))
            self.assertEqual(settings.profile, "strict")
            self.assertEqual(settings.normalization, "NFKC")
            self.assertEqual(settings.detectors, ("unicode-artifact",))
            self.assertEqual(settings.extensions, (".md", ".py"))

    def test_rejects_invalid_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text('[textunmark]\nprofile = "destroy-everything"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(str(path))


if __name__ == "__main__":
    unittest.main()
