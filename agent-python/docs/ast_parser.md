# `ast_parser.py`

This module provides functionality for parsing Python source code and performing static analysis. It includes key classes such as `StaticAnalyser`, `FunctionSymbol`, `ClassSymbol`, `ImportEdge`, `StaticFinding`, and `FileAnalysis`. The public API consists of functions like `parse_file` and `parse_directory` for analyzing individual files or directories, respectively. Important dependencies include the Python `ast` module for abstract syntax tree parsing. The module also contains utility functions such as `_get_source_segment`, `_unparse_annotation`, `_build_signature`, `_collect_calls`, and `_get_decorators` to support the main analysis tasks.

## Classes

### `FunctionSymbol`
*No class docstring.*

Methods: ``

### `ClassSymbol`
*No class docstring.*

Methods: ``

### `ImportEdge`
*No class docstring.*

Methods: ``

### `StaticFinding`
A finding produced by AST-level static analysis (no LLM required).

Methods: ``

### `FileAnalysis`
*No class docstring.*

Methods: ``

### `StaticAnalyser`
*Inherits: ast.NodeVisitor*

Walks the AST and emits StaticFinding objects for known bad patterns.

Methods: `__init__`, `_emit`, `visit_ExceptHandler`, `visit_FunctionDef`, `visit_Call`, `visit_Assign`, `visit_JoinedStr`, `visit_Import`, `visit_ImportFrom`

## Functions

### `def _get_source_segment(source_lines: List[str], start: int, end: int) -> str:`
*ingest/ast_parser.py:88*

Extract lines [start, end] (1-indexed) from source.

### `def _unparse_annotation(node) -> str:`
*ingest/ast_parser.py:93*

Unparses an AST node into a string representation of its source code. If an exception occurs during unparsing, returns "...". Parameters: node (ast.AST): The AST node to unparse. Returns: str: The string representation of the AST node or "..." if an error occurred. Raises: None

### `def _build_signature(node: ast.FunctionDef, source_lines: List[str]) -> str:`
*ingest/ast_parser.py:100*

Reconstruct def line(s) from AST rather than regex.

### `def _collect_calls(func_node: ast.AST) -> List[str]:`
*ingest/ast_parser.py:112*

Walk function body and collect all called names.

### `def _get_decorators(node: ast.FunctionDef) -> List[str]:`
*ingest/ast_parser.py:124*

Extracts decorator names from an AST FunctionDef node.

Parameters:
- node (ast.FunctionDef): The function definition node to extract decorators from.

Returns:
List[str]: A list of decorator names as strings.

Raises:
None.

### `def parse_file(filepath: str) -> FileAnalysis:`
*ingest/ast_parser.py:287*

Parse a single Python file. Returns a FileAnalysis with extracted symbols
and any static findings. Never raises — stores errors in FileAnalysis.parse_error.

### `def parse_directory(source_dir: str, glob: str='**/*.py') -> List[FileAnalysis]:`
*ingest/ast_parser.py:396*

Parse every Python file under source_dir. Returns a list of FileAnalysis.
Files that fail to parse have their error stored — they don't crash the run.

### `def __init__(self, source_lines: List[str], filepath: str):`
*ingest/ast_parser.py:153*

Initializes a new instance of the class with the given source lines and file path. Sets up internal lists for findings and function stack. Parameters: source_lines (List[str]): The list of source code lines. filepath (str): The path to the source file. Returns: None Raises: No exceptions are raised by this method.

### `def _emit(self, line: int, severity: str, rule: str, msg: str, suggestion: str):`
*ingest/ast_parser.py:161*

Emits a static code analysis finding.

Parameters:
- line (int): The line number where the issue was found.
- severity (str): The severity level of the issue (e.g., "error", "warning").
- rule (str): The rule that was violated.
- msg (str): The message describing the issue.
- suggestion (str): A suggested fix for the issue.

Return value:
None

Raises:
- ValueError: If any of the input parameters are invalid.

### `def visit_ExceptHandler(self, node: ast.ExceptHandler):`
*ingest/ast_parser.py:173*

Visits an ExceptHandler node in the AST. Checks for a bare except clause and emits a warning if found. Parameters: node (ast.ExceptHandler). Returns: None. Raises: No exceptions are raised by this function.

### `def visit_FunctionDef(self, node: ast.FunctionDef):`
*ingest/ast_parser.py:183*

Visits a function definition node in the AST, checking for various code quality issues such as long functions, mutable default arguments, and missing return annotations. Emits warnings for these issues. Parameters: node (ast.FunctionDef) - The function definition node to visit. Returns: None Raises: None

### `def visit_Call(self, node: ast.Call):`
*ingest/ast_parser.py:218*

Visits an AST Call node to check for security issues such as the use of eval/exec and os.system. Emits warnings if these functions are detected. Parameters: node (ast.Call). Returns: None. Raises: No exceptions raised.

### `def visit_Assign(self, node: ast.Assign):`
*ingest/ast_parser.py:242*

Visits an assignment node to check for hardcoded secrets. Parameters: node (ast.Assign). Returns: None. Raises: No exceptions raised.

### `def visit_JoinedStr(self, node: ast.JoinedStr):`
*ingest/ast_parser.py:254*

Visits a JoinedStr node to check for potential SQL injection vulnerabilities. If the unparsed string matches the SQL pattern, emits a high-severity warning. Parameters: node (ast.JoinedStr). Returns: None. Raises: Exception if ast.unparse fails.

### `def visit_Import(self, node: ast.Import):`
*ingest/ast_parser.py:268*

Visits an import node in the abstract syntax tree (AST).

Parameters:
node (ast.Import): The import node to visit.

Return value:
None

Raises:
N/A

### `def visit_ImportFrom(self, node: ast.ImportFrom):`
*ingest/ast_parser.py:272*

Visits an ImportFrom node in the AST. Checks for wildcard imports and emits a warning if found. Parameters: node (ast.ImportFrom). Returns: None. Raises: None.

## Static Analysis Warnings

- **[LOW]** line 161: `_emit` has no return type annotation.
- **[LOW]** line 173: `visit_ExceptHandler` has no return type annotation.
- **[LOW]** line 183: `visit_FunctionDef` has no return type annotation.
- **[LOW]** line 218: `visit_Call` has no return type annotation.
- **[LOW]** line 242: `visit_Assign` has no return type annotation.
- **[LOW]** line 254: `visit_JoinedStr` has no return type annotation.
- **[LOW]** line 268: `visit_Import` has no return type annotation.
- **[LOW]** line 272: `visit_ImportFrom` has no return type annotation.
- **[LOW]** line 287: `parse_file` is 106 lines long (limit: 60).
