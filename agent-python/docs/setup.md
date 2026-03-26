# `setup.py`

This module provides a set of utility functions to manage the setup and configuration of the Ollama environment. It includes checks for the installation and running status of the Ollama CLI, as well as functions to install Ollama, pull necessary models, bootstrap dependencies, and set up the environment paths. The key classes/functions are `is_ollama_installed`, `is_ollama_running`, `install_ollama`, `pull_models`, `bootstrap_dependencies`, and `setup_environment`. Important dependencies include the ability to execute shell commands for installation and model pulling, as well as access to system directories for path configuration.

## Functions

### `def is_ollama_installed():`
*D:\CodeSentinel\agent-python\setup.py:16*

Check if the Ollama CLI is available on the system.

### `def is_ollama_running():`
*D:\CodeSentinel\agent-python\setup.py:26*

Check if the Ollama background service is responding.

### `def install_ollama():`
*D:\CodeSentinel\agent-python\setup.py:34*

Detect OS and run the appropriate Ollama installation sequence.

### `def pull_models():`
*D:\CodeSentinel\agent-python\setup.py:99*

Ensure both required models are downloaded.

### `def bootstrap_dependencies():`
*D:\CodeSentinel\agent-python\setup.py:114*

Run the full pre-flight checklist.

### `def setup_environment(source_dir: str):`
*D:\CodeSentinel\agent-python\setup.py:136*

Sets all path env vars. Must use get_app_dir(), NOT __file__.
__file__ in a frozen exe = _internal/setup.pyc — wrong and read-only.

## Static Analysis Warnings

- **[LOW]** line 16: `is_ollama_installed` has no return type annotation.
- **[LOW]** line 26: `is_ollama_running` has no return type annotation.
- **[LOW]** line 34: `install_ollama` is 63 lines long (limit: 60).
- **[LOW]** line 34: `install_ollama` has no return type annotation.
- **[LOW]** line 99: `pull_models` has no return type annotation.
- **[LOW]** line 114: `bootstrap_dependencies` has no return type annotation.
- **[LOW]** line 136: `setup_environment` has no return type annotation.
