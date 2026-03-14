"""
ingest/ast_parser.py

Parses Python source files using the built-in `ast` module to extract:
  - Functions and methods (signature, docstring, line range, calls made)
  - Classes (bases, methods)
  - Import relationships
  - Module-level constants / globals

Also runs zero-dependency static analysis checks directly on the AST.
These checks fire before any LLM is involved — they are cheap and reliable.
"""

import ast
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FunctionSymbol:
    name: str
    qualified_name: str          # ClassName.method_name or just function_name
    file: str
    line_start: int
    line_end: int
    signature: str               # def foo(x: int, y: str = "a") -> bool:
    docstring: str
    calls: List[str]             # names of functions/methods called inside body
    is_method: bool
    class_name: Optional[str]
    decorators: List[str]
    has_return_annotation: bool
    source: str                  # full source text of this function


@dataclass
class ClassSymbol:
    name: str
    file: str
    line_start: int
    line_end: int
    docstring: str
    bases: List[str]
    methods: List[str]           # method names (FunctionSymbol.name)
    source: str


@dataclass
class ImportEdge:
    from_file: str
    imported_module: str         # what was imported
    imported_names: List[str]    # specific names, empty = whole module


@dataclass
class StaticFinding:
    """A finding produced by AST-level static analysis (no LLM required)."""
    file: str
    line: int
    severity: str                # HIGH / MEDIUM / LOW
    rule: str                    # short rule ID, e.g. "bare-except"
    message: str
    suggestion: str


@dataclass
class FileAnalysis:
    path: str
    functions: List[FunctionSymbol] = field(default_factory=list)
    classes: List[ClassSymbol] = field(default_factory=list)
    imports: List[ImportEdge] = field(default_factory=list)
    static_findings: List[StaticFinding] = field(default_factory=list)
    parse_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_source_segment(source_lines: List[str], start: int, end: int) -> str:
    """Extract lines [start, end] (1-indexed) from source."""
    return "\n".join(source_lines[start - 1 : end])


def _unparse_annotation(node) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def _build_signature(node: ast.FunctionDef, source_lines: List[str]) -> str:
    """Reconstruct def line(s) from AST rather than regex."""
    try:
        # ast.unparse gives a clean signature without the body
        reconstructed = ast.unparse(node)
        # Take only the def line up to the colon
        first_line = reconstructed.split("\n")[0]
        return first_line
    except Exception:
        return f"def {node.name}(...)"


def _collect_calls(func_node: ast.AST) -> List[str]:
    """Walk function body and collect all called names."""
    calls = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    return list(set(calls))


def _get_decorators(node: ast.FunctionDef) -> List[str]:
    names = []
    for d in node.decorator_list:
        if isinstance(d, ast.Name):
            names.append(d.id)
        elif isinstance(d, ast.Attribute):
            names.append(f"{ast.unparse(d)}")
    return names


# ---------------------------------------------------------------------------
# Static analysis rules (all run on the AST, no LLM)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = re.compile(
    r"(password|passwd|secret|api[_-]?key|token|auth[_-]?key|private[_-]?key"
    r"|access[_-]?key|aws[_-]?secret|client[_-]?secret)",
    re.IGNORECASE,
)
_SQL_PATTERN = re.compile(
    r"(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s", re.IGNORECASE
)


