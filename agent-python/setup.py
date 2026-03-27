"""This script only runs once when the user is running the sentinel for the first time. It sets up environment variables and starts the ingestion process, then launches the main CLI."""

import os
import sys
import time
import subprocess
import urllib.request
import requests
import tempfile
import zipfile
import shutil
from rich.console import Console
from rich import print
console = Console()

# The models required for the agent
MODELS = ["qwen2.5-coder:0.5b", "qwen2.5-coder:14b"]
OLLAMA_BASE_URL = "http://localhost:11434"
def is_ollama_installed():
    """Check if the Ollama CLI is available on the system."""
    try:
        # Use shell=True on Windows to resolve the executable if it's in PATH
        use_shell = sys.platform == "win32"
        subprocess.run(["ollama", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=use_shell)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def is_ollama_running(WORKER_MODEL=MODELS[0]) -> bool:
    try:
        # Step 1: reachability
        if requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5).status_code != 200:
            return False
        # Step 2: generate endpoint probe (keep_alive=0 = no VRAM committed)
        probe = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": WORKER_MODEL, "prompt": ".", "keep_alive": 0, "stream": False},
            timeout=30,
        )
        return probe.status_code == 200
    except requests.exceptions.RequestException:
        return False

def install_ollama():
    """Detect OS and run the appropriate Ollama installation sequence."""
    system = sys.platform
    temp_dir = tempfile.gettempdir()
    
    print("\n[Setup] Ollama is not installed. Initiating automated setup...")

    try:
        if system == "win32":
            print("[Setup] Windows detected. Downloading the official installer...")
            installer_path = os.path.join(temp_dir, "OllamaSetup.exe")
            urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
            
            print("[Setup] Launching installer... **Please follow the prompts and grant admin permissions.**")
            subprocess.run([installer_path], check=True)

        elif system.startswith("linux"):
            print("[Setup] Linux detected. Running the official install script via curl...")
            print("[Setup] **You may be prompted for your sudo password.**")
            subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)

        elif system == "darwin":
            print("[Setup] macOS detected. Downloading the Ollama app bundle...")
            zip_path = os.path.join(temp_dir, "Ollama-darwin.zip")
            urllib.request.urlretrieve("https://ollama.com/download/Ollama-darwin.zip", zip_path)
            
            print("[Setup] Extracting Ollama...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
            app_source = os.path.join(temp_dir, "Ollama.app")
            app_dest = "/Applications/Ollama.app"
            
            if os.path.exists(app_dest):
                shutil.rmtree(app_dest)
                
            print("[Setup] Moving Ollama to /Applications...")
            shutil.move(app_source, app_dest)
            
            print("[Setup] Launching Ollama... **Please follow the Mac prompts to finish installing the CLI.**")
            subprocess.run(["open", app_dest], check=True)
            
            # Mac users might need a moment to click through the setup wizard
            print("[Setup] Waiting 15 seconds for you to click through the Mac setup...")
            time.sleep(15)

        else:
            print(f"[Error] Unsupported operating system: {system}")
            print("Please install Ollama manually from https://ollama.com/")
            sys.exit(1)

        print("\n[Setup] Waiting for the Ollama background service to start...")
        for _ in range(30):
            if is_ollama_running():
                print("[Setup] Ollama service is up and running!")
                return
            time.sleep(2)
            
        print("[Setup] Warning: Ollama doesn't seem to be responding yet. We will try to continue anyway.")
        
    except Exception as e:
        print(f"\n[Error] Failed to install Ollama automatically: {e}")
        print("Please download and install it manually from https://ollama.com/")
        sys.exit(1)

def pull_models():
    """Ensure both required models are downloaded."""
    console.print("\n[bold cyan]Checking local AI models...[/bold cyan]")
    use_shell = sys.platform == "win32"
    
    for model in MODELS:
        with console.status(f"[magenta]Pulling {model}... (This might take a while, grab a coffee!)[/magenta]", spinner="aesthetic"):
            try:
                subprocess.run(["ollama", "pull", model], check=True, shell=use_shell, stdout=subprocess.DEVNULL)
                console.print(f"  [green]✔[/green] Successfully pulled [bold]{model}[/bold]")
            except subprocess.CalledProcessError as e:
                console.print(f"  [red]✖[/red] Failed to pull {model}: {e}")
                sys.exit(1)

def bootstrap_dependencies():
    """Run the full pre-flight checklist."""
    if not is_ollama_installed():
        install_ollama()
    
    if not is_ollama_running():
        print("\n[Setup] Ollama is installed but the service isn't running.")
        print("Attempting to start it...")
        try:
            use_shell = sys.platform == "win32"
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=use_shell)
            time.sleep(5)
        except Exception:
            pass
            
        if not is_ollama_running():
            print("[Error] Could not start Ollama automatically.")
            print("Please open the Ollama app manually from your system menu/tray and restart this tool.")
            sys.exit(1)
            
    pull_models()

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

