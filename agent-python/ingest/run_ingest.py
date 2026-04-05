"""
ingest/run_ingest.py

One-shot indexing pipeline. Run this whenever the codebase changes
(or schedule it as a cron/CI step).

Steps
-----
1. AST-parse every .py file → FileAnalysis objects
2. Populate SQLite symbol index
3. Build NetworkX dependency graph and save as GraphML
4. Embed all symbols into ChromaDB

Run:
    python -m ingest.run_ingest --source /path/to/repo
"""

import argparse
import os
import shutil
import sys

from ingest.ast_parser import parse_directory
from ingest.symbol_index import SymbolIndex
from ingest.dep_graph import DependencyGraph
from ingest.embedder import build_vector_store
from core.paths import get_dep_graph, get_symbol_db, get_persist_dir

_GLOBAL_EMBEDDING_FN = None

def run_ingest(source_dir: str, clean: bool = True) -> None:
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    VECTOR_DIR = get_persist_dir()
    print(f"\n{'='*55}")
    print(f" Code-Sentinel Indexer — source: {source_dir}")
    print(f"{'='*55}\n")

    if not os.path.exists(source_dir):
        print(f"ERROR: Source directory '{source_dir}' does not exist.")
        sys.exit(1)

    # Clean existing indexes
    if clean:
        for path in [GRAPH_PATH, SYMBOL_DB]:
            if os.path.exists(path):
                os.remove(path)
                print(f"Removed old index: {path}")
        if os.path.exists(VECTOR_DIR):
            try:
                shutil.rmtree(VECTOR_DIR)
                print(f"Removed old vector store: {VECTOR_DIR}")
            except OSError:
                from ingest.embedder import load_vector_store
                try:
                    db = load_vector_store(VECTOR_DIR)
                    db.delete_collection()
                except Exception as e:
                    print(f"Error occurred while deleting vector collection: {e}")

    # Step 1 — AST parse
    print("\n[1/4] Parsing source files with AST...")
    analyses = parse_directory(source_dir)

    total_functions = sum(len(a.functions) for a in analyses)
    total_classes   = sum(len(a.classes) for a in analyses)
    total_static    = sum(len(a.static_findings) for a in analyses)
    print(f"      {total_functions} functions, {total_classes} classes, "
          f"{total_static} static findings detected.")

    # Step 2 — Symbol index
    print("\n[2/4] Building symbol index (SQLite)...")
    symbol_index = SymbolIndex(db_path=SYMBOL_DB)
    symbol_index.clear()
    symbol_index.ingest(analyses)
    stats = symbol_index.stats()
    print(f"      {stats}")

    # Step 3 — Dependency graph
    print("\n[3/4] Building dependency graph (NetworkX)...")
    dep_graph = DependencyGraph()
    dep_graph.build(analyses, repo_root=source_dir)
    dep_graph.save(GRAPH_PATH)

    cycles = dep_graph.get_strongly_connected()
    if cycles:
        print(f"      WARNING: {len(cycles)} circular import cycle(s) detected.")
        for cycle in cycles[:3]:
            print(f"        → {' ↔ '.join(cycle)}")

    # Step 4 — Embed symbols
    print("\n[4/4] Embedding symbols into ChromaDB...")
    build_vector_store(analyses, persist_directory=VECTOR_DIR)

    print(f"\n{'='*55}")
    print(" Indexing complete. Summary:")
    print(f"   Source files  : {len(analyses)}")
    print(f"   Functions     : {total_functions}")
    print(f"   Classes       : {total_classes}")
    print(f"   Static issues : {total_static}")
    print(f"   Dep graph     : {GRAPH_PATH}")
    print(f"   Symbol DB     : {SYMBOL_DB}")
    print(f"   Vector store  : {VECTOR_DIR}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code-Sentinel indexer")
    parser.add_argument("--source", required=True, help="Path to the repo to index")
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip removing existing indexes (incremental update)"
    )
    args = parser.parse_args()
    run_ingest(args.source, clean=not args.no_clean)
