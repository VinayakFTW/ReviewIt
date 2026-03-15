# `orchestrator.py`

This module defines an `OrchestratorAgent` class that coordinates a multi-agent pipeline to handle user requests by planning the depth of review, executing tasks, and synthesizing results. The public API includes the `__init__`, `run`, and `_run_worker` methods. Key dependencies include threading for worker management and language models for planning and synthesis. The module also provides utility functions like `_plan_depth`, `_depth_to_params`, `_format_findings`, `_synthesise`, `_extract_tag`, and `_save`.

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

### `def __init__(self, max_workers: int=1):`
*core/orchestrator.py:89*

Initializes a new instance of the class with the specified number of maximum workers and sets up a language learning model (LLM) for chat operations.

Parameters:
- max_workers: int = 1 - The maximum number of worker threads to use. Defaults to 1 if not provided.

Return value:
None

Raises:
TypeError - If max_workers is not an integer.
ValueError - If max_workers is less than 1.

### `def run(self, user_request: str, memory: MemoryManager):`
*core/orchestrator.py:97*

Runs the orchestrator process to handle a user request by planning depth, executing parallel workers, synthesizing findings with a large model, and saving output files.

Parameters:
- `user_request` (str): The request from the user.
- `memory` (MemoryManager): An instance of MemoryManager for managing memory.

Returns:
- Tuple[str, str]: A tuple containing the synthesized review markdown and documentation markdown.

Raises:
- Exception: If any worker fails during execution.

### `@staticmethod`
*core/orchestrator.py:158*

Thread target — creates and runs a single WorkerAgent.

### `def _plan_depth(self, user_request: str) -> int:`
*core/orchestrator.py:174*

Determines the depth of planning based on a user request. Invokes an LLM with a formatted prompt and extracts a digit from the response, returning it as an integer. If an exception occurs, returns 2 as the default value.

Parameters:
- user_request (str): The input request from the user.

Returns:
int: The determined depth of planning, ranging from 1 to 3.

Raises:
Exception: Any unexpected error during the process, though it is caught and handled by returning a default value.

### `@staticmethod`
*core/orchestrator.py:185*

Converts a depth level to corresponding parameters. Parameters: depth (int) - the depth level of the operation. Returns: A tuple containing two integers representing the parameters for the given depth. Raises: None.

### `@staticmethod`
*core/orchestrator.py:189*

Convert Finding objects into a readable block for the synthesis prompt.

### `def _synthesise(self, user_request: str, formatted_findings: str):`
*core/orchestrator.py:210*

Run the 14B model on all aggregated findings and return (review, docs).

### `@staticmethod`
*core/orchestrator.py:229*

Extracts the content of a specified HTML tag from a given text.

Parameters:
text (str): The input text containing HTML tags.
tag (str): The name of the HTML tag to extract content from.

Return value:
str: The content inside the specified HTML tag, stripped of leading and trailing whitespace. Returns an empty string if the tag is not found.

Raises:
None

### `@staticmethod`
*core/orchestrator.py:235*

Saves the given content to a file. If the content is empty, it skips saving and prints a message.

Parameters:
- filename: str - The name of the file to save the content to.
- content: str - The content to be saved in the file.

Return value:
None

Raises:
No exceptions are raised by this function.

## Static Analysis Warnings

- **[LOW]** line 97: `run` has no return type annotation.
- **[LOW]** line 185: `_depth_to_params` has no return type annotation.
- **[LOW]** line 210: `_synthesise` has no return type annotation.
- **[LOW]** line 235: `_save` has no return type annotation.
