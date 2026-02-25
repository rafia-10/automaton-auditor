from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..state import Evidence, InputState
from ..tools.doc_tools import ingest_pdf, query_chunks
from ..tools.repo_tools import build_ast_graph, cleanup_repo, clone_repo, get_git_log

log = logging.getLogger(__name__)

# Rubric dimension IDs this node is responsible for
_REPO_DIMENSIONS = ["code_quality", "commit_hygiene", "repo_structure"]
_DOC_DIMENSIONS  = ["doc_coverage", "methodology", "results_clarity", "limitations", "evaluation"]

_DOC_QUERIES = {
    "doc_coverage":      "methodology and approach",
    "results_clarity":   "results and findings",
    "limitations":       "limitations and future work",
    "methodology":       "architecture and design decisions",
    "evaluation":        "evaluation metrics",
}


def _ev(dimension_id: str, source: str, kind: str, content: str, **meta) -> Evidence:
    return Evidence(
        dimension_id=dimension_id,
        source=source,
        kind=kind,
        content=content,
        metadata={"evidence_id": str(uuid.uuid4()), **meta},
    )


def repo_investigator(state: InputState) -> dict:
    url = state["repo_url"]
    evidence: dict[str, Evidence] = {}
    errors: list[str] = []
    repo_dir = None

    try:
        repo_dir = clone_repo(url)

        commits = get_git_log(repo_dir)
        evidence["commit_hygiene"] = _ev(
            "commit_hygiene", url, "repo.git_log",
            "\n".join(f"{c.date[:10]}  {c.author:<20}  {c.subject}" for c in commits[:10]),
            commit_count=len(commits),
            authors=list({c.author for c in commits}),
        )

        graph = build_ast_graph(repo_dir)
        evidence["repo_structure"] = _ev(
            "repo_structure", url, "repo.ast_graph",
            str(graph.stats),
            **graph.stats,
        )

        evidence["code_quality"] = _ev(
            "code_quality", url, "repo.ast_edges",
            "\n".join(f"{f} → {', '.join(imp)}" for f, imp in list(graph.edges.items())[:15]),
            files_analysed=len(graph.edges),
            total_symbols=graph.stats["total_symbols"],
        )

    except Exception as exc:
        errors.append(f"[repo_investigator] {type(exc).__name__}: {exc}")
        log.exception("repo_investigator failed")
    finally:
        if repo_dir:
            cleanup_repo(repo_dir)

    return {"evidence": evidence, "errors": errors, "repo_dir": str(repo_dir) if repo_dir else None}


def doc_analyst(state: InputState) -> dict:
    evidence: dict[str, Evidence] = {}
    errors: list[str] = []

    for path in state.get("pdf_paths", []):
        try:
            chunks = ingest_pdf(path)
            for dim_id, query in _DOC_QUERIES.items():
                top = query_chunks(chunks, query, top_k=3)
                if top:
                    evidence[dim_id] = _ev(
                        dim_id, path, "doc.pdf_chunk",
                        "\n\n---\n\n".join(top),
                        query=query,
                        pdf=Path(path).name,
                    )
        except Exception as exc:
            errors.append(f"[doc_analyst] {path}: {type(exc).__name__}: {exc}")
            log.exception("doc_analyst failed on %s", path)

    return {"evidence": evidence, "errors": errors}


__all__ = ["repo_investigator", "doc_analyst"]
