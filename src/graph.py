from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from .nodes.detectives import doc_analyst, repo_investigator
from .state import DetectiveState, FinalVerdict, GraphState

log = logging.getLogger(__name__)


def evidence_aggregator(state: DetectiveState) -> dict:
    """Fan-in node. Summarises collected evidence; placeholder for judge wiring."""
    evidence = state.get("evidence", {})
    errors   = state.get("errors", [])

    dim_lines = "\n".join(f"  [{dim}] {ev.kind} — {ev.source[:60]}" for dim, ev in sorted(evidence.items()))
    score = len(evidence) / max(len(evidence) + len(errors), 1)

    verdict = FinalVerdict(
        overall_score=round(score, 2),
        passed=score >= 0.5,
        summary=f"Collected evidence for {len(evidence)} dimension(s). Errors: {len(errors)}.\n{dim_lines}",
        dimension_scores={dim: 1.0 for dim in evidence},
    )
    return {"verdict": verdict}


def _build_graph() -> StateGraph:
    g = StateGraph(GraphState)

    # Stage 1 — detectives (parallel fan-out)
    g.add_node("repo_investigator", repo_investigator)
    g.add_node("doc_analyst",       doc_analyst)
    g.add_edge(START,               "repo_investigator")
    g.add_edge(START,               "doc_analyst")

    # Stage 2 — fan-in aggregator (judges slot in here in Week 3)
    g.add_node("evidence_aggregator", evidence_aggregator)
    g.add_edge("repo_investigator",   "evidence_aggregator")
    g.add_edge("doc_analyst",         "evidence_aggregator")

    # Stage 3 — terminal
    g.add_edge("evidence_aggregator", END)

    return g


audit_graph = _build_graph().compile()

__all__ = ["audit_graph", "evidence_aggregator"]
