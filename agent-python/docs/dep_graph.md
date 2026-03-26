# `dep_graph.py`

This module provides a `DependencyGraph` class for analyzing file dependencies in a codebase. The public API includes methods like `build`, `get_dependencies`, `get_dependents`, `get_callers_of`, `get_definers_of`, and `shortest_path`. It relies on the NetworkX library to manage directed graphs internally. The module also offers utility functions such as `_get_node`, `get_file_symbols`, and `expand_context` for more detailed dependency analysis.

## Classes

### `DependencyGraph`
Wraps a NetworkX DiGraph and exposes retrieval helpers used by the
HybridRetriever to expand context around matched symbols.

Methods: `__init__`, `build`, `get_dependencies`, `get_dependents`, `get_callers_of`, `get_definers_of`, `_get_node`, `get_file_symbols`, `expand_context`, `shortest_path`, `get_strongly_connected`, `save`, `load`, `_bfs_neighbors`, `_normalise`, `_resolve_import`

## Functions

### `def __init__(self):`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:32*

Initializes a new instance of the class with an empty directed graph and three dictionaries to store function/class definitions, callers, and file symbols. No parameters. Returns nothing. Raises no exceptions.

### `def build(self, analyses: List[FileAnalysis], repo_root: str='') -> None:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:45*

Populate graph from a list of FileAnalysis objects.
Call this once after parsing the whole repository.

### `def get_dependencies(self, filepath: str, hops: int=1) -> Set[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:90*

Files that `filepath` imports, up to `hops` levels deep.
(files this file depends ON)

### `def get_dependents(self, filepath: str, hops: int=1) -> Set[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:97*

Files that import `filepath`.
(files that depend ON this file)

### `def get_callers_of(self, symbol_name: str) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:104*

Return files that call `symbol_name`.

### `def get_definers_of(self, symbol_name: str) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:108*

Return files that define `symbol_name`.

### `def _get_node(self, node_path: str) -> Optional[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:112*

Safely resolve an absolute or relative path to a graph node.

### `def get_file_symbols(self, filepath: str) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:125*

Return names of all functions/classes defined in `filepath`.

### `def expand_context(self, seed_files: List[str], dep_hops: int=1, max_files: int=15) -> List[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:132*

Given a list of seed files (from vector search hits), expand to include
their direct dependencies and dependents. Returns a deduplicated,
size-capped list of files for the LLM context window.

### `def shortest_path(self, source: str, target: str) -> Optional[List[str]]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:155*

Return import chain from source to target, if one exists.

### `def get_strongly_connected(self) -> List[List[str]]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:162*

Return groups of files that form circular import cycles.

### `def save(self, path: str) -> None:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:175*

Persist graph to a GraphML file.

### `def load(self, path: str) -> None:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:180*

Load a previously saved graph.

### `def _bfs_neighbors(self, node: str, direction: str, hops: int) -> Set[str]:`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:189*

Performs a breadth-first search (BFS) to find neighbors of a given node in a specified direction and within a certain number of hops.

Parameters:
- `node` (str): The starting node for the BFS.
- `direction` (str): The direction of traversal, either "successors" or "predecessors".
- `hops` (int): The maximum number of hops to traverse.

Returns:
Set[str]: A set of nodes that are reachable within the specified number of hops in the given direction.

Raises:
- ValueError: If the direction is not one of "successors" or "predecessors".

### `@staticmethod`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:209*

Make filepath relative to repo root for stable node IDs.

### `@staticmethod`
*D:\CodeSentinel\agent-python\ingest\dep_graph.py:219*

Try to map a dotted module name to a .py file within the repo.
Returns None for third-party packages we can't resolve locally.
