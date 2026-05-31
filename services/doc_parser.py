from __future__ import annotations

from pathlib import Path
from docx import Document


class DocParser:
    @staticmethod
    def parse(file_path: str) -> list[str]:
        ext = Path(file_path).suffix.lower()
        if ext == ".docx":
            return DocParser._parse_docx(file_path)
        elif ext == ".txt":
            return DocParser._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    @staticmethod
    def _parse_docx(file_path: str) -> list[str]:
        doc = Document(file_path)
        sentences: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Split each paragraph into sentences
                from utils.text_utils import split_sentences
                sentences.extend(split_sentences(text))
        return sentences

    @staticmethod
    def _parse_txt(file_path: str) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        from utils.text_utils import split_sentences
        return split_sentences(text)
