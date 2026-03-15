# `dep_graph.py`

This module provides functionality for analyzing and querying a dependency graph constructed from file analysis data. It includes key classes and functions such as `DependencyGraph` for managing the directed graph, methods like `build`, `get_dependencies`, `get_dependents`, and others for retrieving various types of dependencies and relationships between files. The module relies on NetworkX for graph operations and is designed to support hybrid retrieval systems by expanding search contexts and identifying circular import cycles.

## Classes

### `DependencyGraph`
Wraps a NetworkX DiGraph and exposes retrieval helpers used by the
HybridRetriever to expand context around matched symbols.

Methods: `__init__`, `build`, `get_dependencies`, `get_dependents`, `get_callers_of`, `get_definers_of`, `get_file_symbols`, `expand_context`, `shortest_path`, `get_strongly_connected`, `save`, `load`, `_bfs_neighbors`, `_normalise`, `_resolve_import`

## Functions

### `def __init__(self):`
*ingest/dep_graph.py:32*

Initializes a new instance of the class with an empty directed graph and dictionaries to store function/class definitions, callers, and symbols per file. No parameters. Returns nothing. Raises no exceptions.

### `def build(self, analyses: List[FileAnalysis], repo_root: str='') -> None:`
*ingest/dep_graph.py:45*

Populate graph from a list of FileAnalysis objects.
Call this once after parsing the whole repository.

### `def get_dependencies(self, filepath: str, hops: int=1) -> Set[str]:`
*ingest/dep_graph.py:90*

Files that `filepath` imports, up to `hops` levels deep.
(files this file depends ON)

### `def get_dependents(self, filepath: str, hops: int=1) -> Set[str]:`
*ingest/dep_graph.py:97*

Files that import `filepath`.
(files that depend ON this file)

### `def get_callers_of(self, symbol_name: str) -> List[str]:`
*ingest/dep_graph.py:104*

Return files that call `symbol_name`.

### `def get_definers_of(self, symbol_name: str) -> List[str]:`
*ingest/dep_graph.py:108*

Return files that define `symbol_name`.

### `def get_file_symbols(self, filepath: str) -> List[str]:`
*ingest/dep_graph.py:112*

Return names of all functions/classes defined in `filepath`.

### `def expand_context(self, seed_files: List[str], dep_hops: int=1, max_files: int=15) -> List[str]:`
*ingest/dep_graph.py:116*

Given a list of seed files (from vector search hits), expand to include
their direct dependencies and dependents. Returns a deduplicated,
size-capped list of files for the LLM context window.

### `def shortest_path(self, source: str, target: str) -> Optional[List[str]]:`
*ingest/dep_graph.py:139*

Return import chain from source to target, if one exists.

### `def get_strongly_connected(self) -> List[List[str]]:`
*ingest/dep_graph.py:146*

Return groups of files that form circular import cycles.

### `def save(self, path: str) -> None:`
*ingest/dep_graph.py:159*

Persist graph to a GraphML file.

### `def load(self, path: str) -> None:`
*ingest/dep_graph.py:164*

Load a previously saved graph.

### `def _bfs_neighbors(self, node: str, direction: str, hops: int) -> Set[str]:`
*ingest/dep_graph.py:173*

Performs a breadth-first search (BFS) to find neighbors of a given node in a graph.

Parameters:
- `node` (str): The starting node for the BFS.
- `direction` (str): The direction of traversal, either "successors" or "predecessors".
- `hops` (int): The number of hops to traverse from the starting node.

Returns:
- Set[str]: A set of nodes that are reachable within the specified number of hops.

Raises:
- ValueError: If the direction is not one of "successors" or "predecessors".

### `@staticmethod`
*ingest/dep_graph.py:189*

Make filepath relative to repo root for stable node IDs.

### `@staticmethod`
*ingest/dep_graph.py:199*

Try to map a dotted module name to a .py file within the repo.
Returns None for third-party packages we can't resolve locally.
