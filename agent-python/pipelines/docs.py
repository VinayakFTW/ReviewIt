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
        output_callback=None,
    ):
        self.retriever = retriever
        self.source_dir = source_dir
        self.docs_dir = docs_dir
        self.out = output_callback or print
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
        self.out(f"\n[Docs] Detecting changes since '{since}'...")
        changed = detect_changed_files(self.source_dir, since=since)

        if changed is None:
            self.out("[Docs] Not a git repo or gitpython not installed. Falling back to full run.")
            self.run_full()
            return

        if not changed:
            self.out("[Docs] No Python files changed. Nothing to document.")
            return

        self.out(f"[Docs] {len(changed)} file(s) changed: {[os.path.basename(f) for f in changed]}")
        self._document_files(list(changed), update_architecture=True)

    def run_full(self) -> None:
        """
        Document the entire codebase from scratch.
        Skips files whose summary is already cached.
        """
        self.out("\n[Docs] Full documentation run...")
        all_files = list(Path(self.source_dir).glob("**/*.py"))
        all_files = [
            str(f) for f in all_files
            if not any(p in f.parts for p in (".venv", "venv", "__pycache__", "site-packages","dist","build"))
        ]
        current_files_set = set(all_files)
        stale_keys = [k for k in self._summary_cache.keys() if k not in current_files_set]
        if stale_keys:
            self.out(f"  [Docs] Pruning {len(stale_keys)} deleted files from cache...")
            for k in stale_keys:
                del self._summary_cache[k]
                self._remove_module_doc(k)
            self._save_cache()

        self.out(f"[Docs] {len(all_files)} Python files to document.")
        self._document_files(all_files, update_architecture=True)

    # ------------------------------------------------------------------
    # Internal documentation stages
    # ------------------------------------------------------------------

    def _document_files(self, filepaths: List[str], update_architecture: bool):
        for filepath in filepaths:
            self.out(f"  [Docs] Documenting {os.path.basename(filepath)}...")

            if not os.path.exists(filepath):
                self.out(f"    File deleted from codebase. Purging from docs.")
                if filepath in self._summary_cache:
                    del self._summary_cache[filepath]
                    self._save_cache()
                self._remove_module_doc(filepath)
                continue

            analysis = parse_file(filepath)
            if analysis.parse_error:
                self.out(f"    Skipping: {analysis.parse_error}")
                continue

            # Stage 1: Function-level docs
            fn_docs = self._document_functions(analysis)

            # Stage 2: Module-level summary
            module_summary = self._document_module(analysis, fn_docs)

            # Cache the summary
            self._summary_cache[filepath] = module_summary
            self._save_cache()

            # Write module doc file
            self._write_module_doc(filepath, analysis, fn_docs, module_summary)

        # Stage 3: Architecture overview (if structure changed)
        if update_architecture:
            self._update_architecture_doc()

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
                self.out(f"    [Docs] Could not document {fn.qualified_name}: {e}")
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
        self.out("\n[Docs] Updating architecture overview...")

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
        self.out(f"  [Docs] Saved → {arch_path}")

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
        self.out(f"    Saved → {out_path}")

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------
    def _remove_module_doc(self, filepath: str) -> None:
        """Deletes the markdown file for a module that was removed."""
        module_name = Path(filepath).stem
        out_path = os.path.join(self.docs_dir, f"{module_name}.md")
        if os.path.exists(out_path):
            os.remove(out_path)
            self.out(f"    Removed obsolete doc → {out_path}")

    def _load_cache(self) -> Dict[str, str]:
        if os.path.exists(self._summary_cache_path):
            with open(self._summary_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        with open(self._summary_cache_path, "w", encoding="utf-8") as f:
            json.dump(self._summary_cache, f, indent=2)
