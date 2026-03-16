"""
ingest/symbol_index.py

A lightweight SQLite-backed symbol index.

Stores every function and class extracted by the AST parser and supports:
  - Exact name lookup
  - Prefix/fuzzy search
  - Fetching the full source of a symbol by name
  - Finding all symbols defined in a file

This lets the hybrid retriever quickly go from "symbol name" → "source code"
without re-reading files from disk on every query.
"""
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, List, Optional

from ingest.ast_parser import FileAnalysis, FunctionSymbol, ClassSymbol


from core.paths import get_symbol_db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS functions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    qualified   TEXT NOT NULL,
    file        TEXT NOT NULL,
    line_start  INTEGER,
    line_end    INTEGER,
    signature   TEXT,
    docstring   TEXT,
    calls       TEXT,          -- JSON list of called names
    decorators  TEXT,          -- JSON list
    source      TEXT,
    is_method   INTEGER,       -- 0/1
    class_name  TEXT
);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    file        TEXT NOT NULL,
    line_start  INTEGER,
    line_end    INTEGER,
    docstring   TEXT,
    bases       TEXT,          -- JSON list
    methods     TEXT,          -- JSON list
    source      TEXT
);

CREATE INDEX IF NOT EXISTS idx_fn_name ON functions(name);
CREATE INDEX IF NOT EXISTS idx_fn_file ON functions(file);
CREATE INDEX IF NOT EXISTS idx_cls_name ON classes(name);
CREATE INDEX IF NOT EXISTS idx_cls_file ON classes(file);
"""


@dataclass
class SymbolRow:
    kind: str               # "function" or "class"
    name: str
    qualified: str
    file: str
    line_start: int
    line_end: int
    signature: str
    docstring: str
    source: str


class SymbolIndex:
    """
    SQLite-backed symbol store. Instantiate once; pass it to the retriever.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_symbol_db()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Building / clearing
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Drop all rows — used before a full re-index."""
        self._conn.execute("DELETE FROM functions")
        self._conn.execute("DELETE FROM classes")
        self._conn.commit()
        print("[SymbolIndex] Cleared.")

    def ingest(self, analyses: List[FileAnalysis]) -> None:
        """
        Insert all symbols from a list of FileAnalysis objects.
        Uses INSERT OR REPLACE so repeated ingestion is safe.
        """
        import json
        fn_rows = []
        cls_rows = []

        for analysis in analyses:
            if analysis.parse_error:
                continue
            for fn in analysis.functions:
                fn_rows.append((
                    fn.name, fn.qualified_name, fn.file,
                    fn.line_start, fn.line_end,
                    fn.signature, fn.docstring,
                    json.dumps(fn.calls),
                    json.dumps(fn.decorators),
                    fn.source,
                    int(fn.is_method),
                    fn.class_name or "",
                ))
            for cls in analysis.classes:
                cls_rows.append((
                    cls.name, cls.file,
                    cls.line_start, cls.line_end,
                    cls.docstring,
                    json.dumps(cls.bases),
                    json.dumps(cls.methods),
                    cls.source,
                ))

        self._conn.executemany(
            "INSERT INTO functions "
            "(name, qualified, file, line_start, line_end, signature, docstring, "
            " calls, decorators, source, is_method, class_name) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            fn_rows,
        )
        self._conn.executemany(
            "INSERT INTO classes "
            "(name, file, line_start, line_end, docstring, bases, methods, source) "
            "VALUES (?,?,?,?,?,?,?,?)",
            cls_rows,
        )
        self._conn.commit()
        print(f"[SymbolIndex] Indexed {len(fn_rows)} functions, "
              f"{len(cls_rows)} classes.")

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def lookup(self, name: str) -> List[SymbolRow]:
        """Exact name match. Returns all definitions (could be in multiple files)."""
        rows = []
        rows += self._fn_query("WHERE name = ? OR qualified = ?", (name, name))
        rows += self._cls_query("WHERE name = ?", (name,))
        return rows

    def search(self, partial: str, limit: int = 10) -> List[SymbolRow]:
        """Prefix search — returns functions and classes whose name starts with `partial`."""
        pat = partial + "%"
        rows = []
        rows += self._fn_query("WHERE name LIKE ? LIMIT ?", (pat, limit))
        rows += self._cls_query("WHERE name LIKE ? LIMIT ?", (pat, limit))
        return rows[:limit]

    def get_file_symbols(self, filepath: str) -> List[SymbolRow]:
        """All symbols defined in a specific file."""
        rows = []
        rows += self._fn_query("WHERE file = ?", (filepath,))
        rows += self._cls_query("WHERE file = ?", (filepath,))
        return rows

    def get_source(self, name: str) -> Optional[str]:
        """Return the source of the first match for `name`."""
        results = self.lookup(name)
        return results[0].source if results else None

    def all_function_names(self) -> List[str]:
        cur = self._conn.execute("SELECT DISTINCT name FROM functions")
        return [r[0] for r in cur.fetchall()]

    def all_file_paths(self) -> List[str]:
        cur = self._conn.execute(
            "SELECT DISTINCT file FROM functions UNION "
            "SELECT DISTINCT file FROM classes"
        )
        return [r[0] for r in cur.fetchall()]

    def stats(self) -> dict:
        fn_count = self._conn.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        cls_count = self._conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
        file_count = len(self.all_file_paths())
        return {"functions": fn_count, "classes": cls_count, "files": file_count}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fn_query(self, where: str, params: tuple) -> List[SymbolRow]:
        sql = (
            "SELECT name, qualified, file, line_start, line_end, "
            "signature, docstring, source FROM functions " + where
        )
        cur = self._conn.execute(sql, params)
        return [
            SymbolRow(
                kind="function",
                name=r["name"], qualified=r["qualified"],
                file=r["file"], line_start=r["line_start"], line_end=r["line_end"],
                signature=r["signature"] or "", docstring=r["docstring"] or "",
                source=r["source"] or "",
            )
            for r in cur.fetchall()
        ]

    def _cls_query(self, where: str, params: tuple) -> List[SymbolRow]:
        sql = (
            "SELECT name, name as qualified, file, line_start, line_end, "
            "'class' as signature, docstring, source FROM classes " + where
        )
        cur = self._conn.execute(sql, params)
        return [
            SymbolRow(
                kind="class",
                name=r["name"], qualified=r["qualified"],
                file=r["file"], line_start=r["line_start"], line_end=r["line_end"],
                signature=r["signature"] or "", docstring=r["docstring"] or "",
                source=r["source"] or "",
            )
            for r in cur.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
