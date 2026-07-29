from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.i18n import LANGUAGES, _TEXT


class LegalDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_every_interface_language_has_all_legal_documents(self):
        for language in LANGUAGES:
            for document in ("LICENSE", "TERMS", "PRIVACY", "EULA"):
                path = self.root / "licenses" / f"{document}-{language}.txt"
                self.assertTrue(path.is_file(), path)
                self.assertGreater(len(path.read_text(encoding="utf-8")), 300)

    def test_every_language_has_legal_interface_labels(self):
        required = {
            "about_license_summary",
            "license_button",
            "terms_button",
            "privacy_button",
            "close",
            "legal_file_error",
        }
        for language, texts in _TEXT.items():
            self.assertTrue(required <= set(texts), language)

    def test_legal_builder_combines_all_three_documents(self):
        from tools.build_legal_files import LICENSES, main

        with tempfile.TemporaryDirectory():
            main()
        for language in LANGUAGES:
            eula = (LICENSES / f"EULA-{language}.txt").read_text(encoding="utf-8")
            for document in ("LICENSE", "TERMS", "PRIVACY"):
                first_line = (
                    LICENSES / f"{document}-{language}.txt"
                ).read_text(encoding="utf-8").splitlines()[0]
                self.assertIn(first_line, eula)


if __name__ == "__main__":
    unittest.main()
