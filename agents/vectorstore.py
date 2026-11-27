from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from agents.config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, OLLAMA_BASE_URL


class PrefixedEmbeddings(Embeddings):
    def __init__(self, base: Embeddings, document_prefix: str, query_prefix: str):
        self.base = base
        self.document_prefix = document_prefix
        self.query_prefix = query_prefix

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.base.embed_documents([self.document_prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self.base.embed_query(self.query_prefix + text)


def get_embeddings() -> Embeddings:
    base = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    if "nomic" in EMBED_MODEL:
        return PrefixedEmbeddings(base, "search_document: ", "search_query: ")
    return base


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )