from __future__ import annotations

import logging
from pathlib import Path

from ..state import Evidence, InputState
from ..tools.doc_tools import get_pdf_metadata, ingest_pdf, query_chunks
from ..tools.repo_tools import (
    build_ast_graph,
    cleanup_repo,
    clone_repo,
    get_git_log,
    make_evidence_from_ast,
    make_evidence_from_commits,
)

log = logging.getLogger(__name__)

# Rubric dimension IDs for documents — prefixed with 'doc_' to match Pydantic constraints
_DOC_QUERIES = {
    "doc_coverage":      "methodology and approach",
    "doc_results":       "results and findings",
    "doc_limitations":   "limitations and future work",
    "doc_methodology":   "architecture and design decisions",
    "doc_evaluation":    "evaluation metrics",
}


def repo_investigator(state: InputState) -> dict:
    url = state["repo_url"]
    evidence: dict[str, Evidence] = {}
    errors: list[str] = []
    repo_dir = None

    try:
        repo_dir = clone_repo(url)

        # Forensic analysis via repo_tools wrappers
        commits = get_git_log(repo_dir)
        ev_commits = make_evidence_from_commits(commits, url)
        evidence[ev_commits.dimension_id] = ev_commits

        graph = build_ast_graph(repo_dir)
        ev_ast = make_evidence_from_ast(graph, url)
        evidence[ev_ast.dimension_id] = ev_ast

        # Additional code quality forensic evidence
        dim_quality = "forensic_code_quality"
        evidence[dim_quality] = Evidence(
            dimension_id=dim_quality,
            source=url,
            kind="repo.ast_edges",
            content="\n".join(f"{f} → {', '.join(imp)}" for f, imp in list(graph.edges.items())[:10]),
            metadata={"files_with_imports": len(graph.edges)},
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
            meta = get_pdf_metadata(path)
            for dim_id, query in _DOC_QUERIES.items():
                top = query_chunks(chunks, query, top_k=3)
                if top:
                    evidence[dim_id] = Evidence(
                        dimension_id=dim_id,
                        source=path,
                        kind="doc.pdf_chunk",
                        content="\n\n---\n\n".join(top),
                        metadata={
                            "query": query, 
                            "pdf": Path(path).name,
                            **meta
                        },
                    )
        except Exception as exc:
            errors.append(f"[doc_analyst] {path}: {type(exc).__name__}: {exc}")
            log.exception("doc_analyst failed on %s", path)

    return {"evidence": evidence, "errors": errors}


__all__ = ["repo_investigator", "doc_analyst"]
