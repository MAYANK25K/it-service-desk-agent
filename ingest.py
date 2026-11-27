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


def print_summary(chunks: list[Document]) -> None:
    counts = Counter(c.metadata["source"] for c in chunks)
    for source, count in sorted(counts.items()):
        print(f"{source}: {count} chunks")
    print(f"Total: {len(chunks)} chunks")


def main() -> None:
    chunks = load_chunks(DATA_DIR)
    print_summary(chunks)

    store = get_vector_store()
    store.add_documents(chunks)
    print(f"Stored {len(chunks)} chunks in ChromaDB")


if __name__ == "__main__":
    main()
