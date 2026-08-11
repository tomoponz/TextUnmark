from pathlib import Path
import tempfile
import unittest

from textunmark.batch import process_path


class BatchBackupTests(unittest.TestCase):
    def test_in_place_backup_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("A\u200bB", encoding="utf-8")
            report = process_path(path, in_place=True, backup_suffix=".bak")
            self.assertEqual(path.read_text(encoding="utf-8"), "AB")
            backup = Path(str(path) + ".bak")
            self.assertEqual(backup.read_text(encoding="utf-8"), "A\u200bB")
            self.assertEqual(report["items"][0]["backup_path"], str(backup))

    def test_backup_requires_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("A\u200bB", encoding="utf-8")
            with self.assertRaises(ValueError):
                process_path(path, backup_suffix=".bak")


if __name__ == "__main__":
    unittest.main()
