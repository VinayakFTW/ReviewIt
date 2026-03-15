# `model_manager.py`

This module provides utility functions for managing models in an environment that uses Ollama, likely a service or application for handling machine learning models. The primary purpose is to facilitate the unloading and pre-loading of models to optimize memory usage and performance.

The public API includes:
- `unload_model`: Unloads a specified model from VRAM by sending a keep_alive=0 request.
- `unload_workers`: A convenience function that unloads the shared worker model.
- `warmup_model`: Pre-loads a model into Ollama to ensure it is ready for use, reducing latency on the first real request.
- `check_ollama_running`: Performs a quick health check to verify if Ollama is reachable.

Important dependencies include:
- The module relies on network connectivity to communicate with Ollama.
- It assumes the existence of certain endpoints or APIs provided by Ollama for model management.

## Functions

### `def unload_model(model_name: str) -> bool:`
*core/model_manager.py:12*

Sends a keep_alive=0 request to Ollama to immediately evict the model from VRAM.
Call this before starting the 14B orchestrator to reclaim memory.

### `def unload_workers():`
*core/model_manager.py:34*

Convenience wrapper — unloads the shared worker model.

### `def warmup_model(model_name: str, keep_alive_seconds: int=600):`
*core/model_manager.py:42*

Pre-loads a model into Ollama so the first real request isn't cold.
Optional but reduces first-token latency.

### `def check_ollama_running() -> bool:`
*core/model_manager.py:64*

Quick health check — returns False if Ollama isn't reachable.

## Static Analysis Warnings

- **[LOW]** line 34: `unload_workers` has no return type annotation.
- **[LOW]** line 42: `warmup_model` has no return type annotation.
