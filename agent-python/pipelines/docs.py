"""
pipelines/docs.py

Incremental Documentation Pipeline.

Generates documentation hierarchically:
    1. Function-level: docstring + parameter description for each changed function.
    2. Module-level:   summary of what the module does, its public API.
    3. Architecture:   top-level view updated when module structure changes.

Documentation is generated INCREMENTALLY — only changed files are re-documented.
A git hook (or CI step) triggers this pipeline after each push.

Git change detection requires `gitpython`.
If the repo is not a git repo, falls back to documenting ALL files.
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple

from langchain_ollama import ChatOllama

from ingest.ast_parser import parse_file, FileAnalysis, FunctionSymbol, ClassSymbol
from retrieval.hybrid_retriever import HybridRetriever
from core.model_manager import ORCHESTRATOR_MODEL
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich import print

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_FN_DOC_PROMPT = """Write a concise docstring for this Python function.
Include: what it does, parameters (with types if missing), return value, raises.
Output ONLY the docstring text, no triple-quotes, no preamble.

{source}"""

_MODULE_SUMMARY_PROMPT = """Analyse this Python module and write a concise module-level docstring.
Include: purpose, public API (key classes/functions), important dependencies.
Output ONLY the docstring text, no triple-quotes, no preamble.
Limit to 8 sentences.

File: {filepath}
Contents overview:
{overview}"""

_ARCHITECTURE_PROMPT = """Based on the module summaries below, write a high-level architecture
overview document in Markdown. Include:
- System purpose
- Module responsibilities (one bullet per module)
- Data flow between modules
- External dependencies

