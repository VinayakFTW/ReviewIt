"""
main.py — Code-Sentinel entry point.
"""

import os

from ingest.dep_graph import DependencyGraph
from ingest.symbol_index import SymbolIndex
from ingest.embedder import load_vector_store
from retrieval.hybrid_retriever import HybridRetriever
from dotenv import load_dotenv

from core.paths import (
    get_source_dir, get_persist_dir, get_symbol_db,
    get_dep_graph, get_docs_dir,get_env_path
)
load_dotenv(dotenv_path=get_env_path())

def load_shared_resources():
    VECTOR_DIR = get_persist_dir()
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    print("[Init] Loading vector store...")
    vector_store = load_vector_store(VECTOR_DIR)

    print("[Init] Loading dependency graph...")
    dep_graph = DependencyGraph()
    if os.path.exists(GRAPH_PATH):
        dep_graph.load(GRAPH_PATH)
    else:
        print(f"  WARNING: No dep graph at '{GRAPH_PATH}'. Run re-index first.")

    print("[Init] Loading symbol index...")
    symbol_index = SymbolIndex(db_path=SYMBOL_DB)
    print(f"  Symbols: {symbol_index.stats()}")

    retriever = HybridRetriever(
        vector_store=vector_store,
        dep_graph=dep_graph,
        symbol_index=symbol_index,
        vector_k=8,
        dep_hops=1,
        max_total=20,
    )
    print("[Init] Hybrid retriever ready.\n")
    return retriever
