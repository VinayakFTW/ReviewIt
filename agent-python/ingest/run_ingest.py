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

def run_ingest(source_dir: str, clean: bool = True,output_callback=None,verbose=False) -> None:
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    VECTOR_DIR = get_persist_dir()
    if verbose == True:
        output_callback = output_callback or print
    else:
        output_callback = print
    output_callback(f" Code-Sentinel Indexer — source: {source_dir}")


    if not os.path.exists(source_dir):
        output_callback(f"ERROR: Source directory '{source_dir}' does not exist.")
        sys.exit(1)

    # Clean existing indexes
    if clean:
        for path in [GRAPH_PATH, SYMBOL_DB]:
            if os.path.exists(path):
                os.remove(path)
                output_callback(f"Removed old index: {path}")
        if os.path.exists(VECTOR_DIR):
            shutil.rmtree(VECTOR_DIR)
            output_callback(f"Removed old vector store: {VECTOR_DIR}")

    # Step 1 — AST parse
    output_callback("\n[1/4] Parsing source files with AST...")
    analyses = parse_directory(source_dir)

    total_functions = sum(len(a.functions) for a in analyses)
    total_classes   = sum(len(a.classes) for a in analyses)
    total_static    = sum(len(a.static_findings) for a in analyses)
    output_callback(f"      {total_functions} functions, {total_classes} classes, "
                    f"{total_static} static findings detected.")

    # Step 2 — Symbol index
    output_callback("\n[2/4] Building symbol index (SQLite)...")
    symbol_index = SymbolIndex(db_path=SYMBOL_DB)
    symbol_index.clear()
    symbol_index.ingest(analyses)
    stats = symbol_index.stats()
    output_callback(f"      {stats}")

    # Step 3 — Dependency graph
    output_callback("\n[3/4] Building dependency graph (NetworkX)...")
    dep_graph = DependencyGraph()
    dep_graph.build(analyses, repo_root=source_dir)
    dep_graph.save(GRAPH_PATH)

    cycles = dep_graph.get_strongly_connected()
    if cycles:
        output_callback(f"      WARNING: {len(cycles)} circular import cycle(s) detected.")
        for cycle in cycles[:3]:
            output_callback(f"        → {' ↔ '.join(cycle)}")

    # Step 4 — Embed symbols
    output_callback("\n[4/4] Embedding symbols into ChromaDB...")
    if verbose:
        build_vector_store(analyses, persist_directory=VECTOR_DIR,output_callback=output_callback,verbose=True)
    else:
        build_vector_store(analyses, persist_directory=VECTOR_DIR)

    output_callback(" Indexing complete. Summary:")
    output_callback(f"   Source files  : {len(analyses)}")
    output_callback(f"   Functions     : {total_functions}")
    output_callback(f"   Classes       : {total_classes}")
    output_callback(f"   Static issues : {total_static}")
    output_callback(f"   Dep graph     : {GRAPH_PATH}")
    output_callback(f"   Symbol DB     : {SYMBOL_DB}")
    output_callback(f"   Vector store  : {VECTOR_DIR}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code-Sentinel indexer")
    parser.add_argument("--source", required=True, help="Path to the repo to index")
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip removing existing indexes (incremental update)"
    )
    args = parser.parse_args()
    run_ingest(args.source, clean=not args.no_clean)
