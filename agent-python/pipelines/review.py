"""
pipelines/review.py

Full Codebase Review Pipeline.

This is not a retrieval problem — it is a scheduled scan.
Two complementary phases feed into a single LLM synthesis:

Phase 1 — Static analysis (zero-LLM, instant)
    Run AST-based checks on every file. These are deterministic and fast:
    bare-except, mutable defaults, eval/exec, hardcoded secrets, SQL f-strings, etc.
    Results available immediately, before any model is loaded.

Phase 2 — Semantic analysis (10 workers, parallel)
    10 specialist WorkerAgents each run hybrid retrieval for their specialization.
    They use the small 0.5b model to filter and structure findings.
    Workers are unloaded from VRAM before Phase 3.

Phase 3 — Synthesis (14B model)
    The orchestrator 14B model receives both static + semantic findings,
    deduplicates, ranks by severity, and produces review.md.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from ingest.ast_parser import StaticFinding, parse_directory
from ingest.symbol_index import SymbolIndex
from retrieval.hybrid_retriever import HybridRetriever
from core.model_manager import load_orchestrator_model, unload_workers
from core.worker import WorkerAgent, Finding, SPECIALIZATIONS
from core.inference import generate_with_turboquant,precompute_system_prefix


# ---------------------------------------------------------------------------
# Synthesis prompt
# ---------------------------------------------------------------------------

_SYNTHESIS_PROMPT = """You are an expert Senior Software Architect producing a comprehensive code review.

You have two sets of findings:

A) STATIC ANALYSIS FINDINGS — produced by AST analysis, 100% deterministic.
B) SEMANTIC FINDINGS — produced by 10 specialised LLM agents reviewing code context.

Synthesise both into a single, authoritative report. Deduplicate overlapping findings.
Group by severity: CRITICAL → HIGH → MEDIUM → LOW.
Reference file and line numbers precisely. Be direct and technical.

CRITICAL INSTRUCTION: You MUST wrap your code review inside <REVIEW> tags and your architecture overview inside <DOCS> tags. Do not omit these tags.

<REVIEW>
# Code Review Report

## Critical Issues
<!-- CRITICAL / HIGH severity items here, file:line references -->

## Warnings
<!-- MEDIUM severity items -->

## Minor Issues & Code Smell
<!-- LOW severity items -->

## Circular Import Cycles
<!-- List any detected import cycles -->

## Overall Assessment
<!-- 3-4 sentence codebase health summary -->
</REVIEW>

<DOCS>
# Architecture Overview
<!-- Inferred from the code reviewed -->

## Key Modules
<!-- One bullet per significant module, what it does -->

