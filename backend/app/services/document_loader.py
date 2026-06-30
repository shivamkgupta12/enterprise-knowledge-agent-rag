from pathlib import Path
from typing import TypedDict
from pypdf import PdfReader
from docx import Document


class PageText(TypedDict):
    page: int
    text: str


def load_pdf(path: Path) -> list[PageText]:
    reader = PdfReader(str(path))
    pages: list[PageText] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()

        if text:
            pages.append(
                {
                    "page": index,
                    "text": text,
                }
            )

    return pages


def load_docx(path: Path) -> list[PageText]:
    doc = Document(str(path))
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    return [
        {
            "page": 1,
            "text": text,
        }
    ]


def load_text(path: Path) -> list[PageText]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    return [
        {
            "page": 1,
            "text": text,
        }
    ]


def load_document(path: Path) -> list[PageText]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(path)

    if suffix == ".docx":
        return load_docx(path)

    if suffix in {".txt", ".md", ".csv"}:
        return load_text(path)

    raise ValueError(f"Unsupported file type: {suffix}")
