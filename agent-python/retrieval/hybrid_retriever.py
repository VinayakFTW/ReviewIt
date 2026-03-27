"""
retrieval/hybrid_retriever.py

The central retrieval engine used by all three pipelines.

Two-stage retrieval
-------------------
Stage 1 — Semantic search
    Query the ChromaDB vector store to find the top-k most semantically
    similar functions/classes. Because embeddings are at symbol granularity
    (see ingest/embedder.py), each hit is a complete, parseable unit.

Stage 2 — Dependency graph expansion
    For each matched file, walk the dependency graph to include files that
    this file imports, and files that import this file. This captures
    cross-module context that pure vector search would miss.

    Example: the user asks "how does authentication work?". Vector search
    finds auth.py. Dep expansion adds models.py (imported by auth.py) and
    middleware.py (which imports auth.py). The LLM now sees the full picture.

Output
------
A list of CodeContext objects, each containing the source of one symbol
plus its location metadata.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_chroma import Chroma
from rich import print
from ingest.dep_graph import DependencyGraph
from ingest.symbol_index import SymbolIndex, SymbolRow


@dataclass
class CodeContext:
    """One retrieved symbol's data, ready to be placed in an LLM prompt."""
    kind: str               # "function" or "class"
    name: str
    qualified_name: str
    file: str
    line_start: int
    line_end: int
    signature: str
    docstring: str
    source: str
    retrieval_score: float  # higher = more relevant (0-1 for vector, 2.0 for dep-expanded)
    retrieval_method: str   # "vector" | "dep-expanded" | "symbol-lookup"

    def format_for_prompt(self) -> str:
        file_base = os.path.basename(self.file)
        header = (
            f"--- {self.kind.upper()}: {self.qualified_name} "
            f"| {file_base} (line {self.line_start}–{self.line_end}) "
            f"| via {self.retrieval_method} ---"
        )
        return f"{header}\n{self.source}"


class HybridRetriever:
    """
    Combines vector search and dependency-graph expansion.
    Used by all three agent pipelines.
    """

    def __init__(
        self,
        vector_store: Chroma,
        dep_graph: DependencyGraph,
        symbol_index: SymbolIndex,
        vector_k: int = 8,
        dep_hops: int = 1,
        max_total: int = 20,
    ):
        self.vs = vector_store
        self.dg = dep_graph
        self.si = symbol_index
        self.vector_k = vector_k
        self.dep_hops = dep_hops
        self.max_total = max_total

    # ------------------------------------------------------------------
    # Primary retrieval entry point (used by Q&A + Review pipelines)
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        vector_k: Optional[int] = None,
        dep_hops: Optional[int] = None,
        max_total: Optional[int] = None,
    ) -> List[CodeContext]:
        """
        Run hybrid retrieval for a natural language query.

        Args:
            query:     Natural language question or code concept.
            vector_k:  Override default number of vector hits.
            dep_hops:  Override dependency expansion hops.
            max_total: Cap on total results returned.

        Returns:
            Deduplicated list of CodeContext, best matches first.
        """
        k     = vector_k  or self.vector_k
        hops  = dep_hops  or self.dep_hops
        total = max_total or self.max_total

        # Stage 1: vector search
        vector_hits = self._vector_search(query, k=k)
        seen_keys: set = {(c.file, c.name) for c in vector_hits}
        results = list(vector_hits)

        # Stage 2: dep graph expansion
        seed_files = list({c.file for c in vector_hits})
        expanded_files = self.dg.expand_context(seed_files, dep_hops=hops)
        dep_only_files = [f for f in expanded_files if f not in seed_files]

        for filepath in dep_only_files:
            symbol_rows = self.si.get_file_symbols(filepath)
            for row in symbol_rows:
                key = (row.file, row.name)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(self._row_to_context(row, method="dep-expanded", score=0.5))

        # Sort: vector hits (higher score) first, then dep-expanded
        results.sort(key=lambda c: c.retrieval_score, reverse=True)
        return results[:total]

    # ------------------------------------------------------------------
    # Direct symbol lookup (used by the Docs pipeline and worker agents)
    # ------------------------------------------------------------------

    def lookup_symbol(self, name: str) -> List[CodeContext]:
        """
        Exact symbol name lookup — returns all definitions of `name`
        with their source, ranked by specificity.
        """
        rows = self.si.lookup(name)
        return [self._row_to_context(r, method="symbol-lookup", score=1.0) for r in rows]

    def retrieve_for_file(self, filepath: str) -> List[CodeContext]:
        """
        Fetch all symbols defined in a specific file.
        Used by the docs pipeline for per-file documentation.
        """
        rows = self.si.get_file_symbols(filepath)
        return [self._row_to_context(r, method="symbol-lookup", score=1.0) for r in rows]

    # ------------------------------------------------------------------
    # Format for LLM prompt
    # ------------------------------------------------------------------

    @staticmethod
    def format_context(contexts: List[CodeContext], max_chars: int = 24_000) -> str:
        """
        Concatenate retrieved contexts into a single prompt block.
        Truncates cleanly at symbol boundaries to stay within token limits.
        """
        parts = []
        total = 0
        for ctx in contexts:
            snippet = ctx.format_for_prompt()
            if total + len(snippet) > max_chars:
                parts.append(
                    f"[{len(contexts) - len(parts)} more symbols omitted — "
                    f"context limit reached]"
                )
                break
            parts.append(snippet)
            total += len(snippet)
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _vector_search(self, query: str, k: int) -> List[CodeContext]:
        try:
            docs_scores = self.vs.similarity_search_with_score(query, k=k)
        except Exception as e:
            print(f"[Retriever] Vector search error: {e}")
            return []

        results = []
        for doc, raw_score in docs_scores:
            m = doc.metadata
            # Chroma returns L2 distance; convert to 0-1 similarity
            similarity = max(0.0, 1.0 - raw_score / 2.0)
            results.append(CodeContext(
                kind=m.get("kind", "function"),
                name=m.get("name", ""),
                qualified_name=m.get("qualified_name", m.get("name", "")),
                file=m.get("source", ""),
                line_start=int(m.get("line_start", 0)),
                line_end=int(m.get("line_end", 0)),
                signature=m.get("signature", ""),
                docstring="",  # not stored in Chroma to save space
                source=doc.page_content,
                retrieval_score=similarity,
                retrieval_method="vector",
            ))
        return results

    def _row_to_context(
        self, row: SymbolRow, method: str, score: float
    ) -> CodeContext:
        return CodeContext(
            kind=row.kind,
            name=row.name,
            qualified_name=row.qualified,
            file=row.file,
            line_start=row.line_start,
            line_end=row.line_end,
            signature=row.signature,
            docstring=row.docstring,
            source=row.source,
            retrieval_score=score,
            retrieval_method=method,
        )
