"""src/graph.py — Hardened StateGraph with conditional routing."""
from __future__ import annotations

import logging
from typing import Dict, List, Literal

from langgraph.graph import END, START, StateGraph

from .nodes.detectives import doc_analyst, repo_investigator
from .state import AgentState, FinalVerdict

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-flight / Config validation node
# ---------------------------------------------------------------------------

def check_config(state: AgentState) -> dict:
    """Validates inputs before starting analysis."""
    errors = []
    repo = state.get("repo_url", "")
    if not repo.startswith("http"):
        errors.append(f"Invalid repo_url: {repo}")
    
    # Ensure reports directory exists if pdf_paths are provided
    for path in state.get("pdf_paths", []):
        if not path.endswith(".pdf"):
            errors.append(f"Invalid PDF path (must end in .pdf): {path}")

    return {"errors": errors}


# ---------------------------------------------------------------------------
# Conditional Routing logic
# ---------------------------------------------------------------------------

def route_detectives(state: AgentState) -> List[str]:
    """Determines which detectives to run based on available input."""
    if state.get("errors"):
        return [END] # Stop if pre-flight failed
    
    detectives = ["repo_investigator"]
    if state.get("pdf_paths"):
        detectives.append("doc_analyst")
    return detectives


# ---------------------------------------------------------------------------
# Aggregator (Chief Judge)
# ---------------------------------------------------------------------------

def evidence_aggregator(state: AgentState) -> dict:
    """Synthesizes FinalVerdict from collected Evidence."""
    ev_count = len(state["evidence"])
    err_count = len(state["errors"])
    
    summary = (
        f"Audit complete. Collected {ev_count} pieces of forensic evidence. "
        f"Encountered {err_count} non-fatal errors during investigation."
    )
    
    # Basic scoring placeholder
    score = 1.0 if err_count == 0 and ev_count > 0 else 0.5
    if ev_count == 0:
        score = 0.0

    verdict = FinalVerdict(
        overall_score=score,
        passed=score >= 0.7,
        summary=summary,
        dimension_scores={k: 1.0 for k in state["evidence"].keys()}
    )
    
    return {"verdict": verdict}


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("check_config", check_config)
workflow.add_node("repo_investigator", repo_investigator)
workflow.add_node("doc_analyst", doc_analyst)
workflow.add_node("evidence_aggregator", evidence_aggregator)

# Define Edges / Routing
workflow.add_edge(START, "check_config")

# Conditional fan-out from check_config
workflow.add_conditional_edges(
    "check_config",
    route_detectives,
    {
        "repo_investigator": "repo_investigator",
        "doc_analyst": "doc_analyst",
        END: END
    }
)

# Fan-in to aggregator
workflow.add_edge("repo_investigator", "evidence_aggregator")
workflow.add_edge("doc_analyst", "evidence_aggregator")

workflow.add_edge("evidence_aggregator", END)

# Compile
audit_graph = workflow.compile()

__all__ = ["audit_graph"]