Module summaries:
{module_summaries}"""


# ---------------------------------------------------------------------------
# Git change detection
# ---------------------------------------------------------------------------

def detect_changed_files(repo_path: str, since: str = "HEAD~1") -> Optional[Set[str]]:
    """
    Return set of .py files changed since `since` commit.
    Returns None if gitpython is not installed or repo is not a git repo.
    """
    try:
        import git
        repo = git.Repo(repo_path, search_parent_directories=True)
        diff = repo.head.commit.diff(since)
        changed = set()
        for item in diff:
            if item.a_path and item.a_path.endswith(".py"):
                changed.add(os.path.join(repo_path, item.a_path))
            if item.b_path and item.b_path.endswith(".py"):
                changed.add(os.path.join(repo_path, item.b_path))
        return changed
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DocsPipeline:
    """
    Generates and incrementally updates documentation for the codebase.
    Output directory: docs/ (configurable).
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        source_dir: str,
        docs_dir: str = "docs",
    ):
        self.retriever = retriever
        self.source_dir = source_dir
        self.docs_dir = docs_dir
        self.llm = ChatOllama(
            model=ORCHESTRATOR_MODEL,
            temperature=0.15,
            keep_alive="10m",
        )
        Path(docs_dir).mkdir(parents=True, exist_ok=True)
        # Cache: filepath → module summary (to avoid re-running for unchanged files)
        self._summary_cache_path = os.path.join(docs_dir, ".summary_cache.json")
        self._summary_cache: Dict[str, str] = self._load_cache()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def run_incremental(self, since: str = "HEAD~1") -> None:
        """
        Detect changed files and update only their documentation.
        Called by git post-push hook.
        """
        print(f"\n[Docs] Detecting changes since '{since}'...")
        changed = detect_changed_files(self.source_dir, since=since)

        if changed is None:
            print("[Docs] Not a git repo or gitpython not installed. Falling back to full run.")
            self.run_full()
            return

        if not changed:
            print("[Docs] No Python files changed. Nothing to document.")
            return

        print(f"[Docs] {len(changed)} file(s) changed: {[os.path.basename(f) for f in changed]}")
        self._document_files(list(changed), update_architecture=True)

    def run_full(self) -> None:
        """
        Document the entire codebase from scratch.
        Skips files whose summary is already cached.
        """
        print("\n[Docs] Full documentation run...")
        all_files = list(Path(self.source_dir).glob("**/*.py"))
        all_files = [
            str(f) for f in all_files
            if not any(p in f.parts for p in (".venv", "venv", "__pycache__", "site-packages","dist","build"))
        ]
        print(f"[Docs] {len(all_files)} Python files to document.")
        self._document_files(all_files, update_architecture=True)

    # ------------------------------------------------------------------
    # Internal documentation stages
    # ------------------------------------------------------------------

    def _document_files(self, filepaths: List[str], update_architecture: bool):
        console = Console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task("[cyan]Documenting Codebase...", total=len(filepaths))

            for filepath in filepaths:
                file_name = os.path.basename(filepath)
                progress.update(task, description=f"[cyan]Documenting {file_name}...")
                
                analysis = parse_file(filepath)
                if analysis.parse_error:
                    progress.console.print(f"  [red]✖[/red] Skipping {file_name}: {analysis.parse_error}")
                    progress.advance(task)
                    continue
                
                #Function level docs
                fn_docs = self._document_functions(analysis)

                #Module level docs
                module_summary = self._document_module(analysis, fn_docs)

                # Update cache and write docs for this module
                self._summary_cache[filepath] = module_summary
                self._save_cache()
                self._write_module_doc(filepath, analysis, fn_docs, module_summary)
                
                progress.advance(task)

        # update the architecture overview if any files were changed (or if it was a full run)
        if update_architecture:
            with console.status("[magenta]Regenerating architecture overview...[/magenta]"):
                self._update_architecture_doc()
            console.print("  [green]✔[/green] Architecture updated.")

    def _document_functions(self, analysis: FileAnalysis) -> Dict[str, str]:
        """Generate docstrings for functions that lack them."""
        fn_docs: Dict[str, str] = {}
        for fn in analysis.functions:
            if fn.docstring:
                # Already documented — preserve existing
                fn_docs[fn.qualified_name] = fn.docstring
                continue
            if len(fn.source) < 20:
                continue  # Too short to bother

            try:
                prompt = _FN_DOC_PROMPT.format(source=fn.source[:3000])
                doc = self.llm.invoke([("human", prompt)]).content.strip()
                fn_docs[fn.qualified_name] = doc
            except Exception as e:
                print(f"    [Docs] Could not document {fn.qualified_name}: {e}")
                fn_docs[fn.qualified_name] = ""
        return fn_docs

    def _document_module(
        self, analysis: FileAnalysis, fn_docs: Dict[str, str]
    ) -> str:
        """Generate a module-level summary."""
        overview_lines = []
        for fn in analysis.functions[:10]:  # top 10 functions
            doc = fn_docs.get(fn.qualified_name, "")
            first_line = doc.split("\n")[0] if doc else "undocumented"
            overview_lines.append(f"  - {fn.qualified_name}: {first_line[:80]}")
        for cls in analysis.classes[:5]:
            overview_lines.append(f"  - class {cls.name}: {cls.docstring[:80] or 'undocumented'}")

        overview = "\n".join(overview_lines) or "  (no symbols)"
        try:
            prompt = _MODULE_SUMMARY_PROMPT.format(
                filepath=os.path.basename(analysis.path),
                overview=overview,
            )
            return self.llm.invoke([("human", prompt)]).content.strip()
        except Exception as e:
            return f"Error generating module summary: {e}"

    def _update_architecture_doc(self) -> None:
        """Regenerate top-level architecture.md from all cached module summaries."""
        if not self._summary_cache:
            return
        print("\n[Docs] Updating architecture overview...")

        summaries_block = "\n\n".join(
            f"### {os.path.basename(fp)}\n{summary}"
            for fp, summary in self._summary_cache.items()
        )
        try:
            prompt = _ARCHITECTURE_PROMPT.format(module_summaries=summaries_block[:16_000])
            arch_doc = self.llm.invoke([("human", prompt)]).content.strip()
        except Exception as e:
            arch_doc = f"# Architecture\n\nError: {e}"

        arch_path = os.path.join(self.docs_dir, "architecture.md")
        with open(arch_path, "w", encoding="utf-8") as f:
            f.write(arch_doc)
        print(f"  [Docs] Saved → {arch_path}")

    def _write_module_doc(
        self,
        filepath: str,
        analysis: FileAnalysis,
        fn_docs: Dict[str, str],
        module_summary: str,
    ) -> None:
        """Write per-module markdown doc file."""
        module_name = Path(filepath).stem
        out_path = os.path.join(self.docs_dir, f"{module_name}.md")

        lines = [
            f"# `{os.path.basename(filepath)}`\n",
            f"{module_summary}\n",
        ]

        if analysis.classes:
            lines.append("## Classes\n")
            for cls in analysis.classes:
                lines.append(f"### `{cls.name}`")
                if cls.bases:
                    lines.append(f"*Inherits: {', '.join(cls.bases)}*\n")
                lines.append(cls.docstring or "*No class docstring.*")
                lines.append(f"\nMethods: `{'`, `'.join(cls.methods)}`\n")

        if analysis.functions:
            lines.append("## Functions\n")
            for fn in analysis.functions:
                lines.append(f"### `{fn.signature}`")
                lines.append(f"*{fn.file}:{fn.line_start}*\n")
                doc = fn_docs.get(fn.qualified_name, "")
                lines.append(doc or "*No documentation generated.*")
                lines.append("")

        if analysis.static_findings:
            lines.append("## Static Analysis Warnings\n")
            for finding in analysis.static_findings:
                lines.append(
                    f"- **[{finding.severity}]** line {finding.line}: "
                    f"{finding.message}"
                )
            lines.append("")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"    Saved → {out_path}")

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self._summary_cache_path):
            with open(self._summary_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        with open(self._summary_cache_path, "w", encoding="utf-8") as f:
            json.dump(self._summary_cache, f, indent=2)
