from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import time
from langchain_ollama import ChatOllama

from retrieval.hybrid_retriever import HybridRetriever
from core.model_manager import (
    ORCHESTRATOR_MODEL,
    unload_workers,
    unload_model
)
from core.worker import WorkerAgent, Finding, SPECIALIZATIONS

# ---------------------------------------------------------------------------
# Orchestrator prompts
# ---------------------------------------------------------------------------
_PLAN_PROMPT = """You are a senior engineering lead planning a code review.
Given the user's request, decide how deep the review should be on a scale 1-3:
  1 = quick spot check (1 round per worker, k=3 snippets)
  2 = standard review  (2 rounds per worker, k=4 snippets)
  3 = deep audit       (3 rounds per worker, k=6 snippets)

Respond with ONLY a single digit: 1, 2, or 3.
User request: {user_request}"""

_SYNTHESIS_PROMPT = """You are an expert Senior Software Architect producing a comprehensive code review report.

You have received findings from 10 specialised analysis agents. Synthesise them into a single, precise report.

### USER REQUEST
{user_request}

### AGGREGATED FINDINGS FROM ALL AGENTS
{formatted_findings}

### INSTRUCTIONS
- Deduplicate overlapping findings.
- Group by severity: HIGH → MEDIUM → LOW.
- Reference file names and line numbers where provided.
- Be direct and technical. Do not pad.
- Generate ONLY the content inside the XML tags below.

<REVIEW>
# Code Review Report

## Critical Issues (HIGH severity)
<!-- List all HIGH severity issues with file/line references -->

## Warnings (MEDIUM severity)
<!-- List all MEDIUM severity issues -->

## Minor Issues (LOW severity)
<!-- List all LOW severity issues -->

## Overall Assessment
<!-- 2-3 sentence summary of codebase health -->
</REVIEW>

<DOCS>
# Codebase Documentation

## Architecture Overview
<!-- What this codebase does, based on the code seen -->

## Key Components
<!-- Main modules/classes/functions identified -->

## Known Issues & Tech Debt
<!-- Summary for future maintainers -->
</DOCS>"""


class OrchestratorAgent:
    """
    Coordinates the full multi-agent pipeline:
      1. Plans review depth using the 14B model.
      2. Spins up 10 WorkerAgents in parallel thread pool.
      3. Collects all Findings.
      4. Unloads worker model from VRAM.
      5. Synthesises a comprehensive review with the 14B model.
      6. Saves review.md and documentation.md.
    """

    def __init__(self, retriever: HybridRetriever, max_workers: int = 1):
        self.retriever = retriever
        self.max_workers = max_workers
        self.llm = ChatOllama(
            model=ORCHESTRATOR_MODEL,
            temperature=0.1,
            keep_alive="10m",
        )

    def run(self, user_request: str):
        print("\n[Orchestrator] Planning review depth...")
        depth = self._plan_depth(user_request)
        rounds, k = self._depth_to_params(depth)
        print(f"[Orchestrator] Depth={depth} → {rounds} round(s), k={k} per search.")
        unload_model(ORCHESTRATOR_MODEL)
        try:
            import gc
            from torch.cuda import empty_cache
            gc.collect()
            empty_cache()
        except Exception:
            pass
        time.sleep(5)
        # ------------------------------------------------------------------
        # Phase 1: Parallel worker execution
        # ------------------------------------------------------------------
        print(f"\n[Orchestrator] Dispatching {len(SPECIALIZATIONS)} workers...")
        all_findings: List[Finding] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(
                    self._run_worker, spec, self.retriever, user_request, k, rounds
                ): spec
                for spec in SPECIALIZATIONS
            }
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    short = " ".join(spec.split()[:2])
                    print(f"  [Worker:{short}] Failed with error: {e}")

        print(
            f"\n[Orchestrator] All workers done. "
            f"Total findings: {len(all_findings)}"
        )

        # ------------------------------------------------------------------
        # Phase 2: Unload worker model BEFORE loading 14B
        # ------------------------------------------------------------------
        unload_workers()

        # ------------------------------------------------------------------
        # Phase 3: 14B synthesis
        # ------------------------------------------------------------------
        print("[Orchestrator] Synthesising final report with 14B model...")
        formatted = self._format_findings(all_findings)
        review_md, docs_md = self._synthesise(user_request, formatted)

        # ------------------------------------------------------------------
        # Phase 4: Save output files
        # ------------------------------------------------------------------
        self._save("review.md", review_md)
        self._save("documentation.md", docs_md)

        print("\n[Orchestrator] Done! Files saved: review.md, documentation.md")
        return review_md, docs_md

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _run_worker(
        specialization: str,
        retriever: HybridRetriever,
        user_request: str,
        k: int,
        rounds: int,
    ) -> List[Finding]:
        """Thread target — creates and runs a single WorkerAgent."""
        worker = WorkerAgent(
            specialization=specialization,
            retriever=retriever,
            chunks_per_search=k,
            max_rounds=rounds,
        )
        return worker.run(user_request)

    def _plan_depth(self, user_request: str) -> int:
        try:
            resp = self.llm.invoke(
                [("human", _PLAN_PROMPT.format(user_request=user_request))]
            ).content.strip()
            digit = next((c for c in resp if c in "123"), "2")
            return int(digit)
        except Exception:
            return 2  # default to standard

    @staticmethod
    def _depth_to_params(depth: int):
        return {1: (1, 3), 2: (2, 4), 3: (3, 6)}.get(depth, (2, 4))

    @staticmethod
    def _format_findings(findings: List[Finding]) -> str:
        """Convert Finding objects into a readable block for the synthesis prompt."""
        if not findings:
            return "No issues detected by worker agents."

        # Sort: HIGH first, then MEDIUM, then LOW
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_f = sorted(findings, key=lambda f: order.get(f.severity.upper(), 1))

        lines = []
        for i, f in enumerate(sorted_f, 1):
            lines.append(
                f"[{i}] [{f.severity}] {f.source_file} (line {f.line_number})\n"
                f"    Spec: {f.specialization.split('(')[0].strip()}\n"
                f"    Issue: {f.description}\n"
                f"    Fix: {f.suggestion}"
            )
            if f.snippet_preview:
                lines.append(f"    Code: {f.snippet_preview[:100]}...")
        return "\n\n".join(lines)

    def _synthesise(self, user_request: str, formatted_findings: str):
        """Run the 14B model on all aggregated findings and return (review, docs)."""
        prompt = _SYNTHESIS_PROMPT.format(
            user_request=user_request,
            formatted_findings=formatted_findings,
        )
        try:
            raw = self.llm.invoke(
                [("human", prompt)]
            ).content.strip()
        except Exception as e:
            print(f"[Orchestrator] Synthesis error: {e}")
            return f"# Error\n{e}", ""

        review = self._extract_tag(raw, "REVIEW")
        docs = self._extract_tag(raw, "DOCS")
        return review or "# No review generated.", docs or ""

    @staticmethod
    def _extract_tag(text: str, tag: str) -> str:
        import re
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _save(filename: str, content: str):
        if content:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Saved → {filename}")
        else:
            print(f"  Skipped {filename} (empty)")
