import os
import sys
from core.paths import get_app_dir, get_env_path
from setup import *
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()
env_path = get_env_path()
load_dotenv(dotenv_path=env_path)

def main():
    console.print(Panel.fit(
        "[bold cyan]Code-Sentinel[/bold cyan] - [dim]Local Code Intelligence[/dim]", 
        border_style="cyan"
    ))
    console.print("[dim]Note: Please ensure Ollama is running in the background.[/dim]\n")
    
    with console.status("[magenta]Checking Ollama status...[/magenta]", spinner="dots"):
        if not is_ollama_running():
            bootstrap_dependencies()
            console.print("[bold red]✖ Error: Ollama is not responding.[/bold red] Attempting to Start Ollama...")
            sys.exit(1)
    console.print("[bold green]✔ Ollama is running.[/bold green]\n")
    bootstrap_dependencies()
    app_dir = get_app_dir()
    env_path = get_env_path()
    load_dotenv(dotenv_path=env_path)

    while True:
        current_repo = os.environ.get("SOURCE_DIR")
        
        if current_repo:
            console.print(f"[cyan]Current repository:[/cyan] {current_repo}")
            repo_path = Prompt.ask("[bold yellow]Enter absolute path to codebase[/bold yellow] (Press Enter to keep current, or 'q' to quit)", default=current_repo)
        else:
            repo_path = Prompt.ask("[bold yellow]Enter absolute path to codebase[/bold yellow] (or 'q' to quit)")
        
        if repo_path.lower() in ('q', 'quit', 'exit'):
            console.print("[red]Exiting Code-Sentinel.[/red]")
            sys.exit(0)
            
        repo_path = repo_path.strip('"').strip("'")

        if not os.path.exists(repo_path):
            console.print(f"[bold red]✖ Error:[/bold red] The path '{repo_path}' does not exist.\n")
            continue
            
        is_configured = (
            os.environ.get("SOURCE_DIR") == repo_path and
            os.environ.get("PERSIST_DIRECTORY") and 
            os.environ.get("SYMBOL_DB_PATH") and 
            os.environ.get("DEP_GRAPH_PATH")
        )

        if not is_configured:
            with console.status("[cyan]Setting up environment...[/cyan]", spinner="arc"):
                if not os.path.exists(env_path):
                    open(env_path, 'a').close()

                # bootstrap_dependencies()
                setup_environment(repo_path)

                from dotenv import set_key
                for key in ["SOURCE_DIR", "DATA_DIR", "PERSIST_DIRECTORY", "SYMBOL_DB_PATH", "DEP_GRAPH_PATH", "DOCS_DIR"]:
                    set_key(env_path, key, os.environ[key])

                load_dotenv(dotenv_path=env_path, override=True)
        else:
            console.print("[green]✔ Environment already configured for this repository.[/green]")

        vector_dir = os.environ.get("PERSIST_DIRECTORY")
        symbol_db = os.environ.get("SYMBOL_DB_PATH")
        dep_graph = os.environ.get("DEP_GRAPH_PATH")

        needs_ingestion = True
        if os.path.exists(vector_dir) and os.path.exists(symbol_db) and os.path.exists(dep_graph):
            console.print("\n[cyan]ℹ Found existing indexes in the local directory.[/cyan]")
            choice = Prompt.ask("Do you want to re-index the repository?", choices=["y", "n"], default="n")
            if choice != 'y':
                needs_ingestion = False

        if needs_ingestion:
            console.print("\n[bold cyan]Starting repository ingestion...[/bold cyan]")
            from ingest.run_ingest import run_ingest
            try:
                run_ingest(repo_path, clean=True)
                console.print("\n[bold green]✔ Ingestion complete![/bold green]")
            except Exception as e:
                console.print(f"\n[bold red]✖ Ingestion failed:[/bold red] {e}")
                continue
        else:
            console.print("\n[dim]Skipping ingestion. Using existing indexes.[/dim]")
            
        while True:
            menu = Table(show_header=False, box=None)
            menu.add_row("[bold cyan][1][/bold cyan]", "Start Code-Sentinel CLI")
            menu.add_row("[bold cyan][2][/bold cyan]", "Change Repository")
            menu.add_row("[bold red][3][/bold red]", "Exit Application")
            console.print(Panel(menu, title="Startup Menu", border_style="blue", expand=False))
            
            choice = Prompt.ask("[bold yellow]Choice[/bold yellow]", choices=["1", "2", "3"])
            
            if choice == "1":
                from main import main as inititate_sentinel
                try:
                    inititate_sentinel()
                except Exception as e:
                    console.print(f"[bold red]✖ Error running CLI:[/bold red] {e}")
            elif choice == "2":
                console.print("\n[cyan]Changing repository...[/cyan]")
                break 
            elif choice == "3":
                console.print("[red]Exiting Code-Sentinel.[/red]")
                sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        input("Press Enter to close...")