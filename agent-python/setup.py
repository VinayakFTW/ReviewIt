"""This script only runs once when the user is running the sentinel for the first time. It sets up environment variables and starts the ingestion process, then launches the main CLI."""

import os

def setup_environment(source_dir: str):
    """
    Sets all path env vars. Must use get_app_dir(), NOT __file__.
    __file__ in a frozen exe = _internal/setup.pyc — wrong and read-only.
    """
    from core.paths import get_app_dir  # safe — paths.py uses sys.executable
    app_dir = get_app_dir()
    data_dir = os.path.join(app_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    os.environ["SOURCE_DIR"]        = source_dir
    os.environ["DATA_DIR"]          = data_dir
    os.environ["PERSIST_DIRECTORY"] = os.path.join(data_dir, "chroma_db")
    os.environ["SYMBOL_DB_PATH"]    = os.path.join(data_dir, "symbol_index.db")
    os.environ["DEP_GRAPH_PATH"]    = os.path.join(data_dir, "dep_graph.graphml")
    os.environ["DOCS_DIR"]          = os.path.join(source_dir, "docs")
    os.environ["WORKER_MODEL_NAME"] = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    os.environ["ORCHESTRATOR_MODEL_NAME"] = "Qwen/Qwen2.5-Coder-14B-Instruct"
    os.environ["EMBEDDING_MODEL_NAME"] = "jinaai/jina-code-embeddings-1.5b"
