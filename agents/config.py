import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma"
CHECKPOINT_DB = STORAGE_DIR / "checkpoints.sqlite"
OPS_DB = STORAGE_DIR / "ops.db"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "it_service_desk")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "4"))

STORAGE_DIR.mkdir(parents=True, exist_ok=True)