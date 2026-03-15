# `hybrid_retriever.py`

This module provides functionality for hybrid retrieval of code symbols based on natural language queries. It includes a `HybridRetriever` class that combines vector search with dependency graph expansion to find relevant code contexts. The public API consists of the `HybridRetriever.retrieve` method, which performs the hybrid retrieval, and helper functions like `lookup_symbol`, `retrieve_for_file`, and `format_context`. Key dependencies include classes for handling code context (`CodeContext`) and symbol rows (`SymbolRow`). This module is used by all three agent processes.

## Classes

### `CodeContext`
One retrieved symbol's data, ready to be placed in an LLM prompt.

Methods: `format_for_prompt`

### `HybridRetriever`
Combines vector search and dependency-graph expansion.
Used by all three agent pipelines.

Methods: `__init__`, `retrieve`, `lookup_symbol`, `retrieve_for_file`, `format_context`, `_vector_search`, `_row_to_context`

## Functions

### `def format_for_prompt(self) -> str:`
*retrieval/hybrid_retriever.py:53*

Formats a prompt string for displaying code information.

Parameters:
- None

Returns:
- A formatted string containing the header and source code.

Raises:
- None

### `def __init__(self, vector_store: Chroma, dep_graph: DependencyGraph, symbol_index: SymbolIndex, vector_k: int=8, dep_hops: int=1, max_total: int=20):`
*retrieval/hybrid_retriever.py:69*

Initializes a new instance of the class with the provided parameters.

Parameters:
- vector_store (Chroma): The vector store to use for similarity searches.
- dep_graph (DependencyGraph): The dependency graph representing relationships between symbols.
- symbol_index (SymbolIndex): The index for efficiently looking up symbols.
- vector_k (int, optional): The number of top vectors to retrieve from the vector store. Defaults to 8.
- dep_hops (int, optional): The number of hops to traverse in the dependency graph. Defaults to 1.
- max_total (int, optional): The maximum total number of results to return. Defaults to 20.

Return value:
None

Raises:
No exceptions are raised by this method.

### `def retrieve(self, query: str, vector_k: Optional[int]=None, dep_hops: Optional[int]=None, max_total: Optional[int]=None) -> List[CodeContext]:`
*retrieval/hybrid_retriever.py:89*

Run hybrid retrieval for a natural language query.

Args:
    query:     Natural language question or code concept.
    vector_k:  Override default number of vector hits.
    dep_hops:  Override dependency expansion hops.
    max_total: Cap on total results returned.

Returns:
    Deduplicated list of CodeContext, best matches first.

### `def lookup_symbol(self, name: str) -> List[CodeContext]:`
*retrieval/hybrid_retriever.py:138*

Exact symbol name lookup — returns all definitions of `name`
with their source, ranked by specificity.

### `def retrieve_for_file(self, filepath: str) -> List[CodeContext]:`
*retrieval/hybrid_retriever.py:146*

Fetch all symbols defined in a specific file.
Used by the docs pipeline for per-file documentation.

### `@staticmethod`
*retrieval/hybrid_retriever.py:159*

Concatenate retrieved contexts into a single prompt block.
Truncates cleanly at symbol boundaries to stay within token limits.

### `def _vector_search(self, query: str, k: int) -> List[CodeContext]:`
*retrieval/hybrid_retriever.py:182*

Performs a vector search for the given query and returns the top k results as CodeContext objects.

Parameters:
- query (str): The search query.
- k (int): The number of top results to retrieve.

Returns:
List[CodeContext]: A list of CodeContext objects representing the search results.

Raises:
Exception: If an error occurs during the vector search, it is caught and printed, then an empty list is returned.

### `def _row_to_context(self, row: SymbolRow, method: str, score: float) -> CodeContext:`
*retrieval/hybrid_retriever.py:209*

Converts a SymbolRow to a CodeContext object.

Parameters:
- row (SymbolRow): The symbol row to convert.
- method (str): The retrieval method used.
- score (float): The retrieval score associated with the row.

Returns:
CodeContext: A CodeContext object populated with data from the symbol row and additional metadata.

Raises:
No specific exceptions are raised by this function.