## Known Tech Debt
<!-- Items future maintainers must be aware of -->
</DOCS>
"""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class ReviewPipeline:
    """
    Orchestrates the full two-phase code review.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        symbol_index: SymbolIndex,
        source_dir: str,
        max_workers: int = 10,
        output_dir: str | None = None
    ):
        self.output_dir = output_dir or source_dir
        self.retriever = retriever
        self.symbol_index = symbol_index
        self.source_dir = source_dir
        self.max_workers = max_workers
        self.model = None
        self.tokenizer = None
        self.review_base_cache, _ = None, None # precompute_system_prefix(_SYNTHESIS_PROMPT, self.model, self.tokenizer)

    def run(self, user_request: str = "Full codebase audit") -> Tuple[str, str]:
        print(f"\n{'─'*55}")
        print(f" Code Review Pipeline — scope: {user_request}")
        print(f"{'─'*55}")

        # ------------------------------------------------------------------
        # Phase 1: Static analysis (fast, no LLM)
        # ------------------------------------------------------------------
        print("\n[Phase 1/3] Running static analysis...")
        analyses = parse_directory(self.source_dir)
        static_findings: List[StaticFinding] = []
        for analysis in analyses:
            static_findings.extend(analysis.static_findings)
        print(f"  Static analysis: {len(static_findings)} finding(s) across "
              f"{len(analyses)} files.")

        # ------------------------------------------------------------------
        # Phase 2: 10 parallel semantic workers
        # ------------------------------------------------------------------
        print(f"\n[Phase 2/3] Launching {len(SPECIALIZATIONS)} semantic workers...")
        semantic_findings: List[Finding] = []
        safe_workers = 1
        total_workers = len(SPECIALIZATIONS)
        db_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=safe_workers) as pool:
            futures = {
                pool.submit(
                    self._run_worker, spec, user_request, db_lock
                ): spec
                for spec in SPECIALIZATIONS
            }
            completed = 0
            try:
                for future in as_completed(futures):
                    spec = futures[future]
                    completed += 1
                    try:
                        findings = future.result()
                        semantic_findings.extend(findings)
                        # Print successful completion progress
                        short_spec = spec.split('(')[0].strip()
                        print(f"  [Progress] {completed}/{total_workers} workers done. (Finished: {short_spec})")
                    except Exception as e:
                        short_spec = spec.split('(')[0].strip()
                        print(f"  [Progress] {completed}/{total_workers} workers done. (Error in {short_spec}: {e})")
            except KeyboardInterrupt:
                print("\n[!] Force quitting: Review interrupted by user. Cancelling pending workers...")
                pool.shutdown(wait=False, cancel_futures=True)
                raise

        print(f"  Semantic analysis: {len(semantic_findings)} finding(s).")

        # Unload 0.5b model before loading 14B for synthesis
        unload_workers()

        # ------------------------------------------------------------------
        # Phase 3: 14B synthesis
        # ------------------------------------------------------------------
        print("\n[Phase 3/3] Synthesising report with 14B model...")
        self.model, self.tokenizer = load_orchestrator_model()
        self.review_base_cache, _ = precompute_system_prefix(_SYNTHESIS_PROMPT, self.model, self.tokenizer)
        review_md, docs_md = self._synthesise(
            user_request, static_findings, semantic_findings
        )

        self._save("review.md", review_md)
        # self._save("documentation.md", docs_md)

        print(f"\n{'─'*55}")
        print(" Review complete → review.md")
        print(f"{'─'*55}\n")
        return review_md, docs_md

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_worker(self, specialization: str, user_request: str,lock: threading.Lock = None) -> List[Finding]:
        worker = WorkerAgent(
            specialization=specialization,
            retriever=self.retriever,
            chunks_per_search=6,
            max_rounds=3,
            db_lock=lock
        )
        return worker.run(user_request)

    def _synthesise(
        self,
        user_request: str,
        static_findings: List[StaticFinding],
        semantic_findings: List[Finding],
    ) -> Tuple[str, str]:
        static_block = self._format_static(static_findings)
        semantic_block = self._format_semantic(semantic_findings)

        req_cache = self.review_base_cache.clone()

        prompt = """### STATIC ANALYSIS FINDINGS
{static_findings}

### SEMANTIC FINDINGS (from 10 specialist agents)
{semantic_findings}

### USER REQUEST / SCOPE
{user_request}""".format(
            static_findings=static_block,
            semantic_findings=semantic_block,
            user_request=user_request,
        )
        try:
            raw = generate_with_turboquant(prompt, base_cache=req_cache, model=self.model, tokenizer=self.tokenizer)
        except Exception as e:
            print(f"[Review] Synthesis error: {e}")
            return f"# Error\n{e}", ""

        review = self._extract_tag(raw, "REVIEW") or "# No review generated."
        docs   = self._extract_tag(raw, "DOCS")   or ""
        return review, docs

    @staticmethod
    def _format_static(findings: List[StaticFinding]) -> str:
        if not findings:
            return "None detected."
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_f = sorted(findings, key=lambda f: order.get(f.severity, 1))
        lines = []
        for i, f in enumerate(sorted_f, 1):
            lines.append(
                f"[{i}] [{f.severity}] {os.path.basename(f.file)}:{f.line} "
                f"[{f.rule}] {f.message} → {f.suggestion}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_semantic(findings: List[Finding]) -> str:
        if not findings:
            return "None detected."
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_f = sorted(findings, key=lambda f: order.get(f.severity.upper(), 1))
        lines = []
        for i, f in enumerate(sorted_f, 1):
            lines.append(
                f"[{i}] [{f.severity}] {f.source_file} (line {f.line_number})\n"
                f"    {f.description} → {f.suggestion}"
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_tag(text: str, tag: str) -> str:
        import re
        # Sometimes LLMs wrap the entire output in markdown code blocks like ```xml
        clean_text = re.sub(r"^```[a-zA-Z]*\n", "", text.strip())
        clean_text = re.sub(r"\n```$", "", clean_text)

        m = re.search(rf"<{tag}>(.*?)</{tag}>", clean_text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        
        # FALLBACK: If the LLM forgot the tags, rescue the raw text
        if tag == "REVIEW":
            # If <DOCS> exists, take everything before it. Otherwise, take the whole text.
            if "<DOCS>" in clean_text:
                return clean_text.split("<DOCS>")[0].strip()
            elif "DOCS" in clean_text: # Handle missing brackets
                return clean_text.split("DOCS")[0].strip()
            return clean_text.strip()
            
        elif tag == "DOCS":
            if "</REVIEW>" in clean_text:
                return clean_text.split("</REVIEW>")[-1].strip()
            elif "<DOCS>" in clean_text:
                return clean_text.split("<DOCS>")[-1].replace("</DOCS>", "").strip()
                
        return ""

    # @staticmethod
    def _save(self, filename: str, content: str):
        if content:
            path = os.path.join(self.output_dir, filename)
            os.makedirs(self.output_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Saved → {path}")
