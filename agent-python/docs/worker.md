# `worker.py`

This module provides the `WorkerAgent` class, which is responsible for processing user requests to generate analysis findings. The public API includes the `run` method, which initiates the analysis process. Key dependencies include language models for code snippet analysis and utilities for parsing and refining search queries. The module also defines a private helper function `_analyse` for analyzing code snippets and a `Finding` class for encapsulating individual analysis results.

## Classes

### `Finding`
*No class docstring.*

Methods: ``

### `WorkerAgent`
*No class docstring.*

Methods: `__init__`, `run`, `_short`, `_generate_queries`, `_refine_queries`, `_analyse`, `_parse`, `_parse_block`

## Functions

### `def __init__(self, specialization, retriever, chunks_per_search=6, max_rounds=3):`
*core/worker.py:68*

Initializes a new instance of the class with the given parameters.

Parameters:
- specialization (str): The specialization area for the model.
- retriever: The document retrieval system to use.
- chunks_per_search (int, optional): Number of chunks to search per round. Defaults to 6.
- max_rounds (int, optional): Maximum number of rounds for searching. Defaults to 3.

Return value:
None

Raises:
None

### `def run(self, user_request: str) -> List[Finding]:`
*core/worker.py:75*

Runs the analysis process on a user request to generate a list of findings.

Parameters:
- user_request (str): The input query or request from the user.

Returns:
List[Finding]: A list of Finding objects containing the results of the analysis.

Raises:
None.

### `def _short(self):`
*core/worker.py:108*

Returns a string containing the first two words of the specialization attribute. No parameters. Returns a string. Raises no exceptions.

### `def _generate_queries(self, user_request):`
*core/worker.py:111*

Generates a list of up to three search queries based on the user's request and the model's specialization. If an exception occurs, returns a default query derived from the model's specialization.

Parameters:
- `user_request` (str): The user's input or request for which search queries are needed.

Return value:
- List[str]: A list of up to three generated search queries, or a single default query if an error occurs.

Raises:
- Exception: Any exception that may occur during the generation process is caught and handled gracefully.

### `def _refine_queries(self, queries, findings):`
*core/worker.py:121*

Refines a list of search queries by appending up to six unique keywords extracted from the descriptions of given findings.

Parameters:
- `queries` (list of str): The original search queries.
- `findings` (list of objects): Objects with a 'description' attribute containing relevant keywords.

Returns:
- list of str: The refined search queries with additional keywords appended.

Raises:
- AttributeError: If any finding object does not have a 'description' attribute.

### `def _analyse(self, snippets, contexts):`
*core/worker.py:128*

Analyzes a list of code snippets using a language model. Parameters: snippets (list), contexts (list). Returns: A parsed list of issues or an empty list if no issues are found. Raises: Prints an error message and returns an empty list if an exception occurs during the analysis.

### `def _parse(self, raw, contexts):`
*core/worker.py:140*

Parses a raw string to extract issue blocks and returns a list of parsed findings.

Parameters:
- raw (str): The raw input string containing issue blocks.
- contexts: Additional context information used during parsing.

Returns:
List of parsed findings from the raw input.

Raises:
- ValueError: If an issue block is malformed and cannot be parsed.

### `def _parse_block(self, block, contexts) -> Optional[Finding]:`
*core/worker.py:151*

Parses a block of text to extract finding details and returns a Finding object.

Parameters:
- block (str): The block of text to parse.
- contexts (List[Context]): A list of Context objects for preview generation.

Returns:
Optional[Finding]: A Finding object if the description is found, otherwise None.

Raises:
None

## Static Analysis Warnings

- **[LOW]** line 108: `_short` has no return type annotation.
- **[LOW]** line 111: `_generate_queries` has no return type annotation.
- **[LOW]** line 121: `_refine_queries` has no return type annotation.
- **[LOW]** line 128: `_analyse` has no return type annotation.
- **[LOW]** line 140: `_parse` has no return type annotation.
