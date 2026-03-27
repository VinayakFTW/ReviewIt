"""
core/paths.py
Single source of truth for all runtime paths.

Key rule: never use __file__ for writable paths.
  - __file__ in a frozen exe points to sys._MEIPASS (_internal/) — read-only bundle dir.
  - sys.executable always points to the exe itself, so dirname() is always writable.
  - sys._MEIPASS is where PyInstaller puts --add-data files (version-agnostic).
"""
import os
import sys
from rich import print

def get_app_dir() -> str:
    """
    The directory that owns the process. Always writable.
      - Frozen exe  : dirname(sys.executable)  → dist/CodeSentinel/
      - Script mode : project root (two levels up from core/paths.py)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # core/paths.py → core/ → project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_meipass_dir() -> str:
    """
    Where PyInstaller unpacks --add-data files.
      - PyInstaller 6+ : dist/CodeSentinel/_internal/   (sys._MEIPASS)
      - PyInstaller 5  : dist/CodeSentinel/              (sys._MEIPASS == exe dir)
      - Script mode    : project root (same as get_app_dir)
    Never hardcode _internal/ — always read sys._MEIPASS.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return get_app_dir()


def get_env_path() -> str:
    """
    .env file lives next to the exe (or project root in dev).
    Never os.path.dirname(__file__) — that resolves to _internal/ when frozen.
    """
    return os.path.join(get_app_dir(), ".env")


def get_data_dir() -> str:
    """
    data/ directory — writable, next to the exe.
    Reads DATA_DIR env var first (set by cli.py after user picks a repo).
    """
    val = os.environ.get("DATA_DIR")
    if val:
        return val
    return os.path.join(get_app_dir(), "data")


def get_persist_dir() -> str:
    return os.environ.get("PERSIST_DIRECTORY") or \
           os.path.join(get_data_dir(), "chroma_db")


def get_symbol_db() -> str:
    return os.environ.get("SYMBOL_DB_PATH") or \
           os.path.join(get_data_dir(), "symbol_index.db")


def get_dep_graph() -> str:
    return os.environ.get("DEP_GRAPH_PATH") or \
           os.path.join(get_data_dir(), "dep_graph.graphml")


def get_embedding_model() -> str:
    """
    Priority:
    1. offline_model/ bundled via --add-data  (frozen exe, sys._MEIPASS)
    2. offline_model/ in project root          (dev / script mode)
    3. EMBEDDING_MODEL_NAME env var            (HuggingFace download fallback)
    4. hardcoded HuggingFace default           (last resort)
    """
    # 1. Frozen exe — check the bundle first, always
    if getattr(sys, "frozen", False):
        bundled = os.path.join(get_meipass_dir(), "offline_model")
        if os.path.exists(bundled):
            print(f"[Paths] Using bundled offline model: {bundled}")
            return bundled

    # 2. Script / dev mode — check project root
    local = os.path.join(get_app_dir(), "offline_model")
    if os.path.exists(local):
        print(f"[Paths] Using local offline model: {local}")
        return local

    # 3. Env var — treated as a HuggingFace model ID for download
    env_val = os.environ.get("EMBEDDING_MODEL_NAME")
    if env_val:
        print(f"[Paths] No local model found. Falling back to: {env_val}")
        return env_val

    # 4. Hardcoded last resort
    print("[Paths] WARNING: No local model and no EMBEDDING_MODEL_NAME set. Using default.")
    return "jinaai/jina-code-embeddings-1.5b"

def get_docs_dir(source_dir: str = None) -> str:
    return os.environ.get("DOCS_DIR") or \
           os.path.join(source_dir or get_app_dir(), "docs")


def get_source_dir() -> str:
    val = os.environ.get("SOURCE_DIR")
    if not val:
        raise EnvironmentError(
            "SOURCE_DIR is not set. Run cli.py to configure a repository first."
        )
    return val