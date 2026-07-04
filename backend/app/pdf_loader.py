from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class PageText:
    source: str
    page_number: int
    text: str


def list_pdfs(data_dir: Path) -> list[Path]:
    return sorted(data_dir.glob("*.pdf"))


def load_pdf_pages(pdf_path: Path) -> list[PageText]:
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(PageText(source=pdf_path.name, page_number=i, text=text))
    return pages
