"""src/graph.py — Hardened StateGraph with conditional routing."""
from __future__ import annotations

import operator
from typing import Dict, List, Literal

from dotenv import load_dotenv

# Load environment variables from .env before anything else
load_dotenv()
from langgraph.graph import END, START, StateGraph

from langsmith import traceable
from .nodes.detectives import doc_analyst, repo_investigator, vision_inspector
from .nodes.judges import prosecutor_node, defense_node, tech_lead_node
from .state import AgentState, Evidence, FinalVerdict, JudicialOpinion


# ---------------------------------------------------------------------------
# Pre-flight / Config validation node
# ---------------------------------------------------------------------------

@traceable(name="check_config")
def check_config(state: AgentState) -> dict:
    """Validates inputs before starting analysis."""
    errors = []
    evidence = {}
    
    repo = state.get("repo_url", "")
    if not repo.startswith("http"):
        errors.append(f"Invalid repo_url: {repo}")
    
    # Ensure reports directory exists if pdf_paths are provided
    for path in state.get("pdf_paths", []):
        if not path.endswith(".pdf"):
            errors.append(f"Invalid PDF path (must end in .pdf): {path}")

    if not errors:
        ev = Evidence(
            dimension_id="forensic_preflight",
            source="system",
            kind="repo.config_check",
            content=f"Configuration validated for repo: {repo}",
            metadata={"pdf_count": len(state.get("pdf_paths", []))}
        )
        evidence[ev.dimension_id] = ev

    return {"errors": errors, "evidence": evidence}

check_config.name = "check_config"


# ---------------------------------------------------------------------------
# Conditional Routing logic
# ---------------------------------------------------------------------------

def route_detectives(state: AgentState) -> List[str]:
    """Determines which detectives to run based on available input."""
    if state.get("errors"):
        return [END]
    
    detectives = ["RepoInvestigator"]
    if state.get("pdf_paths"):
        detectives.extend(["DocAnalyst", "VisionInspector"])
    return detectives


# ---------------------------------------------------------------------------
# Aggregator (Chief Judge)
# ---------------------------------------------------------------------------

@traceable(name="ChiefJustice")
def chief_justice_node(state: AgentState) -> dict:
    """Synthesizes FinalVerdict from multi-role JudicialOpinions."""
    opinions = state.get("opinions", [])
    ev_count = len(state["evidence"])
    
    avg_score = sum(o.score for o in opinions) / len(opinions) if opinions else 0.0
    
    summary = f"Audit summarized by Chief Justice. Collected {ev_count} pieces of evidence and {len(opinions)} judicial opinions."
    
    dissent = [f"{o.dimension_id}: {o.rationale}" for o in opinions if o.verdict == "fail"]
            
    verdict = FinalVerdict(
        overall_score=avg_score,
        passed=avg_score >= 0.7,
        summary=summary,
        dissent_summary="\n".join(dissent) if dissent else "No major dissent.",
        remediation_plan=["Review AST complexity", "Verify PDF methodology"] if avg_score < 0.9 else [],
        dimension_scores={o.dimension_id: o.score for o in opinions}
    )
    
    return {"verdict": verdict}

chief_justice_node.name = "chief_justice_node"


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("check_config", check_config)
workflow.add_node("RepoInvestigator", repo_investigator)
workflow.add_node("DocAnalyst", doc_analyst)
workflow.add_node("VisionInspector", vision_inspector)
workflow.add_node("Prosecutor", prosecutor_node)
workflow.add_node("Defense", defense_node)
workflow.add_node("TechLead", tech_lead_node)
workflow.add_node("ChiefJustice", chief_justice_node)

# Define Edges / Routing
workflow.add_edge(START, "check_config")

# Conditional fan-out from check_config
workflow.add_conditional_edges(
    "check_config",
    route_detectives,
    {
        "RepoInvestigator": "RepoInvestigator",
        "DocAnalyst": "DocAnalyst",
        "VisionInspector": "VisionInspector",
        END: END
    }
)

# Fan-out from detectives to multiple judges
for detective in ["RepoInvestigator", "DocAnalyst", "VisionInspector"]:
    workflow.add_edge(detective, "Prosecutor")
    workflow.add_edge(detective, "Defense")
    workflow.add_edge(detective, "TechLead")

# Fan-in judges to ChiefJustice
workflow.add_edge("Prosecutor", "ChiefJustice")
workflow.add_edge("Defense", "ChiefJustice")
workflow.add_edge("TechLead", "ChiefJustice")

workflow.add_edge("ChiefJustice", END)

# Compile
audit_graph = workflow.compile()

__all__ = ["audit_graph"]
