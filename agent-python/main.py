"""
main.py — Code-Sentinel entry point.
"""

import os
import sys
import time
import gc

from core.model_manager import check_ollama_running, warmup_model, ORCHESTRATOR_MODEL
from ingest.dep_graph import DependencyGraph
from ingest.symbol_index import SymbolIndex
from ingest.embedder import load_vector_store
from retrieval.hybrid_retriever import HybridRetriever
from pipelines.qa import QAPipeline
from pipelines.review import ReviewPipeline
from pipelines.docs import DocsPipeline
from dotenv import load_dotenv

from core.paths import (
    get_source_dir, get_persist_dir, get_symbol_db,
    get_dep_graph, get_docs_dir,get_env_path
)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

load_dotenv(dotenv_path=get_env_path())

console = Console()

def load_shared_resources():
    VECTOR_DIR = get_persist_dir()
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    
    with console.status("[bold cyan]Loading Sentinel Cores...[/bold cyan]", spinner="arc"):
        vector_store = load_vector_store(VECTOR_DIR)
        
        dep_graph = DependencyGraph()
        if os.path.exists(GRAPH_PATH):
            dep_graph.load(GRAPH_PATH)
            
        symbol_index = SymbolIndex(db_path=SYMBOL_DB)
        stats = symbol_index.stats()
        
        retriever = HybridRetriever(
            vector_store=vector_store, dep_graph=dep_graph, symbol_index=symbol_index,
            vector_k=8, dep_hops=1, max_total=20,
        )
    console.print(f"[green]✔[/green] Engines Online. Indexed: {stats['files']} files, {stats['functions']} functions.")
    return retriever


def main():

    SOURCE_DIR = get_source_dir()
    VECTOR_DIR = get_persist_dir()
    GRAPH_PATH = get_dep_graph()
    SYMBOL_DB  = get_symbol_db()
    DOCS_DIR   = get_docs_dir(SOURCE_DIR)

    console.print(Panel.fit(
        "[bold cyan]Code-Sentinel v2 (Hybrid)[/bold cyan]\n"
        "[dim]AST + DepGraph + Vector + 10 Specialist Workers[/dim]",
        border_style="cyan"
    ))

    if not check_ollama_running():
        print("ERROR: Ollama is not running. Start with: ollama serve")
        sys.exit(1)

    if not os.path.exists(VECTOR_DIR):
        print(f"ERROR: No vector store. Run:\n  python -m ingest.run_ingest --source {SOURCE_DIR}")
        sys.exit(1)

    retriever = load_shared_resources()

    qa_pipeline     = QAPipeline(retriever)
    review_pipeline = ReviewPipeline(
        retriever=retriever, symbol_index=retriever.si, source_dir=SOURCE_DIR)
    docs_pipeline   = DocsPipeline(
        retriever=retriever, source_dir=SOURCE_DIR, docs_dir=DOCS_DIR)

    # warmup_model(ORCHESTRATOR_MODEL, keep_alive_seconds=1800)

    while True:
        menu = Table(show_header=False, box=None)
        menu.add_row("[bold cyan][1][/bold cyan]", "Q&A", "[dim]Ask about the code[/dim]")
        menu.add_row("[bold cyan][2][/bold cyan]", "Review", "[dim]Full codebase audit[/dim]")
        menu.add_row("[bold cyan][3][/bold cyan]", "Docs", "[dim]Update documentation[/dim]")
        menu.add_row("[bold cyan][4][/bold cyan]", "Re-index", "[dim]Re-run ingest[/dim]")
        menu.add_row("[bold red][q][/bold red]", "Quit", "")
        
        console.print(Panel(menu, title="Main Menu", border_style="blue", expand=False))

        try:
            choice = Prompt.ask("[bold yellow]Action[/bold yellow]", choices=["1", "2", "3", "4", "q", "quit", "exit"])
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Exiting.[/red]")
            break

        if choice in ("q", "quit", "exit"):
            break
        elif choice == "1":
            qa_pipeline.interactive_loop()
        elif choice == "2":
            scope = Prompt.ask("Scope", default="Full codebase audit")
            review_pipeline.run(user_request=scope)
        elif choice == "3":
            mode = Prompt.ask("Full [f] or incremental [i]?", choices=["f", "i"])
            if mode == "f":
                docs_pipeline.run_full()
            else:
                since = Prompt.ask("Since ref (default HEAD~1):", default="HEAD~1")
                docs_pipeline.run_incremental(since=since)
        elif choice == "4":
            src = Prompt.ask(f"Source dir (default {SOURCE_DIR}):", default=SOURCE_DIR)
            from ingest.run_ingest import run_ingest
            print("Dropping old references...")
            if retriever and hasattr(retriever, 'si'):
                try:
                    retriever.si.close()
                except Exception:
                    pass
                try:
                    if hasattr(retriever, 'vector_store'):
                        if hasattr(retriever.vector_store, '_client'):
                            del retriever.vector_store._client
                        del retriever.vector_store
                except:
                    pass
                retriever.vs.delete_collection()
                retriever = None
                qa_pipeline.retriever = None
                review_pipeline.retriever = None
                review_pipeline.symbol_index = None
                docs_pipeline.retriever = None
                from torch.cuda import is_available,empty_cache
                if is_available():
                    empty_cache()
                gc.collect()
                time.sleep(3)
            print("Re-indexing...")
            run_ingest(src, clean=True)
            retriever = load_shared_resources()
            qa_pipeline.retriever = retriever
            review_pipeline.retriever = retriever
            review_pipeline.symbol_index = retriever.si
            docs_pipeline.retriever = retriever
        else:
            console.print("[red]Invalid choice.[/red]")

if __name__ == "__main__":
    main()
