from __future__ import annotations
from langsmith import traceable
from ..state import Evidence, JudicialOpinion, AgentState

@traceable(name="Prosecutor")
def prosecutor_node(state: AgentState) -> dict:
    """Argues for strict compliance and highlights failures."""
    opinions = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Harsh judge
        score = 0.3 if "error" in ev.content.lower() else 0.7
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="fail" if score < 0.5 else "partial",
            score=score,
            rationale=f"[Prosecutor] Evidence for {dim_id} is questionable. Too many unknowns.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions}

@traceable(name="Defense")
def defense_node(state: AgentState) -> dict:
    """Advocates for the implementation, emphasizing constraints and context."""
    opinions = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Lenient judge
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="pass",
            score=0.9,
            rationale=f"[Defense] Evidence for {dim_id} shows significant effort and progress.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions}

@traceable(name="TechLead")
def tech_lead_node(state: AgentState) -> dict:
    """Evaluates technical feasibility and long-term maintainability."""
    opinions = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Pragmatic judge
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="partial" if len(ev.content) < 100 else "pass",
            score=0.8,
            rationale=f"[TechLead] Technical depth for {dim_id} is acceptable.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions}
