from functools import lru_cache
from typing import Optional

from langchain_core.documents import Document

from agents.config import RETRIEVAL_TOP_K
from agents.vectorstore import get_vector_store


@lru_cache(maxsize=1)
def _store():
    return get_vector_store()


def build_filter(
    doc_type: Optional[str] = None, source: Optional[str] = None
) -> Optional[dict]:
    conditions = []
    if doc_type:
        conditions.append({"doc_type": doc_type})
    if source:
        conditions.append({"source": source})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def to_evidence(doc: Document, distance: float) -> dict:
    meta = doc.metadata
    return {
        "content": doc.page_content,
        "source": meta.get("source", "unknown"),
        "doc_id": meta.get("doc_id", ""),
        "doc_type": meta.get("doc_type", ""),
        "section": meta.get("subsection") or meta.get("section", ""),
        "section_ref": meta.get("section_ref", ""),
        "distance": float(distance),
    }


def retrieve(
    query: str, k: int = RETRIEVAL_TOP_K, filters: Optional[dict] = None
) -> list[dict]:
    results = _store().similarity_search_with_score(query, k=k, filter=filters)
    return [to_evidence(doc, distance) for doc, distance in results]