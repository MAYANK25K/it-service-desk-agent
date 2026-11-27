import hashlib
import re
from collections import Counter
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from agents.config import DATA_DIR
from agents.vectorstore import get_vector_store

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

HEADERS_TO_SPLIT_ON = [
    ("#", "title"),
    ("##", "section"),
    ("###", "subsection"),
]

DOC_TYPES = {
    "RUN": "runbook",
    "POL": "policy",
    "SOP": "sop",
    "KB": "knowledge_base",
}

DOC_ID_PATTERN = re.compile(r"Document ID:\s*([A-Z]+)-(\d+)")
SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)")


def read_document_info(text: str) -> tuple[str, str]:
    match = DOC_ID_PATTERN.search(text)
    if not match:
        return "UNKNOWN", "general"
    prefix, number = match.groups()
    return f"{prefix}-{number}", DOC_TYPES.get(prefix, "general")


def section_reference(metadata: dict) -> str:
    heading = metadata.get("subsection") or metadata.get("section") or ""
    match = SECTION_NUMBER_PATTERN.match(heading)
    return match.group(1) if match else "header"


def has_body(chunk: Document) -> bool:
    return any(
        line.strip() and not line.lstrip().startswith("#")
        for line in chunk.page_content.splitlines()
    )


def split_markdown_file(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8")
    doc_id, doc_type = read_document_info(text)

    header_splitter = MarkdownHeaderTextSplitter(
        HEADERS_TO_SPLIT_ON, strip_headers=False
    )
    sections = header_splitter.split_text(text)

    chunker = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = [c for c in chunker.split_documents(sections) if has_body(c)]

    for chunk in chunks:
        chunk.metadata["source"] = path.name
        chunk.metadata["doc_id"] = doc_id
        chunk.metadata["doc_type"] = doc_type
        chunk.metadata["section"] = chunk.metadata.get("section", "Document header")
        chunk.metadata["section_ref"] = section_reference(chunk.metadata)
    return chunks


def load_chunks(data_dir: Path) -> list[Document]:
    files = sorted(data_dir.glob("*.md"))
    if not files:
        raise SystemExit(f"No .md files found in {data_dir}")
    chunks = []
    for path in files:
        chunks.extend(split_markdown_file(path))
    return chunks


def make_chunk_id(chunk: Document, position: int) -> str:
    digest = hashlib.sha1(chunk.page_content.encode("utf-8")).hexdigest()[:12]
    source = chunk.metadata["source"]
    section_ref = chunk.metadata["section_ref"]
    return f"{source}::{section_ref}::{position}::{digest}"


def assign_chunk_ids(chunks: list[Document]) -> list[Document]:
    positions: dict[tuple[str, str], int] = {}
    for chunk in chunks:
        key = (chunk.metadata["source"], chunk.metadata["section_ref"])
        position = positions.get(key, 0)
        positions[key] = position + 1
        chunk.metadata["chunk_id"] = make_chunk_id(chunk, position)
    return chunks


def sync_chunks(store, chunks: list[Document]) -> tuple[int, int, int]:
    current_ids = {c.metadata["chunk_id"] for c in chunks}
    existing_ids = set(store.get()["ids"])

    new_chunks = [c for c in chunks if c.metadata["chunk_id"] not in existing_ids]
    stale_ids = sorted(existing_ids - current_ids)

    if new_chunks:
        store.add_documents(
            new_chunks, ids=[c.metadata["chunk_id"] for c in new_chunks]
        )
    if stale_ids:
        store.delete(ids=stale_ids)
    return len(new_chunks), len(chunks) - len(new_chunks), len(stale_ids)


def print_summary(chunks: list[Document]) -> None:
    counts = Counter(c.metadata["source"] for c in chunks)
    for source, count in sorted(counts.items()):
        print(f"{source}: {count} chunks")
    print(f"Total: {len(chunks)} chunks")


def main() -> None:
    chunks = assign_chunk_ids(load_chunks(DATA_DIR))
    print_summary(chunks)

    store = get_vector_store()
    added, unchanged, removed = sync_chunks(store, chunks)
    print(f"Added: {added} | Unchanged: {unchanged} | Removed: {removed}")


if __name__ == "__main__":
    main()