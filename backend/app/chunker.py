from dataclasses import dataclass

from .config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS
from .pdf_loader import PageText


@dataclass
class Chunk:
    id: str
    source: str
    page_number: int
    chunk_index: int
    text: str
    word_count: int


def chunk_page(page: PageText, chunk_index_offset: int) -> list[Chunk]:
    words = page.text.split()
    if not words:
        return []

    chunks = []
    start = 0
    idx = chunk_index_offset
    step = max(CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS, 1)

    while start < len(words):
        end = min(start + CHUNK_SIZE_WORDS, len(words))
        chunk_words = words[start:end]
        text = " ".join(chunk_words)
        chunk_id = f"{page.source}::p{page.page_number}::c{idx}"
        chunks.append(
            Chunk(
                id=chunk_id,
                source=page.source,
                page_number=page.page_number,
                chunk_index=idx,
                text=text,
                word_count=len(chunk_words),
            )
        )
        idx += 1
        if end == len(words):
            break
        start += step

    return chunks


def chunk_document(pages: list[PageText]) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    running_index = 0
    for page in pages:
        page_chunks = chunk_page(page, running_index)
        all_chunks.extend(page_chunks)
        running_index += len(page_chunks)
    return all_chunks
