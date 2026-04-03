"""
core/worker.py  (updated)

WorkerAgent now uses the HybridRetriever rather than the raw MemoryManager.
This gives it dep-graph-expanded context instead of pure similarity hits.
"""
import threading
from dataclasses import dataclass
from typing import List, Optional
from rich import print
from langchain_ollama import ChatOllama

from core.model_manager import WORKER_MODEL

SPECIALIZATIONS = [
    "security vulnerabilities (SQL injection, XSS, hardcoded secrets, broken auth, path traversal)",
    "logic errors and bugs (off-by-one, null/None dereference, incorrect boolean conditions)",
    "performance bottlenecks (N+1 queries, O(n²) loops, unnecessary I/O, blocking calls in async)",
    "error and exception handling (missing try/except, swallowed exceptions, bare except clauses)",
    "code maintainability (duplicated code, god functions, poor naming, magic numbers)",
    "API and interface design (inconsistent return types, missing validation, unclear signatures)",
    "data validation and sanitisation (unvalidated user input, improper serialisation)",
    "concurrency and thread safety (race conditions, shared mutable state, missing locks)",
    "dependency and import hygiene (circular imports, unused imports, deprecated APIs)",
    "documentation and type annotation coverage (missing docstrings, absent type hints)",
]


@dataclass
class Finding:
    specialization: str
    source_file: str
    line_number: str
    severity: str
    description: str
    suggestion: str
    snippet_preview: str


_SEARCH_QUERY_PROMPT = """Convert this specialization into 3 short search queries (one per line).
Specialization: {specialization}
Context: {user_request}
Output only the 3 queries, nothing else."""

_ANALYSIS_PROMPT = """You are a code reviewer specialised ONLY in: {specialization}

Analyse the code below. Report issues related to your specialization only.
For each issue use this exact format:

ISSUE_START
FILE: <filename>
LINE: <line number or "?">
SEVERITY: <HIGH|MEDIUM|LOW>
DESCRIPTION: <one sentence>
SUGGESTION: <one sentence fix>
ISSUE_END

If no issues: output NO_ISSUES

Code:
{snippets}"""


class WorkerAgent:
    def __init__(self, specialization, retriever, chunks_per_search=6, max_rounds=3,db_lock=None):
        self.specialization = specialization
        self.retriever = retriever
        self.chunks_per_search = chunks_per_search
        self.max_rounds = max_rounds
        self.llm = ChatOllama(model=WORKER_MODEL, temperature=0.05, keep_alive="5m", num_ctx=32768)
        self.db_lock = db_lock or threading.Lock()

    def run(self, user_request: str) -> List[Finding]:
        all_findings: List[Finding] = []
        seen: set = set()
        queries = self._generate_queries(user_request)

        for round_idx in range(self.max_rounds):
            new_contexts = []
            for query in queries:
                # ---> LOCK ACQUIRED HERE: Safely query ChromaDB + SQLite <---
                with self.db_lock:
                    contexts = self.retriever.retrieve(
                        query=query, vector_k=self.chunks_per_search, dep_hops=1,
                        max_total=self.chunks_per_search,
                    )
                #LOCK RELEASED HERE <--- after retrieval is done, allowing other workers to proceed
                for ctx in contexts:
                    key = (ctx.file, ctx.name)
                    if key not in seen:
                        seen.add(key)
                        new_contexts.append(ctx)

            if not new_contexts:
                break
            
            MAX_CHARS_PER_BATCH = 12000

            current_batch_snippets = []
            current_batch_contexts = []
            current_chars = 0
            round_findings = []
            for ctx in new_contexts:
                formatted = ctx.format_for_prompt()
                length = len(formatted)
                
                # If adding this context exceeds the limit AND the batch isn't empty, process it
                if current_chars + length > MAX_CHARS_PER_BATCH and current_batch_snippets:
                    snippets_text = "\n\n---\n\n".join(current_batch_snippets)
                    batch_findings = self._analyse(snippets_text, current_batch_contexts)
                    round_findings.extend(batch_findings)
                    
                    # Reset the batch
                    current_batch_snippets = []
                    current_batch_contexts = []
                    current_chars = 0
                
                # Add the current context to the newly cleared (or still growing) batch
                current_batch_snippets.append(formatted)
                current_batch_contexts.append(ctx)
                current_chars += length
                
            # Process any remaining contexts in the final batch
            if current_batch_snippets:
                snippets_text = "\n\n---\n\n".join(current_batch_snippets)
                batch_findings = self._analyse(snippets_text, current_batch_contexts)
                round_findings.extend(batch_findings)

            all_findings.extend(round_findings)

            if not round_findings or round_idx == self.max_rounds - 1:
                break
            queries = self._refine_queries(queries, round_findings)

        print(f"  [Worker:{self._short()}] {len(all_findings)} finding(s).")
        return all_findings

    def _short(self):
        return " ".join(self.specialization.split()[:2])

    def _generate_queries(self, user_request):
        from rich import print as rprint
        prompt = _SEARCH_QUERY_PROMPT.format(
            specialization=self.specialization, user_request=user_request)
        try:
            # rprint(f"  [dim]↳ Worker '{self._short()}' querying 0.5b model...[/dim]")
            response = self.llm.invoke([("human", prompt)]).content.strip()
            queries = [q.strip() for q in response.split("\n") if q.strip()]
            return queries[:3] or [self.specialization.split("(")[0].strip()]
        except Exception:
            return [self.specialization.split("(")[0].strip()]

    def _refine_queries(self, queries, findings):
        keywords = set()
        for f in findings:
            keywords.update(f.description.split()[:4])
        extra = " ".join(list(keywords)[:6])
        return [f"{q} {extra}" for q in queries]

    def _analyse(self, snippets, contexts):
        from rich import print as rprint
        # rprint(f"  [dim]↳ Worker '{self._short()}' analyzing {len(contexts)} code chunks...[/dim]")
        prompt = _ANALYSIS_PROMPT.format(
            specialization=self.specialization, snippets=snippets)
        try:
            raw = self.llm.invoke([("human", prompt)]).content.strip()
        except Exception as e:
            print(f"  [Worker:{self._short()}] Error: {e}")
            return []
        if "NO_ISSUES" in raw and "ISSUE_START" not in raw:
            return []
        return self._parse(raw, contexts)

    def _parse(self, raw, contexts):
        findings = []
        for block in raw.split("ISSUE_START")[1:]:
            end = block.find("ISSUE_END")
            if end == -1:
                continue
            f = self._parse_block(block[:end].strip(), contexts)
            if f:
                findings.append(f)
        return findings

    def _parse_block(self, block, contexts) -> Optional[Finding]:
        lines = {
            k.strip(): v.strip()
            for line in block.splitlines()
            if ":" in line
            for k, v in [line.split(":", 1)]
        }
        desc = lines.get("DESCRIPTION", "")
        if not desc:
            return None
        preview = ""
        for ctx in contexts:
            if any(w in ctx.source.lower() for w in desc.lower().split()[:3]):
                preview = ctx.source[:100].replace("\n", " ")
                break
        return Finding(
            specialization=self.specialization,
            source_file=lines.get("FILE", "unknown"),
            line_number=lines.get("LINE", "?"),
            severity=lines.get("SEVERITY", "MEDIUM"),
            description=desc,
            suggestion=lines.get("SUGGESTION", ""),
            snippet_preview=preview,
        )
