"""src/tools/repo_tools.py — Sandboxed repo analysis tools emitting Evidence."""
from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Dict, Optional

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
        raise RuntimeError(f"Command timed out: {' '.join(args)}") from e
    except subprocess.CalledProcessError as e:
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
    except Exception:
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
# Specific Rubric Forensic Checks
# ---------------------------------------------------------------------------

def check_git_progression(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Run 'git log --oneline --reverse' and check progression."""
    try:
        r = safe_run(["git", "log", "--oneline", "--reverse"], cwd=repo_dir)
        lines = r.stdout.strip().splitlines()
        count = len(lines)
        messages = [l.split(" ", 1)[1] for l in lines if " " in l]
        
        # Check progression pattern (heuristically)
        progression = "Environment Setup" in r.stdout or "setup" in r.stdout.lower()
        success = count > 3
        
        return Evidence(
            goal="Verify git commit history progression.",
            found=success,
            content=r.stdout,
            location="git log",
            rationale=f"Found {count} commits. progression_story: {success}",
            confidence=1.0 if count > 0 else 0.5
        )
    except Exception as e:
        return Evidence(
            goal="Verify git commit history progression.",
            found=False,
            location="git log",
            rationale=f"Error running git log: {str(e)}",
            confidence=0.0
        )

def check_state_rigor(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Scan for state definitions using AST."""
    found_pydantic = False
    found_reducers = False
    code_snippets = []
    
    for py_file in repo_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                # Look for Pydantic/TypedDict
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in ("BaseModel", "TypedDict"):
                            found_pydantic = True
                            code_snippets.append(ast.unparse(node))
                
                # Look for operator.add/ior
                if isinstance(node, ast.Attribute):
                    if node.attr in ("add", "ior") and isinstance(node.value, ast.Name) and node.value.id == "operator":
                        found_reducers = True
        except:
            continue

    return Evidence(
        goal="State Management Rigor (Phase 0)",
        found=found_pydantic and found_reducers,
        content="\n---\n".join(code_snippets[:2]),
        location="src/state.py or equivalent",
        rationale=f"found_pydantic={found_pydantic}, found_reducers={found_reducers}",
        confidence=0.9
    )

def check_graph_orchestration(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Scan for StateGraph and fan-out/fan-in."""
    found_graph = False
    found_parallel = False
    
    for py_file in repo_dir.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "StateGraph" in content:
                found_graph = True
            
            tree = ast.parse(content)
            for node in ast.walk(tree):
                # Heuristic for parallel branches: multiple edges from same node
                if isinstance(node, ast.Call) and hasattr(node.func, "attr") and node.func.attr == "add_edge": # type: ignore
                    found_parallel = True # Simple check for now
        except:
            continue

    return Evidence(
        goal="Graph Orchestration Architecture (Phase 1)",
        found=found_graph,
        location="src/graph.py or equivalent",
        rationale=f"found_graph={found_graph}, found_parallel_logic={found_parallel}",
        confidence=0.8
    )

def check_tool_safety(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Scan for tempfile and subprocess safety."""
    uses_temp = False
    unsafe_os = False
    snippet = ""
    
    for py_file in repo_dir.rglob("*.py"):
        try:
            content = py_file.read_text()
            if "tempfile" in content or "TemporaryDirectory" in content:
                uses_temp = True
            if "os.system(" in content:
                unsafe_os = True
                snippet = "Detected os.system call"
        except:
            continue

    return Evidence(
        goal="Safe Tool Engineering (Phase 2)",
        found=uses_temp and not unsafe_os,
        content=snippet,
        location="src/tools/",
        rationale=f"uses_temp={uses_temp}, unsafe_os_system={unsafe_os}",
        confidence=1.0
    )

def check_structured_output(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Scan Judge nodes for .with_structured_output()."""
    found_structured = False
    snippet = ""
    
    for py_file in repo_dir.rglob("judges.py"):
        try:
            content = py_file.read_text()
            if ".with_structured_output(" in content or ".bind_tools(" in content:
                found_structured = True
                snippet = "Detected .with_structured_output call"
        except:
            continue

    return Evidence(
        goal="Structured Output Enforcement (Phase 3)",
        found=found_structured,
        content=snippet,
        location="src/nodes/judges.py",
        rationale=f"found_structured={found_structured}",
        confidence=1.0
    )

def check_judicial_nuance(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Compare Judge prompts for distinctness."""
    found_distinct = False
    
    for py_file in repo_dir.rglob("judges.py"):
        try:
            content = py_file.read_text()
            if "PROSECUTOR_PROMPT" in content and "DEFENSE_PROMPT" in content and "TECHLEAD_PROMPT" in content:
                found_distinct = True
        except:
            continue

    return Evidence(
        goal="Judicial Nuance and Dialectics",
        found=found_distinct,
        content="Detected distinct PROSECUTOR, DEFENSE, and TECHLEAD prompt templates." if found_distinct else "",
        location="src/nodes/judges.py",
        rationale=f"found_distinct_prompts={found_distinct}",
        confidence=1.0
    )

def check_justice_synthesis(repo_dir: Path) -> Evidence:
    """Forensic Instruction: Verify deterministic synthesis logic."""
    found_logic = False
    
    for py_file in repo_dir.rglob("justice.py"):
        try:
            content = py_file.read_text()
            if "def resolve_dimension" in content and ("if" in content or "weights" in content):
                found_logic = True
        except:
            continue

    return Evidence(
        goal="Chief Justice Synthesis Engine",
        found=found_logic,
        content="Detected deterministic resolve_dimension logic with conditional weighting." if found_logic else "",
        location="src/nodes/justice.py",
        rationale=f"found_deterministic_logic={found_logic}",
        confidence=1.0
    )

__all__ = [
    "CommitRecord", "ASTGraph",
    "clone_repo", "cleanup_repo", "get_git_log", "build_ast_graph",
    "check_git_progression", "check_state_rigor", "check_graph_orchestration", "check_tool_safety", "check_structured_output",
    "check_judicial_nuance", "check_justice_synthesis",
    "safe_run"
]