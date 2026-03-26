# `docs.py`

This Python module provides functionality to generate and update documentation for a codebase. It includes two main public functions, `run_incremental` and `run_full`, which allow for incremental updates based on changed files or full re-documentation of the entire codebase, respectively. The key class is `DocsPipeline`, which manages the documentation generation process using a hybrid retriever and source directory. Important dependencies include parsing libraries to understand Python code structure and JSON handling for caching purposes.

## Classes

### `DocsPipeline`
Generates and incrementally updates documentation for the codebase.
Output directory: docs/ (configurable).

Methods: `__init__`, `run_incremental`, `run_full`, `_document_files`, `_document_functions`, `_document_module`, `_update_architecture_doc`, `_write_module_doc`, `_load_cache`, `_save_cache`

## Functions

### `def detect_changed_files(repo_path: str, since: str='HEAD~1') -> Optional[Set[str]]:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:64*

Return set of .py files changed since `since` commit.
Returns None if gitpython is not installed or repo is not a git repo.

### `def __init__(self, retriever: HybridRetriever, source_dir: str, docs_dir: str='docs'):`
*D:\CodeSentinel\agent-python\pipelines\docs.py:94*

Initializes a new instance of the class with a hybrid retriever, source directory, and optional documents directory. Sets up a language learning model and initializes a cache for module summaries. Creates the documents directory if it does not exist. Loads any existing summary cache from a JSON file.

Parameters:
- retriever (HybridRetriever): The hybrid retriever to be used.
- source_dir (str): The path to the source directory.
- docs_dir (str, optional): The path to the documents directory. Defaults to "docs".

Return value: None

Raises:
- OSError: If there is an error creating the documents directory or loading the cache file.

### `def run_incremental(self, since: str='HEAD~1') -> None:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:117*

Detect changed files and update only their documentation.
Called by git post-push hook.

### `def run_full(self) -> None:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:137*

Document the entire codebase from scratch.
Skips files whose summary is already cached.

### `def _document_files(self, filepaths: List[str], update_architecture: bool):`
*D:\CodeSentinel\agent-python\pipelines\docs.py:155*

Documents a list of files by parsing them and generating function-level and module-level documentation. Updates the architecture document if specified.

Parameters:
- filepaths (List[str]): A list of file paths to be documented.
- update_architecture (bool): If True, updates the architecture overview document.

Returns:
None

Raises:
- None

### `def _document_functions(self, analysis: FileAnalysis) -> Dict[str, str]:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:180*

Generate docstrings for functions that lack them.

### `def _document_module(self, analysis: FileAnalysis, fn_docs: Dict[str, str]) -> str:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:200*

Generate a module-level summary.

### `def _update_architecture_doc(self) -> None:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:222*

Regenerate top-level architecture.md from all cached module summaries.

### `def _write_module_doc(self, filepath: str, analysis: FileAnalysis, fn_docs: Dict[str, str], module_summary: str) -> None:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:243*

Write per-module markdown doc file.

### `def _load_cache(self) -> Dict[str, str]:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:294*

Loads a cache from a JSON file.

Parameters:
    self (object): The instance of the class containing this method.

Returns:
    Dict[str, str]: A dictionary loaded from the JSON file if it exists, otherwise an empty dictionary.

Raises:
    FileNotFoundError: If the specified cache path does not exist.
    json.JSONDecodeError: If the file contains invalid JSON.

### `def _save_cache(self) -> None:`
*D:\CodeSentinel\agent-python\pipelines\docs.py:300*

Saves the summary cache to a file in JSON format. No parameters. Returns None. Raises IOError if there is an error writing to the file.

## Static Analysis Warnings

- **[LOW]** line 155: `_document_files` has no return type annotation.
