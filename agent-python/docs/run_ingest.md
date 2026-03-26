# `run_ingest.py`

This module is designed to handle the ingestion and indexing of code from a specified source directory. The primary function, `run_ingest`, orchestrates the entire process, ensuring that all relevant files are parsed and stored appropriately. Key dependencies include libraries for file system navigation, code parsing, and database interaction to manage the indexed data efficiently. This module is essential for projects requiring comprehensive codebase analysis or documentation generation.

## Functions

### `def run_ingest(source_dir: str, clean: bool=True) -> None:`
*D:\CodeSentinel\agent-python\ingest\run_ingest.py:29*

Runs the ingestion process for indexing code from a specified source directory. Cleans existing indexes if requested, parses source files using AST, builds symbol index and dependency graph, and embeds symbols into ChromaDB.

Parameters:
- `source_dir` (str): The path to the source directory containing the code to be indexed.
- `clean` (bool, optional): If True, cleans existing indexes before running the ingestion process. Defaults to True.

Return value:
- None

Raises:
- SystemExit: If the specified source directory does not exist.

## Static Analysis Warnings

- **[LOW]** line 29: `run_ingest` is 65 lines long (limit: 60).
