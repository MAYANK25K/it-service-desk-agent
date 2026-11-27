from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from agents.config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, OLLAMA_BASE_URL


def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )