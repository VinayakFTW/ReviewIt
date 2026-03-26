# `worker.py`

This module provides the `WorkerAgent` class, which is responsible for processing user requests by generating search queries, analyzing code snippets, and parsing results. The public API includes the `run` method to initiate the analysis process. Key dependencies include language models for analysis and utilities for parsing text. The module also defines a `Finding` class to encapsulate parsed issue details.

## Classes

### `Finding`
*No class docstring.*

Methods: ``

### `WorkerAgent`
*No class docstring.*

Methods: `__init__`, `run`, `_short`, `_generate_queries`, `_refine_queries`, `_analyse`, `_parse`, `_parse_block`

## Functions

### `def __init__(self, specialization, retriever, chunks_per_search=6, max_rounds=3, db_lock=None):`
*D:\CodeSentinel\agent-python\core\worker.py:65*

Initializes a new instance of the class with the given parameters.

Parameters:
- specialization (str): The specialization area for the instance.
- retriever: The retriever object used to fetch data.
- chunks_per_search (int, optional): Number of chunks to search per round. Defaults to 6.
- max_rounds (int, optional): Maximum number of rounds allowed. Defaults to 3.
- db_lock (threading.Lock, optional): Lock for database operations. If not provided, a new lock is created.

Returns:
None

Raises:
None

### `def run(self, user_request: str) -> List[Finding]:`
*D:\CodeSentinel\agent-python\core\worker.py:73*

Runs the analysis process for a given user request.

Parameters:
- `user_request` (str): The input query or request from the user.

Returns:
- List[Finding]: A list of findings generated from the analysis.

Raises:
- None explicitly documented.

### `def _short(self):`
*D:\CodeSentinel\agent-python\core\worker.py:109*

Returns a string containing the first two words of the `specialization` attribute. No parameters. Returns a string. Raises no exceptions.

### `def _generate_queries(self, user_request):`
*D:\CodeSentinel\agent-python\core\worker.py:112*

Generates a list of up to three search queries based on the user's request and the model's specialization. If an exception occurs, returns a default query derived from the model's specialization.

Parameters:
- `user_request` (str): The user's input or request for which search queries are needed.

Return value:
- List[str]: A list of up to three generated search queries, or a single default query if an error occurs.

Raises:
- None: Any exceptions are caught and handled internally, returning a default value instead.

### `def _refine_queries(self, queries, findings):`
*D:\CodeSentinel\agent-python\core\worker.py:122*

Refines a list of search queries by appending up to six unique keywords extracted from the descriptions of given findings.

Parameters:
- `queries` (list): A list of original search queries.
- `findings` (list): A list of findings, each with a 'description' attribute.

Returns:
- list: A new list of refined queries with additional keywords appended.

Raises:
- AttributeError: If any finding object does not have a 'description' attribute.

### `def _analyse(self, snippets, contexts):`
*D:\CodeSentinel\agent-python\core\worker.py:129*

Analyzes a list of code snippets using a language model. Parameters: snippets (list), contexts (list). Returns a parsed result or an empty list if no issues are found. Raises exceptions from the LLM invocation.

### `def _parse(self, raw, contexts):`
*D:\CodeSentinel\agent-python\core\worker.py:141*

Parses a raw string to extract issue blocks and returns a list of parsed findings.

Parameters:
- raw (str): The raw input string containing issue blocks.
- contexts: Additional context information used during parsing.

Returns:
List of parsed findings from the raw input.

Raises:
- ValueError: If an issue block is malformed and cannot be parsed.

### `def _parse_block(self, block, contexts) -> Optional[Finding]:`
*D:\CodeSentinel\agent-python\core\worker.py:152*

Parses a block of text to extract finding details and returns a Finding object if valid. Parameters: block (str): The text block to parse. contexts (list): A list of context objects. Returns: Optional[Finding]: A Finding object with parsed details or None if no description is found. Raises: No specific exceptions are raised by this function.

## Static Analysis Warnings

- **[LOW]** line 109: `_short` has no return type annotation.
- **[LOW]** line 112: `_generate_queries` has no return type annotation.
- **[LOW]** line 122: `_refine_queries` has no return type annotation.
- **[LOW]** line 129: `_analyse` has no return type annotation.
- **[LOW]** line 141: `_parse` has no return type annotation.
