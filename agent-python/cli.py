import os
import sys
from core.paths import get_app_dir, get_env_path
from setup import *
from dotenv import load_dotenv
env_path = get_env_path()
load_dotenv(dotenv_path=env_path)
import time


def main():
    print("========================================================")
    print("           Code-Sentinel - Code Review Assistant             ")
    print("========================================================")
    print("Note: Please ensure Ollama is running in the background.\n")
    
    print("Checking Ollama status...")
    bootstrap_dependencies()
    
    app_dir = get_app_dir()
    env_path = get_env_path()
    
    # Load existing .env if present
    load_dotenv(dotenv_path=env_path)

    while True:
        current_repo = os.environ.get("SOURCE_DIR")
        
        if current_repo:
            print(f"Current repository: {current_repo}")
            repo_path = input("Enter the absolute path to your codebase (Press Enter to keep current, or 'q' to quit): ").strip()
            if not repo_path:
                repo_path = current_repo
        else:
            repo_path = input("Enter the absolute path to your codebase (or 'q' to quit): ").strip()
        
        if repo_path.lower() in ('q', 'quit', 'exit'):
            print("Exiting Code-Sentinel.")
            sys.exit(0)
            
        repo_path = repo_path.strip('"').strip("'")

        if not os.path.exists(repo_path):
            print(f"Error: The path '{repo_path}' does not exist. Please try again.\n")
            continue
            
        # Check if environment is already configured for THIS repo
        is_configured = (
            os.environ.get("SOURCE_DIR") == repo_path and
            os.environ.get("PERSIST_DIRECTORY") and 
            os.environ.get("SYMBOL_DB_PATH") and 
            os.environ.get("DEP_GRAPH_PATH")
        )

        if not is_configured:
            print("Setting up environment...")
            if not os.path.exists(env_path):
                open(env_path, 'a').close()

            setup_environment(repo_path)      # sets all os.environ keys cleanly

            # Write back to .env for persistence across restarts
            from dotenv import set_key
            for key in ["SOURCE_DIR", "DATA_DIR", "PERSIST_DIRECTORY",
                        "SYMBOL_DB_PATH", "DEP_GRAPH_PATH", "DOCS_DIR"]:
                set_key(env_path, key, os.environ[key])

            load_dotenv(dotenv_path=env_path, override=True)
            
        else:
            print("Environment and dependencies are already set up for this repository.")

        # Check for existing indexes
        vector_dir = os.environ.get("PERSIST_DIRECTORY")
        symbol_db = os.environ.get("SYMBOL_DB_PATH")
        dep_graph = os.environ.get("DEP_GRAPH_PATH")

        needs_ingestion = True
        if os.path.exists(vector_dir) and os.path.exists(symbol_db) and os.path.exists(dep_graph):
            print("\n[INFO] Found existing vector store, dependency graph, and symbol index in the local directory.")
            choice = input("Do you want to re-index the repository? (y/N): ").strip().lower()
            if choice != 'y':
                needs_ingestion = False

        if needs_ingestion:
            from core.paths import get_embedding_model,download_to_program_files
            from ingest.run_ingest import run_ingest
            if get_embedding_model():
                print("\nStarting repository ingestion...")
                try:
                    run_ingest(repo_path, clean=True)
                    print("\nIngestion complete!")
                except Exception as e:
                    print(f"\nIngestion failed: {e}")
                    print("Returning to repository selection...\n")
                    continue
            else:
                print("\nNo embedding model found. Downloading Embedding Model...")
                try:
                    download_to_program_files()
                    print("\nDownload complete!")
                    try:
                        run_ingest(repo_path, clean=True)
                        print("\nIngestion complete!")
                    except Exception as e:
                        print(f"\nIngestion failed: {e}")
                        print("Returning to repository selection...\n")
                        continue
                except Exception as e:
                    print(f"\nFailed to download embedding model: {e}")
                    continue
        else:
            print("\nSkipping ingestion. Using existing indexes.")
            
        # Inner loop for the Sentinel CLI
        while True:
            print("\n=======================================")
            print("[1] Start Code-Sentinel CLI")
            print("[2] Change Repository")
            print("[3] Exit Application")
            print("=======================================")
            choice = input("Choice: ").strip()
            
            if choice == "1":
                from main import main as inititate_sentinel
                try:
                    inititate_sentinel()
                except Exception as e:
                    print(f"An error occurred while running the CLI: {e}")
            elif choice == "2":
                print("\nChanging repository...")
                # Drop reference to vector db and retriever to free up memory before re-ingestion
                from torch.cuda import is_available,empty_cache
                if is_available():
                    empty_cache()
                import gc
                gc.collect()
                time.sleep(3)
                break 
            elif choice == "3":
                print("Exiting Code-Sentinel.")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFatal error: {e}")
        input("Press Enter to close...")