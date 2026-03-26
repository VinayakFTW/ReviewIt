# `symbol_index.py`

This module provides a `SymbolIndex` class for managing a symbol database using SQLite. The primary purpose is to index and retrieve symbols (functions, classes) from source files efficiently. Key public API includes methods like `ingest` for adding symbols, `lookup` for exact name matches, and `search` for prefix-based searches. Important dependencies include the `sqlite3` library for database operations and a custom `FileAnalysis` class for symbol extraction. The module also offers utility functions such as `get_file_symbols`, `get_source`, and `stats` to interact with the indexed data.

## Classes

### `SymbolRow`
*No class docstring.*

Methods: ``

### `SymbolIndex`
SQLite-backed symbol store. Instantiate once; pass it to the retriever.

Methods: `__init__`, `clear`, `ingest`, `lookup`, `search`, `get_file_symbols`, `get_source`, `all_function_names`, `all_file_paths`, `stats`, `_fn_query`, `_cls_query`, `close`

## Functions

### `def __init__(self, db_path: str | None=None):`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:79*

Initializes a new instance of the class with an optional database path. If no path is provided, it defaults to a predefined symbol database. Establishes a connection to the SQLite database, sets the row factory to return rows as dictionaries, executes the schema script to set up the database tables, and commits the changes.

Parameters:
- db_path (str | None): The path to the SQLite database file. If None, uses the default symbol database.

Return value:
None

Raises:
- sqlite3.Error: If there is an error connecting to or setting up the database.

### `def clear(self) -> None:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:90*

Drop all rows — used before a full re-index.

### `def ingest(self, analyses: List[FileAnalysis]) -> None:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:97*

Insert all symbols from a list of FileAnalysis objects.
Uses INSERT OR REPLACE so repeated ingestion is safe.

### `def lookup(self, name: str) -> List[SymbolRow]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:151*

Exact name match. Returns all definitions (could be in multiple files).

### `def search(self, partial: str, limit: int=10) -> List[SymbolRow]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:158*

Prefix search — returns functions and classes whose name starts with `partial`.

### `def get_file_symbols(self, filepath: str) -> List[SymbolRow]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:166*

All symbols defined in a specific file.

### `def get_source(self, name: str) -> Optional[str]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:173*

Return the source of the first match for `name`.

### `def all_function_names(self) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:178*

Returns a list of distinct function names from the database. No parameters. Returns a list of strings. Raises an exception if the database query fails.

### `def all_file_paths(self) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:182*

Retrieves a list of unique file paths from the 'functions' and 'classes' tables.

Returns:
    List[str]: A list of distinct file paths.

Raises:
    None.

### `def stats(self) -> dict:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:189*

Returns a dictionary containing the count of functions, classes, and files. No parameters. Raises an exception if database queries fail.

### `def _fn_query(self, where: str, params: tuple) -> List[SymbolRow]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:199*

Executes a SQL query to retrieve function symbols from the database.

Parameters:
    where (str): The WHERE clause of the SQL query.
    params (tuple): Parameters to be substituted into the SQL query.

Returns:
    List[SymbolRow]: A list of SymbolRow objects representing the retrieved functions.

Raises:
    DatabaseError: If an error occurs during the database operation.

### `def _cls_query(self, where: str, params: tuple) -> List[SymbolRow]:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:216*

Executes a SQL query to retrieve class information from the database and returns a list of SymbolRow objects.

Parameters:
- where (str): The WHERE clause of the SQL query.
- params (tuple): Parameters to be substituted into the SQL query.

Return value:
List[SymbolRow]: A list of SymbolRow objects containing class information.

Raises:
No specific exceptions are raised by this function. However, it may raise database-related exceptions if the SQL execution fails.

### `def close(self) -> None:`
*D:\CodeSentinel\agent-python\ingest\symbol_index.py:233*

Closes the connection to the database. No parameters. Returns None. Raises an exception if the connection is already closed or fails to close.
