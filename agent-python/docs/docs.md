# `docs.py`

This Python module provides functionality to generate and update documentation for a codebase. It includes two main public functions, `run_incremental` and `run_full`, which respectively update documentation for changed files since a specified commit or regenerate the entire codebase's documentation from scratch. The key class is `DocsPipeline`, initialized with a hybrid retriever and source directory. Important dependencies include file system operations for detecting changes and JSON handling for caching purposes.

## Classes

### `DocsPipeline`
Generates and incrementally updates documentation for the codebase.
Output directory: docs/ (configurable).

Methods: `__init__`, `run_incremental`, `run_full`, `_document_files`, `_document_functions`, `_document_module`, `_update_architecture_doc`, `_write_module_doc`, `_load_cache`, `_save_cache`

## Functions

### `def detect_changed_files(repo_path: str, since: str='HEAD~1') -> Optional[Set[str]]:`
*pipelines/docs.py:64*

Return set of .py files changed since `since` commit.
Returns None if gitpython is not installed or repo is not a git repo.

### `def __init__(self, retriever: HybridRetriever, source_dir: str, docs_dir: str='docs'):`
*pipelines/docs.py:94*

Initializes a new instance of the class with a hybrid retriever, source directory, and optional documents directory. Sets up a language learning model and initializes a cache for module summaries. Raises an error if the directories cannot be created or accessed.

### `def run_incremental(self, since: str='HEAD~1') -> None:`
*pipelines/docs.py:117*

Detect changed files and update only their documentation.
Called by git post-push hook.

### `def run_full(self) -> None:`
*pipelines/docs.py:137*

Document the entire codebase from scratch.
Skips files whose summary is already cached.

### `def _document_files(self, filepaths: List[str], update_architecture: bool):`
*pipelines/docs.py:155*

Documents a list of files by analyzing their content, generating function-level and module-level documentation, caching summaries, writing doc files, and optionally updating an architecture overview.

Parameters:
- filepaths (List[str]): A list of file paths to be documented.
- update_architecture (bool): If True, updates the architecture overview if the structure has changed.

Returns:
- None

Raises:
- FileNotFoundError: If a specified file path does not exist.

### `def _document_functions(self, analysis: FileAnalysis) -> Dict[str, str]:`
*pipelines/docs.py:180*

Generate docstrings for functions that lack them.

### `def _document_module(self, analysis: FileAnalysis, fn_docs: Dict[str, str]) -> str:`
*pipelines/docs.py:200*

Generate a module-level summary.

### `def _update_architecture_doc(self) -> None:`
*pipelines/docs.py:222*

Regenerate top-level architecture.md from all cached module summaries.

### `def _write_module_doc(self, filepath: str, analysis: FileAnalysis, fn_docs: Dict[str, str], module_summary: str) -> None:`
*pipelines/docs.py:243*

Write per-module markdown doc file.

### `def _load_cache(self) -> Dict[str, str]:`
*pipelines/docs.py:294*

Loads a cache from a JSON file.

Parameters:
    self (object): The instance of the class containing the method.

Returns:
    Dict[str, str]: A dictionary loaded from the cache file if it exists, otherwise an empty dictionary.

Raises:
    FileNotFoundError: If the specified cache file does not exist.
    json.JSONDecodeError: If the cache file contains invalid JSON.

### `def _save_cache(self) -> None:`
*pipelines/docs.py:300*

Saves the summary cache to a file in JSON format. No parameters. Returns None. Raises IOError if there is an error writing to the file.

## Static Analysis Warnings

- **[LOW]** line 155: `_document_files` has no return type annotation.
