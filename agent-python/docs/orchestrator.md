# `orchestrator.py`

This module provides an orchestrator for managing a multi-agent pipeline aimed at generating comprehensive reports and documentation. The primary public API includes the `OrchestratorAgent` class, which initializes with a retriever and maximum number of workers, and its `run` method to execute the process. Key functions like `_run_worker`, `_plan_depth`, `_depth_to_params`, `_format_findings`, `_synthesise`, `_extract_tag`, and `_save` support this orchestration by handling worker execution, planning depth, parameter conversion, finding formatting, synthesis using a 14B model, HTML tag extraction, and file saving respectively. The module relies on dependencies such as threading for concurrent processing and possibly external libraries for model execution and HTML parsing.

## Classes

### `OrchestratorAgent`
Coordinates the full multi-agent pipeline:
  1. Plans review depth using the 14B model.
  2. Spins up 10 WorkerAgents in parallel thread pool.
  3. Collects all Findings.
  4. Unloads worker model from VRAM.
  5. Synthesises a comprehensive review with the 14B model.
  6. Saves review.md and documentation.md.

Methods: `__init__`, `run`, `_run_worker`, `_plan_depth`, `_depth_to_params`, `_format_findings`, `_synthesise`, `_extract_tag`, `_save`

## Functions

### `def __init__(self, retriever: HybridRetriever, max_workers: int=1):`
*D:\CodeSentinel\agent-python\core\orchestrator.py:84*

Initializes a new instance of the class with a given retriever and maximum number of workers. Sets up an LLM using specified parameters.

Parameters:
- retriever (HybridRetriever): The retriever to be used.
- max_workers (int, optional): Maximum number of worker threads. Defaults to 1.

Return value: None

Raises:
- TypeError: If the retriever is not an instance of HybridRetriever or max_workers is not an integer.
- ValueError: If max_workers is less than 1.

### `def run(self, user_request: str):`
*D:\CodeSentinel\agent-python\core\orchestrator.py:93*

Runs the orchestrator process to generate a final report and documentation based on user input.

Parameters:
- `user_request` (str): The request from the user for which the report and documentation will be generated.

Returns:
- Tuple[str, str]: A tuple containing the content of the review markdown file and the documentation markdown file.

Raises:
- Exception: If any worker fails during execution, an error message is printed but no exception is raised to halt the process.

### `@staticmethod`
*D:\CodeSentinel\agent-python\core\orchestrator.py:159*

Thread target — creates and runs a single WorkerAgent.

### `def _plan_depth(self, user_request: str) -> int:`
*D:\CodeSentinel\agent-python\core\orchestrator.py:175*

Determines the depth of planning based on a user request.

Parameters:
- user_request (str): The input request from the user.

Returns:
int: An integer representing the planning depth, defaults to 2 if an error occurs.

Raises:
Exception: Any exception that occurs during processing is caught and ignored, defaulting to a return value of 2.

### `@staticmethod`
*D:\CodeSentinel\agent-python\core\orchestrator.py:186*

Converts a depth level to corresponding parameters. Parameters: depth (int) - the depth level of the operation. Returns: A tuple containing two integers representing the parameters for the given depth. Raises: None.

### `@staticmethod`
*D:\CodeSentinel\agent-python\core\orchestrator.py:190*

Convert Finding objects into a readable block for the synthesis prompt.

### `def _synthesise(self, user_request: str, formatted_findings: str):`
*D:\CodeSentinel\agent-python\core\orchestrator.py:211*

Run the 14B model on all aggregated findings and return (review, docs).

### `@staticmethod`
*D:\CodeSentinel\agent-python\core\orchestrator.py:230*

Extracts the content of a specified HTML tag from a given text.

Parameters:
    text (str): The input text containing HTML tags.
    tag (str): The name of the HTML tag to extract content from.

Return value:
    str: The content inside the specified HTML tag, stripped of leading and trailing whitespace. Returns an empty string if the tag is not found.

Raises:
    None

### `@staticmethod`
*D:\CodeSentinel\agent-python\core\orchestrator.py:236*

Saves the given content to a file. If the content is empty, it skips saving and prints a message.

Parameters:
- filename: str - The name of the file to save the content to.
- content: str - The content to be saved in the file.

Return value:
None

Raises:
No exceptions are raised by this function.

## Static Analysis Warnings

- **[LOW]** line 93: `run` has no return type annotation.
- **[LOW]** line 186: `_depth_to_params` has no return type annotation.
- **[LOW]** line 211: `_synthesise` has no return type annotation.
- **[LOW]** line 236: `_save` has no return type annotation.