class StaticAnalyser(ast.NodeVisitor):
    """
    Walks the AST and emits StaticFinding objects for known bad patterns.
    """

    def __init__(self, source_lines: List[str], filepath: str):
        self.source_lines = source_lines
        self.filepath = filepath
        self.findings: List[StaticFinding] = []
        self._func_stack: List[ast.FunctionDef] = []

    # -- Rule helpers -------------------------------------------------------

    def _emit(self, line: int, severity: str, rule: str, msg: str, suggestion: str):
        self.findings.append(StaticFinding(
            file=self.filepath,
            line=line,
            severity=severity,
            rule=rule,
            message=msg,
            suggestion=suggestion,
        ))

    # -- Visitors -----------------------------------------------------------

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # R001: bare except
        if node.type is None:
            self._emit(
                node.lineno, "MEDIUM", "bare-except",
                "Bare `except:` catches ALL exceptions including SystemExit and KeyboardInterrupt.",
                "Catch specific exceptions: `except (ValueError, TypeError) as e:`",
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._func_stack.append(node)
        line_count = (node.end_lineno or node.lineno) - node.lineno

        # R002: function too long
        if line_count > 60:
            self._emit(
                node.lineno, "LOW", "long-function",
                f"`{node.name}` is {line_count} lines long (limit: 60).",
                "Extract sub-routines to keep each function focused.",
            )

        # R003: mutable default argument
        for default in node.args.defaults + node.args.kw_defaults:
            if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self._emit(
                    node.lineno, "HIGH", "mutable-default",
                    f"`{node.name}` uses a mutable default argument (list/dict/set).",
                    "Use `None` as default and initialise inside the function body.",
                )
                break

        # R004: missing return annotation
        if node.returns is None and node.name != "__init__":
            self._emit(
                node.lineno, "LOW", "missing-return-annotation",
                f"`{node.name}` has no return type annotation.",
                "Add `-> ReturnType` annotation for better static analysis.",
            )

        self.generic_visit(node)
        self._func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call):
        # R005: eval / exec usage
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self._emit(
                node.lineno, "HIGH", "eval-exec",
                f"Use of `{node.func.id}()` is a code-injection risk.",
                "Avoid dynamic code execution; use explicit logic instead.",
            )

        # R006: os.system — prefer subprocess
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "system"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
        ):
            self._emit(
                node.lineno, "MEDIUM", "os-system",
                "`os.system()` is a shell-injection risk and harder to handle errors from.",
                "Use `subprocess.run([...], check=True)` instead.",
            )

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # R007: hardcoded secrets — check variable names assigned string literals
        for target in node.targets:
            if isinstance(target, ast.Name) and _SECRET_PATTERNS.search(target.id):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self._emit(
                        node.lineno, "HIGH", "hardcoded-secret",
                        f"Possible hardcoded secret in variable `{target.id}`.",
                        "Load secrets from environment variables or a secrets manager.",
                    )
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr):
        # R008: f-string that looks like SQL (potential injection)
        try:
            raw = ast.unparse(node)
        except Exception:
            raw = ""
        if _SQL_PATTERN.search(raw):
            self._emit(
                node.lineno, "HIGH", "sql-fstring",
                "SQL query constructed with an f-string — possible SQL injection.",
                "Use parameterised queries: `cursor.execute(sql, (param,))`",
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        # R009: wildcard-adjacent: warn on `import *` handled separately
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            if alias.name == "*":
                self._emit(
                    node.lineno, "LOW", "wildcard-import",
                    f"`from {node.module} import *` pollutes the namespace.",
                    "Import only the names you need.",
                )
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Main parsing function
# ---------------------------------------------------------------------------

def parse_file(filepath: str) -> FileAnalysis:
    """
    Parse a single Python file. Returns a FileAnalysis with extracted symbols
    and any static findings. Never raises — stores errors in FileAnalysis.parse_error.
    """
    analysis = FileAnalysis(path=filepath)

    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        analysis.parse_error = str(e)
        return analysis

    source_lines = source.splitlines()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        analysis.parse_error = f"SyntaxError: {e}"
        return analysis

    # -- Extract imports ---------------------------------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                analysis.imports.append(ImportEdge(
                    from_file=filepath,
                    imported_module=alias.name,
                    imported_names=[],
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            analysis.imports.append(ImportEdge(
                from_file=filepath,
                imported_module=module,
                imported_names=names,
            ))

    # -- Extract classes and functions ------------------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            method_names = [
                n.name for n in ast.walk(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n is not node
            ]
            docstring = ast.get_docstring(node) or ""
            bases = [ast.unparse(b) for b in node.bases]
            end = getattr(node, "end_lineno", node.lineno)
            analysis.classes.append(ClassSymbol(
                name=node.name,
                file=filepath,
                line_start=node.lineno,
                line_end=end,
                docstring=docstring,
                bases=bases,
                methods=method_names,
                source=_get_source_segment(source_lines, node.lineno, end),
            ))

    # Walk top-level and class bodies for functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            docstring = ast.get_docstring(node) or ""
            sig = _build_signature(node, source_lines)
            calls = _collect_calls(node)
            decorators = _get_decorators(node)

            # Determine if it's a method (parent is a ClassDef)
            # Simple heuristic: check if "self" or "cls" is first arg
            args = node.args.args
            is_method = bool(args) and args[0].arg in ("self", "cls")
            class_name: Optional[str] = None
            if is_method:
                # Try to find class name from the source context (look backwards)
                for i in range(node.lineno - 2, max(0, node.lineno - 30), -1):
                    line = source_lines[i].strip()
                    if line.startswith("class "):
                        class_name = line.split()[1].rstrip("(:")
                        break

            qname = f"{class_name}.{node.name}" if class_name else node.name

            analysis.functions.append(FunctionSymbol(
                name=node.name,
                qualified_name=qname,
                file=filepath,
                line_start=node.lineno,
                line_end=end,
                signature=sig,
                docstring=docstring,
                calls=calls,
                is_method=is_method,
                class_name=class_name,
                decorators=decorators,
                has_return_annotation=node.returns is not None,
                source=_get_source_segment(source_lines, node.lineno, end),
            ))

    # -- Static analysis ---------------------------------------------------
    analyser = StaticAnalyser(source_lines, filepath)
    analyser.visit(tree)
    analysis.static_findings = analyser.findings

    return analysis


def parse_directory(source_dir: str, glob: str = "**/*.py") -> List[FileAnalysis]:
    """
    Parse every Python file under source_dir. Returns a list of FileAnalysis.
    Files that fail to parse have their error stored — they don't crash the run.
    """
    results = []
    root = Path(source_dir)
    files = list(root.glob(glob))
    print(f"[ASTParser] Found {len(files)} Python files in '{source_dir}'.")

    for fp in files:
        # Skip venv / site-packages
        parts = fp.parts
        if any(p in (".venv", "venv", "__pycache__", "site-packages") for p in parts):
            continue
        analysis = parse_file(str(fp))
        results.append(analysis)

    errors = [a for a in results if a.parse_error]
    print(f"[ASTParser] Parsed {len(results) - len(errors)} files OK, "
          f"{len(errors)} with errors.")
    return results
