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

from rich.console import Console
from rich.panel import Panel
console = Console()

from ingest.ast_parser import parse_directory
from ingest.symbol_index import SymbolIndex
from ingest.dep_graph import DependencyGraph
from ingest.embedder import build_vector_store
from core.paths import get_dep_graph, get_symbol_db, get_persist_dir

def run_ingest(source_dir: str, clean: bool = True) -> None:
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    VECTOR_DIR = get_persist_dir()
    console.print("\n")
    console.print(Panel(f"[bold cyan]Code-Sentinel Indexer[/bold cyan]\nSource: [dim]{source_dir}[/dim]", border_style="blue"))

    if not os.path.exists(source_dir):
        console.print(f"[bold red]✖ ERROR:[/bold red] Source directory '{source_dir}' does not exist.")
        sys.exit(1)

    if clean:
        with console.status("[magenta]Cleaning existing indexes...[/magenta]"):
            for path in [GRAPH_PATH, SYMBOL_DB]:
                if os.path.exists(path):
                    os.remove(path)
            if os.path.exists(VECTOR_DIR):
                shutil.rmtree(VECTOR_DIR)

    with console.status("[cyan][1/4] Parsing source files with AST...[/cyan]", spinner="dots"):
        analyses = parse_directory(source_dir)
        total_functions = sum(len(a.functions) for a in analyses)
        total_classes   = sum(len(a.classes) for a in analyses)
        total_static    = sum(len(a.static_findings) for a in analyses)
    console.print(f"  [green]✔[/green] AST Parse: [bold]{total_functions}[/bold] functions, [bold]{total_classes}[/bold] classes, [bold]{total_static}[/bold] static findings.")

    with console.status("[cyan][2/4] Building SQLite symbol index...[/cyan]", spinner="dots"):
        symbol_index = SymbolIndex(db_path=SYMBOL_DB)
        symbol_index.clear()
        symbol_index.ingest(analyses)
        stats = symbol_index.stats()
    console.print(f"  [green]✔[/green] Symbol Index: {stats}")

    with console.status("[cyan][3/4] Building NetworkX dependency graph...[/cyan]", spinner="dots"):
        dep_graph = DependencyGraph()
        dep_graph.build(analyses, repo_root=source_dir)
        dep_graph.save(GRAPH_PATH)
        cycles = dep_graph.get_strongly_connected()
    
    console.print("  [green]✔[/green] Dependency Graph saved.")
    if cycles:
        console.print(f"    [bold yellow]⚠ WARNING:[/bold yellow] {len(cycles)} circular import cycle(s) detected.")

    console.print("[cyan][4/4] Embedding symbols into ChromaDB...[/cyan]")
    build_vector_store(analyses, persist_directory=VECTOR_DIR)
    console.print("  [green]✔[/green] Vector Embeddings complete.")

    console.print(Panel(
        f"[bold green]Indexing Complete[/bold green]\n"
        f"[dim]Files:[/dim] {len(analyses)}\n"
        f"[dim]Functions:[/dim] {total_functions}\n"
        f"[dim]Classes:[/dim] {total_classes}",
        border_style="green"
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code-Sentinel indexer")
    parser.add_argument("--source", required=True, help="Path to the repo to index")
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Skip removing existing indexes (incremental update)"
    )
    args = parser.parse_args()
    run_ingest(args.source, clean=not args.no_clean)
