import tempfile
import unittest
from pathlib import Path

from documents_lib import read_invoice


class DocumentsTests(unittest.TestCase):
    def setUp(self) -> None:
        # Use the test process's workspace, not platform-specific temp locations.
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / "invoices"
        self.root.mkdir()
        (self.root / "one.txt").write_text("invoice 1", encoding="utf-8")
        (self.folder / "secret.txt").write_text("private", encoding="utf-8")

    def test_invoice(self) -> None:
        self.assertEqual(read_invoice(str(self.root), "one.txt"), "invoice 1")

    def test_nested_invoice(self) -> None:
        (self.root / "archive").mkdir()
        (self.root / "archive/two.txt").write_text("invoice 2", encoding="utf-8")
        self.assertEqual(read_invoice(str(self.root), "archive/two.txt"), "invoice 2")

    def test_missing_invoice(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_invoice(str(self.root), "missing.txt")

    def test_path_traversal(self) -> None:
        for filename in ("../secret.txt", str(self.folder / "secret.txt")):
            with self.assertRaises(ValueError):
                read_invoice(str(self.root), filename)

    def test_normalized_inside_path(self) -> None:
        self.assertEqual(read_invoice(str(self.root), "./one.txt"), "invoice 1")
