"""Lab configuration. Every value can be overridden with an environment variable."""

import os
from pathlib import Path

from dotenv import load_dotenv

LAB_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = LAB_DIR / "common" / "assets"
DATA_DIR = LAB_DIR / ".data"

# lab/.env is written by exercise 00. The repo-root .env is for local development.
load_dotenv(LAB_DIR / ".env")
load_dotenv(LAB_DIR.parent / ".env")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIMS = 384

SCYLLA_HOST = os.getenv("SCYLLA_HOST", "127.0.0.1")
SCYLLA_DC = os.getenv("SCYLLA_DC", "datacenter1")
KEYSPACE = os.getenv("KEYSPACE", "plushie_shop")

CUSTOMERS = ["alice", "bob"]


def google_api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Run exercise 00 first (it asks for your key).")
    return key


def mem0_config(**overrides) -> dict:
    """mem0 config: Gemini for fact extraction, bge-small on CPU for embeddings, ScyllaDB for storage."""
    DATA_DIR.mkdir(exist_ok=True)
    config = {
        "llm": {
            "provider": "gemini",
            "config": {"model": GEMINI_MODEL, "temperature": 0.1, "api_key": google_api_key()},
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": EMBEDDING_MODEL, "embedding_dims": EMBEDDING_DIMS},
        },
        "vector_store": {
            "provider": "scylladb",
            "config": {
                "contact_points": [SCYLLA_HOST],
                "datacenter": SCYLLA_DC,
                "keyspace": KEYSPACE,
                "collection_name": "memories",
                "embedding_model_dims": EMBEDDING_DIMS,
            },
        },
        # mem0 keeps the change history of each memory in a local SQLite file, not in ScyllaDB.
        "history_db_path": str(DATA_DIR / "history.db"),
    }
    config.update(overrides)
    return config
