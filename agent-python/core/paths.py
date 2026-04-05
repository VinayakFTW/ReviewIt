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
from huggingface_hub import snapshot_download

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
    if getattr(sys, "frozen", False):
        # Move writable data to %LOCALAPPDATA%\CodeSentinel\data
        user_data_dir = os.path.join(os.environ["LOCALAPPDATA"], "CodeSentinel", "data")
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir

    #dev mode fallback
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

def download_to_program_files():
    # Resolves to C:\Program Files\CodeSentinel when installed
    install_dir = get_app_dir() 
    local_dir = os.path.join(install_dir, "offline_model")
    
    os.makedirs(local_dir, exist_ok=True)
    
    snapshot_download(
        repo_id="jinaai/jina-code-embeddings-1.5b", 
        local_dir=local_dir,
        ignore_patterns=["*.msgpack", "*.h5", "rust_model.ot", "*.onnx"],
        local_dir_use_symlinks=False # Important for Windows portability
    )

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
            if "config.json" in os.listdir(bundled):
                print(f"[Paths] Using bundled offline model: {bundled}")
                return bundled
            else:
                print(f"[Paths] Found bundled offline_model at {bundled} but it's missing config.json. Trying to download offline_model.")
                try:
                    download_to_program_files()
                    if "config.json" in os.listdir(bundled):
                        return bundled
                    else:
                        return None
                except Exception as e:
                    print(f"Failed to download model': {e}")
                    return None

    # 2. Script / dev mode — check project root
    local = os.path.join(get_app_dir(), "offline_model")
    if os.path.exists(local) and "config.json" in os.listdir(local):
        print(f"[Paths] Using local offline model: {local}")
        return local

    else:
        print(f"[Paths] Found offline_model at {local} but it's missing config.json. Attempting to download offline_model.")
        try:
            download_to_program_files()
            return local
        except Exception as e:
           print(f"Failed to download model': {e}")
           return None

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