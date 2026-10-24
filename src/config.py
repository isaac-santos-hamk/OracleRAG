import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_chroma_db_dir() -> str:
    """
    Resolves CHROMA_DB_DIR anchored at the project root while preferring an
    ASCII-safe path on Windows.
    """
    raw_dir = os.getenv("CHROMA_DB_DIR")
    if not raw_dir:
        abs_path = os.path.join(_PROJECT_ROOT, "data", "chroma")
    elif os.path.isabs(raw_dir):
        abs_path = raw_dir
    else:
        abs_path = os.path.abspath(os.path.join(_PROJECT_ROOT, raw_dir))

    try:
        rel_path = os.path.relpath(abs_path)
        if rel_path.isascii():
            return rel_path
    except ValueError:
        pass

    if os.name == "nt" and not abs_path.isascii() and os.path.exists(abs_path):
        try:
            import ctypes

            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.kernel32.GetShortPathNameW(abs_path, buf, 1024):
                if buf.value.isascii():
                    return buf.value
        except Exception:
            pass

    return abs_path


@dataclass
class Config:
    """Simple configuration object reading environment variables."""

    # Ollama settings
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name: str = os.getenv("MODEL_NAME", "llama3.2:3b")
    model_temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.0"))
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT", "180"))

    # RAG settings
    chroma_db_dir: str = _resolve_chroma_db_dir()
    rag_collection_name: str = os.getenv("RAG_COLLECTION_NAME", "oracle_rules")
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "1.2"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "6"))


# Instantiate global configuration object
config = Config()
