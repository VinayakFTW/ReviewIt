import os
import sys
from setup import *

def main():
    print("========================================================")
    print("           Code-Sentinel - Code Review Assistant             ")
    print("========================================================")
    print("Note: Please ensure Ollama is running in the background.\n")
    
    repo_path = input("Enter the absolute path to your codebase(eg: /path/to/your/repo): ").strip()
    repo_path = repo_path.strip('"').strip("'")

    if not os.path.exists(repo_path):
        print(f"Error: The path '{repo_path}' does not exist.")
        sys.exit(1)
        
    # Configure the paths for this session
    if (("SOURCE_DIR" not in os.environ or os.environ["SOURCE_DIR"] != repo_path) 
        and "PERSIST_DIRECTORY" not in os.environ 
        and "SYMBOL_DB_PATH" not in os.environ 
        and "DEP_GRAPH_PATH" not in os.environ 
        and "DOCS_DIR" not in os.environ):
        
        print("Setting up environment variables...")
        setup_environment(repo_path)
        bootstrap_dependencies()
        
    else:
        print("Environment already configured for this repository.")

    print("\nStarting repository ingestion...")

    from ingest.run_ingest import run_ingest
    
    try:
        run_ingest(repo_path, clean=True)
    except Exception as e:
        print(f"\nIngestion failed: {e}")
        sys.exit(1)
        
    while True:
        print("\nIngestion complete!")
        print("[1] Start Code-Sentinel CLI")
        print("[2] Exit")
        choice = input("Choice: ").strip()
        
        if choice == "1":
            from main import main as inititate_sentinel
            inititate_sentinel()
            break
        elif choice == "2":
            print("Exiting Code-Sentinel.")
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

if __name__ == "__main__":
    main()