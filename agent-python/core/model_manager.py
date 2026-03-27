import requests
import time
from rich import print
    
OLLAMA_BASE_URL = "http://localhost:11434"

# The small worker model — qwen2.5-coder:0.5b is ~400MB, fast, code-aware.
# Swap for "smollm2:360m" if you want pure 300M, but it's weaker on code.
WORKER_MODEL = "qwen2.5-coder:0.5b"
ORCHESTRATOR_MODEL = "qwen2.5-coder:14b"


def unload_model(model_name: str) -> bool:
    """
    Sends a keep_alive=0 request to Ollama to immediately evict the model from VRAM.
    Call this before starting the 14B orchestrator to reclaim memory.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model_name, "keep_alive": 0, "prompt": ".", "stream": False},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"[ModelManager] Unloaded '{model_name}' from VRAM.")
            return True
        else:
            print(f"[ModelManager] Warning: unload returned {resp.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ModelManager] Could not unload '{model_name}': {e}")
        return False


def unload_workers():
    """Convenience wrapper — unloads the shared worker model."""
    print("[ModelManager] Evicting worker model from VRAM...")
    unload_model(WORKER_MODEL)
    # Brief pause to let Ollama finish the eviction before 14B loads.
    time.sleep(1.5)


def warmup_model(model_name: str, keep_alive_seconds: int = 600):
    """
    Pre-loads a model into Ollama so the first real request isn't cold.
    Optional but reduces first-token latency.
    """
    try:
        print(f"[ModelManager] Warming up '{model_name}'...")
        requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "keep_alive": keep_alive_seconds,
                "prompt": ".",
                "stream": False,
            },
            timeout=120,
        )
        print(f"[ModelManager] '{model_name}' ready.")
    except requests.exceptions.RequestException as e:
        print(f"[ModelManager] Warning: warmup failed for '{model_name}': {e}")


def check_ollama_running() -> bool:
    """Quick health check — returns False if Ollama isn't reachable."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False
