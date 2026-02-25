"""src/tools/repo_tools.py — Sandboxed repo analysis tools emitting Evidence."""
from __future__ import annotations

import ast
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Dict, Optional

from src.state import Evidence  # Pydantic Evidence model

log = logging.getLogger(__name__)

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
    
    # Hardening: Metrics
    loc: Dict[str, int] = field(default_factory=dict)
    complexity_score: Dict[str, int] = field(default_factory=dict)  # max nesting depth
    suspicious_patterns: Dict[str, List[str]] = field(default_factory=dict) # e.g. eval, os.system

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "total_files": len(self.nodes),
            "total_loc": sum(self.loc.values()),
            "files_with_imports": len(self.edges),
            "parse_errors": len(self.parse_errors),
            "total_symbols": sum(len(v) for v in self.defined_symbols.values()),
            "suspicious_count": sum(len(v) for v in self.suspicious_patterns.values()),
        }


# ---------------------------------------------------------------------------
# Defensive Subprocess Wrapper
# ---------------------------------------------------------------------------

def safe_run(args: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> subprocess.CompletedProcess:
    """Runs a command safely without shell, with timeout and explicit error handling."""
    try:
        r = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=True
        )
        return r
    except subprocess.TimeoutExpired as e:
        log.error("Command timed out after %ds: %s", timeout, " ".join(args))
        raise RuntimeError(f"Command timed out: {' '.join(args)}") from e
    except subprocess.CalledProcessError as e:
        log.error("Command failed (exit %d): %s\nStderr: %s", e.returncode, " ".join(args), e.stderr)
        raise RuntimeError(f"Command failed with exit {e.returncode}: {e.stderr.strip()}") from e


# ---------------------------------------------------------------------------
# Clone (sandboxed via tempfile)
# ---------------------------------------------------------------------------

def clone_repo(url: str, *, depth: int = 1, timeout: int = 120) -> Path:
    """Shallow-clone *url* into a temp directory. Caller owns cleanup."""
    tmp = Path(tempfile.mkdtemp(prefix="auditor_"))
    try:
        safe_run(
            ["git", "clone", "--depth", str(depth), "--single-branch", "--no-tags", url, str(tmp)],
            timeout=timeout
        )
        return tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def cleanup_repo(path: Path) -> None:
    shutil.rmtree(str(path), ignore_errors=True)


# ---------------------------------------------------------------------------
# Git log
# ---------------------------------------------------------------------------

def get_git_log(repo_dir: Path, max_commits: int = 50) -> List[CommitRecord]:
    try:
        r = safe_run(
            ["git", "log", f"--max-count={max_commits}", "--format=%H|%an|%ae|%ai|%s"],
            cwd=repo_dir
        )
        commits = []
        for line in r.stdout.strip().splitlines():
            parts = line.split("|", maxsplit=4)
            if len(parts) == 5:
                commits.append(CommitRecord(*parts))
        return commits
    except Exception as e:
        log.warning("Failed to get git log: %s", e)
        return []


# ---------------------------------------------------------------------------
# AST graph (imports + defined symbols + metrics)
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

def _analyze_metrics(tree: ast.AST) -> tuple[int, list[str]]:
    """Returns (max_nesting_depth, suspicious_patterns)."""
    nesting = 0
    suspicious = []
    
    for node in ast.walk(tree):
        # Nested depth detection (simplified)
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            d = 0
            curr = node
            while hasattr(curr, "parent") and curr.parent: # type: ignore
                if isinstance(curr.parent, (ast.If, ast.For, ast.While, ast.With, ast.Try)): # type: ignore
                    d += 1
                curr = curr.parent # type: ignore
            nesting = max(nesting, d)
        
        # Suspicious call detection
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "compile"):
                suspicious.append(node.func.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "system" and getattr(node.func.value, "id", "") == "os":
                suspicious.append("os.system")
                
    return nesting, suspicious

def build_ast_graph(repo_dir: Path) -> ASTGraph:
    graph = ASTGraph()
    for py_file in sorted(repo_dir.rglob("*.py")):
        rel = str(py_file.relative_to(repo_dir))
        graph.nodes.append(rel)
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            graph.loc[rel] = len(content.splitlines())
            
            tree = ast.parse(content)
            # Add parent pointers for nesting analysis
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child.parent = node # type: ignore
            
            graph.edges[rel] = _extract_imports(tree)
            graph.defined_symbols[rel] = _extract_symbols(tree)
            
            nesting, suspicious = _analyze_metrics(tree)
            graph.complexity_score[rel] = nesting
            if suspicious:
                graph.suspicious_patterns[rel] = suspicious
                
        except Exception as e:
            graph.parse_errors.append(f"{rel}: {type(e).__name__}: {e}")
            
    return graph


# ---------------------------------------------------------------------------
# Detective Evidence wrapper
# ---------------------------------------------------------------------------

def make_evidence_from_commits(commits: List[CommitRecord], repo_url: str) -> Evidence:
    content = "\n".join(f"{c.hash[:8]} {c.subject}" for c in commits)
    return Evidence(
        dimension_id="forensic_commit_hygiene",
        source=repo_url,
        kind="repo.git_log",
        content=content if content else "No commits found.",
        metadata={"total_commits": len(commits)},
    )


def make_evidence_from_ast(ast_graph: ASTGraph, repo_url: str) -> Evidence:
    stats = ast_graph.stats
    content = (
        f"Forensic Repo Audit Summary for {repo_url}\n"
        f"------------------------------------------\n"
        f"Total Files: {stats['total_files']}\n"
        f"Total LOC: {stats['total_loc']}\n"
        f"Defined Symbols: {stats['total_symbols']}\n"
        f"Suspicious Patterns: {stats['suspicious_count']}\n"
        f"Parse Errors: {stats['parse_errors']}\n"
    )
    return Evidence(
        dimension_id="forensic_repo_structure",
        source=repo_url,
        kind="repo.ast_graph",
        content=content,
        metadata=stats,
    )


__all__ = [
    "CommitRecord", "ASTGraph",
    "clone_repo", "cleanup_repo", "get_git_log", "build_ast_graph",
    "make_evidence_from_commits", "make_evidence_from_ast",
    "safe_run"
]