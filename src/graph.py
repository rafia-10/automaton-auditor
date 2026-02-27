"""src/graph.py — Hardened StateGraph with conditional routing."""
from __future__ import annotations

import operator
from typing import Dict, List, Literal

import os
from dotenv import load_dotenv

# Load environment variables from .env before anything else
load_dotenv()

# Bridge LANGSMITH_API_KEY to LANGCHAIN_API_KEY if needed (compatibility)
if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

# Check for tracing config and warn if missing
if os.getenv("LANGCHAIN_TRACING_V2") == "true":
    if not os.getenv("LANGCHAIN_API_KEY"):
        print("⚠️  WARNING: LANGCHAIN_TRACING_V2 is enabled but LANGCHAIN_API_KEY is missing/empty.")
        print("   Traces will not be sent to LangSmith. Check your .env file.")
from langgraph.graph import END, START, StateGraph

from langsmith import traceable
from .nodes.detectives import doc_analyst, repo_investigator, vision_inspector
from .nodes.judges import prosecutor_node, defense_node, tech_lead_node
from .nodes.optimizers import min_max_optimizer
from .nodes.justice import chief_justice_node
from .state import AgentState, Evidence, AuditReport, JudicialOpinion


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
            goal="Validate Input Configuration",
            found=True,
            content=f"Configuration validated for repo: {repo}",
            location="system.config",
            rationale="Pre-flight check passed.",
            confidence=1.0
        )
        evidence[ev.goal] = [ev] # Note: detectives return lists of evidences by goal/dim_id

    return {"errors": errors, "evidences": evidence}

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


@traceable(name="EvidenceAggregator")
def evidence_aggregator_node(state: AgentState) -> dict:
    """Synchronization node for detectives."""
    return {} # Just a fan-in point

# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("check_config", check_config)
workflow.add_node("RepoInvestigator", repo_investigator)
workflow.add_node("DocAnalyst", doc_analyst)
workflow.add_node("VisionInspector", vision_inspector)
workflow.add_node("EvidenceAggregator", evidence_aggregator_node)
workflow.add_node("Prosecutor", prosecutor_node)
workflow.add_node("Defense", defense_node)
workflow.add_node("TechLead", tech_lead_node)
workflow.add_node("MinMaxOptimizer", min_max_optimizer)
workflow.add_node("ChiefJustice", chief_justice_node)

# Define Edges / Routing
workflow.add_edge(START, "check_config")

# Conditional fan-out to detectives
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

# Fan-in detectives to EvidenceAggregator
workflow.add_edge("RepoInvestigator", "EvidenceAggregator")
workflow.add_edge("DocAnalyst", "EvidenceAggregator")
workflow.add_edge("VisionInspector", "EvidenceAggregator")

# Fan-out from aggregator to Judges
workflow.add_edge("EvidenceAggregator", "Prosecutor")
workflow.add_edge("EvidenceAggregator", "Defense")
workflow.add_edge("EvidenceAggregator", "TechLead")

# Fan-in judges to MinMaxOptimizer
workflow.add_edge("Prosecutor", "MinMaxOptimizer")
workflow.add_edge("Defense", "MinMaxOptimizer")
workflow.add_edge("TechLead", "MinMaxOptimizer")

# Finalize
workflow.add_edge("MinMaxOptimizer", "ChiefJustice")
workflow.add_edge("ChiefJustice", END)

# Compile
audit_graph = workflow.compile()

__all__ = ["audit_graph"]
