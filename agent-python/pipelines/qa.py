"""
pipelines/qa.py

Natural Language Q&A pipeline.

Workflow
--------
1. User asks a question in plain English.
2. HybridRetriever fetches relevant symbols + dep-expanded context.
3. The 14B orchestrator generates a precise answer with file:line citations.

This pipeline does NOT run all 10 worker agents — it's designed for fast,
interactive answers, not a full audit.
"""

from langchain_ollama import ChatOllama
from retrieval.hybrid_retriever import HybridRetriever, CodeContext
from core.model_manager import ORCHESTRATOR_MODEL
from typing import List

_QA_SYSTEM_PROMPT = """You are a senior software engineer who has read every line of this codebase.
Answer the user's question using ONLY the provided code context.
Always cite the source file and line numbers when referencing code.
If the answer is not in the provided context, say so — do not guess.
Format: clear prose, with inline citations like `auth.py:42`."""


class QAPipeline:
    """
    Fast Q&A over the indexed codebase.
    Designed for interactive use — single question, single answer.
    """

    def __init__(self, retriever: HybridRetriever, output_callback=None):
        self.retriever = retriever
        self.out = output_callback or print
        self.llm = ChatOllama(
            model=ORCHESTRATOR_MODEL,
            temperature=0.1,
            keep_alive="10m",
        )

    def ask(self, question: str, verbose: bool = True) -> str:
        if verbose:
            self.out(f"\n[Q&A] Retrieving context for: '{question}'")

        contexts = self.retriever.retrieve(
            query=question,
            vector_k=10,
            dep_hops=1,
            max_total=20,
        )

        if not contexts:
            return "No relevant code found in the indexed codebase."

        if verbose:
            self.out(f"[Q&A] Using {len(contexts)} symbol(s) as context.")

        formatted_ctx = self.retriever.format_context(contexts, max_chars=20_000)

        messages = [
            ("system", _QA_SYSTEM_PROMPT),
            ("human", f"### QUESTION\n{question}\n\n### CODE CONTEXT\n{formatted_ctx}"),
        ]

        answer = self.llm.invoke(messages).content.strip()
        return answer

    def interactive_loop(self):
        self.out("\n[Q&A Mode] Ask anything about the codebase. Type 'back' to return.\n")
        while True:
            try:
                question = input("Question: ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not question:
                continue
            if question.lower() in ("back", "exit", "quit"):
                break
            answer = self.ask(question)
            self.out(f"\n{answer}\n")
