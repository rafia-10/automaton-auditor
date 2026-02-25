"""src/tools/repo_tools.py — Sandboxed repo analysis tools emitting Evidence."""
from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Dict

from src.state import Evidence  # Pydantic Evidence model

# ---------------------------------------------------------------------------
# Typed result models
# ---------------------------------------------------------------------------

@dataclass
class CommitRecord:
    hash: str
    author: str
    email: str
    date: str
    subject: str


@dataclass
class ASTGraph:
    """Module-level import graph extracted from a repo's Python source."""
    nodes: List[str] = field(default_factory=list)
    edges: Dict[str, List[str]] = field(default_factory=dict)  # file → imports
    defined_symbols: Dict[str, List[str]] = field(default_factory=dict)  # file → [class/func names]
    parse_errors: List[str] = field(default_factory=list)

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "total_files": len(self.nodes),
            "files_with_imports": len(self.edges),
            "parse_errors": len(self.parse_errors),
            "total_symbols": sum(len(v) for v in self.defined_symbols.values()),
        }


# ---------------------------------------------------------------------------
# Clone (sandboxed via tempfile)
# ---------------------------------------------------------------------------

def clone_repo(url: str, *, depth: int = 1, timeout: int = 120) -> Path:
    """Shallow-clone *url* into a temp directory. Caller owns cleanup."""
    tmp = Path(tempfile.mkdtemp(prefix="auditor_"))
    r = subprocess.run(
        ["git", "clone", "--depth", str(depth), "--single-branch", "--no-tags", url, str(tmp)],
        capture_output=True, text=True, timeout=timeout, shell=False,
    )
    if r.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"git clone failed:\n{r.stderr.strip()}")
    return tmp


def cleanup_repo(path: Path) -> None:
    shutil.rmtree(str(path), ignore_errors=True)


# ---------------------------------------------------------------------------
# Git log
# ---------------------------------------------------------------------------

def get_git_log(repo_dir: Path, max_commits: int = 50) -> List[CommitRecord]:
    r = subprocess.run(
        ["git", "-C", str(repo_dir), "log",
         f"--max-count={max_commits}", "--format=%H|%an|%ae|%ai|%s"],
        capture_output=True, text=True, timeout=30, shell=False,
    )
    commits = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("|", maxsplit=4)
        if len(parts) == 5:
            commits.append(CommitRecord(*parts))
    return commits


# ---------------------------------------------------------------------------
# AST graph (imports + defined symbols)
# ---------------------------------------------------------------------------

def _extract_imports(tree: ast.AST) -> List[str]:
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return sorted(imports)


def _extract_symbols(tree: ast.AST) -> List[str]:
    """Top-level class and function names."""
    return [
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def build_ast_graph(repo_dir: Path) -> ASTGraph:
    graph = ASTGraph()
    for py_file in sorted(repo_dir.rglob("*.py")):
        rel = str(py_file.relative_to(repo_dir))
        graph.nodes.append(rel)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            graph.parse_errors.append(f"{rel}: {e}")
            continue
        imports = _extract_imports(tree)
        if imports:
            graph.edges[rel] = imports
        symbols = _extract_symbols(tree)
        if symbols:
            graph.defined_symbols[rel] = symbols
    return graph


# ---------------------------------------------------------------------------
# Detective Evidence wrapper
# ---------------------------------------------------------------------------

def make_evidence_from_commits(commits: List[CommitRecord], repo_url: str) -> Evidence:
    content = "\n".join(f"{c.hash} {c.subject}" for c in commits)
    return Evidence(
        dimension_id="forensic_accuracy_code",
        source=repo_url,
        kind="repo.git_log",
        content=content,
        metadata={"total_commits": len(commits)},
    )


def make_evidence_from_ast(ast_graph: ASTGraph, repo_url: str) -> Evidence:
    metadata = {
        "total_files": ast_graph.stats["total_files"],
        "total_symbols": ast_graph.stats["total_symbols"],
        "files_with_imports": ast_graph.stats["files_with_imports"],
        "parse_errors": ast_graph.stats["parse_errors"],
    }
    content = f"Nodes: {ast_graph.nodes}\nEdges: {ast_graph.edges}\nSymbols: {ast_graph.defined_symbols}"
    return Evidence(
        dimension_id="forensic_accuracy_code",
        source=repo_url,
        kind="repo.ast_graph",
        content=content,
        metadata=metadata,
    )


__all__ = [
    "CommitRecord", "ASTGraph",
    "clone_repo", "cleanup_repo", "get_git_log", "build_ast_graph",
    "make_evidence_from_commits", "make_evidence_from_ast",
]