# `model_manager.py`

This module provides utility functions for managing models in an Ollama environment, focusing on unloading and warming up models to optimize resource usage and performance. The public API includes `unload_model` for evicting a model from VRAM, `unload_workers` as a convenience function to unload shared worker models, `warmup_model` for pre-loading models to prevent cold starts, and `check_ollama_running` for performing a quick health check on the Ollama service. Important dependencies include network connectivity to communicate with Ollama and access to VRAM resources for model management.

## Functions

### `def unload_model(model_name: str) -> bool:`
*D:\CodeSentinel\agent-python\core\model_manager.py:12*

Sends a keep_alive=0 request to Ollama to immediately evict the model from VRAM.
Call this before starting the 14B orchestrator to reclaim memory.

### `def unload_workers():`
*D:\CodeSentinel\agent-python\core\model_manager.py:34*

Convenience wrapper — unloads the shared worker model.

### `def warmup_model(model_name: str, keep_alive_seconds: int=600):`
*D:\CodeSentinel\agent-python\core\model_manager.py:42*

Pre-loads a model into Ollama so the first real request isn't cold.
Optional but reduces first-token latency.

### `def check_ollama_running() -> bool:`
*D:\CodeSentinel\agent-python\core\model_manager.py:64*

Quick health check — returns False if Ollama isn't reachable.

## Static Analysis Warnings

- **[LOW]** line 34: `unload_workers` has no return type annotation.
- **[LOW]** line 42: `warmup_model` has no return type annotation.
