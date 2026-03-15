# `symbol_index.py`

This module provides a `SymbolIndex` class for managing a symbol database using SQLite. The primary purpose is to index and retrieve symbols (functions, classes) from source files efficiently. Key public API includes methods like `ingest` for adding symbols, `lookup` for exact name matches, and `search` for prefix-based searches. Important dependencies include the `sqlite3` library for database operations and a custom `FileAnalysis` class for symbol extraction. The module also offers utility functions such as `all_function_names`, `all_file_paths`, and `stats` to provide insights into the indexed data.

## Classes

### `SymbolRow`
*No class docstring.*

Methods: ``

### `SymbolIndex`
SQLite-backed symbol store. Instantiate once; pass it to the retriever.

Methods: `__init__`, `clear`, `ingest`, `lookup`, `search`, `get_file_symbols`, `get_source`, `all_function_names`, `all_file_paths`, `stats`, `_fn_query`, `_cls_query`, `close`

## Functions

### `def __init__(self, db_path: str=DB_PATH_DEFAULT):`
*ingest/symbol_index.py:81*

Initializes a new instance of the class with a specified database path. Connects to the SQLite database at the given path and sets up the connection to use `sqlite3.Row` for row access. Executes the schema script to create necessary tables if they do not exist.

Parameters:
- db_path (str): The path to the SQLite database file. Defaults to `DB_PATH_DEFAULT`.

Return value:
- None

Raises:
- sqlite3.Error: If there is an error connecting to or setting up the database.

### `def clear(self) -> None:`
*ingest/symbol_index.py:92*

Drop all rows — used before a full re-index.

### `def ingest(self, analyses: List[FileAnalysis]) -> None:`
*ingest/symbol_index.py:99*

Insert all symbols from a list of FileAnalysis objects.
Uses INSERT OR REPLACE so repeated ingestion is safe.

### `def lookup(self, name: str) -> List[SymbolRow]:`
*ingest/symbol_index.py:153*

Exact name match. Returns all definitions (could be in multiple files).

### `def search(self, partial: str, limit: int=10) -> List[SymbolRow]:`
*ingest/symbol_index.py:160*

Prefix search — returns functions and classes whose name starts with `partial`.

### `def get_file_symbols(self, filepath: str) -> List[SymbolRow]:`
*ingest/symbol_index.py:168*

All symbols defined in a specific file.

### `def get_source(self, name: str) -> Optional[str]:`
*ingest/symbol_index.py:175*

Return the source of the first match for `name`.

### `def all_function_names(self) -> List[str]:`
*ingest/symbol_index.py:180*

Returns a list of distinct function names from the database. No parameters. Returns a list of strings. Raises an exception if the database query fails.

### `def all_file_paths(self) -> List[str]:`
*ingest/symbol_index.py:184*

Returns a list of unique file paths from the 'functions' and 'classes' tables.

Parameters:
- None

Return value:
- List[str]: A list containing distinct file paths as strings.

Raises:
- None

### `def stats(self) -> dict:`
*ingest/symbol_index.py:191*

Returns a dictionary containing the count of functions, classes, and files. No parameters. Raises an exception if database queries fail.

### `def _fn_query(self, where: str, params: tuple) -> List[SymbolRow]:`
*ingest/symbol_index.py:201*

Queries the database for function symbols based on a given SQL WHERE clause and parameters.

Parameters:
- where (str): The SQL WHERE clause to filter the query.
- params (tuple): A tuple of parameters to be used with the SQL query.

Returns:
List[SymbolRow]: A list of SymbolRow objects representing the queried functions.

Raises:
- DatabaseError: If there is an error executing the database query.

### `def _cls_query(self, where: str, params: tuple) -> List[SymbolRow]:`
*ingest/symbol_index.py:218*

Executes a SQL query to retrieve class information from the database.

Parameters:
- where (str): The WHERE clause of the SQL query.
- params (tuple): Parameters to be used with the SQL query.

Returns:
List[SymbolRow]: A list of SymbolRow objects containing class information.

Raises:
- DatabaseError: If there is an error executing the SQL query.

### `def close(self) -> None:`
*ingest/symbol_index.py:235*

Closes the connection to the database. No parameters. Returns None. Raises an exception if the connection is already closed or if there is an error during closure.
