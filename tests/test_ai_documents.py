import unittest
from io import BytesIO

from docx import Document

from ai.documents import MAX_FILE_BYTES, extract_example_text


class TestAIExampleDocuments(unittest.TestCase):
    def test_extracts_txt(self) -> None:
        self.assertEqual(extract_example_text("exemplo.txt", "Olá".encode()), "Olá")

    def test_extracts_docx(self) -> None:
        document = Document()
        document.add_paragraph("Objeto de exemplo")
        content = BytesIO()
        document.save(content)
        self.assertIn("Objeto de exemplo", extract_example_text("exemplo.docx", content.getvalue()))

    def test_rejects_unsupported_or_oversized_file(self) -> None:
        with self.assertRaises(ValueError):
            extract_example_text("exemplo.exe", b"texto")
        with self.assertRaises(ValueError):
            extract_example_text("exemplo.txt", b"x" * (MAX_FILE_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
