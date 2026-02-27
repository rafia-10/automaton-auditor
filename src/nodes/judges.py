from __future__ import annotations
from langsmith import traceable
from ..state import Evidence, JudicialOpinion, AgentState

@traceable(name="Prosecutor")
def prosecutor_node(state: AgentState) -> dict:
    """Argues for strict compliance and highlights failures."""
    opinions = []
    debate = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Dialectical logic: identify strictly negative aspects
        negative_points = [line for line in ev.content.split("\n") if "error" in line.lower() or "fail" in line.lower()]
        score = 0.4 if negative_points else 0.7
        
        debate.append(f"[Prosecutor] Dimension {dim_id}: Found {len(negative_points)} strict violations. Maintenance cost is too high.")
        
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="fail" if score < 0.5 else "partial",
            score=score,
            rationale=f"Prosecutor found {len(negative_points)} issues in {ev.kind}.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions, "debate_log": debate}

@traceable(name="Defense")
def defense_node(state: AgentState) -> dict:
    """Advocates for the implementation, emphasizing constraints and context."""
    opinions = []
    debate = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Dialectical logic: highlight innovation/effort
        merit_points = [line for line in ev.content.split("\n") if "validated" in line.lower() or "completed" in line.lower()]
        
        debate.append(f"[Defense] Dimension {dim_id}: Despite criticisms, the code shows {len(merit_points)} successful validations. It's a pragmatic trade-off.")
        
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="pass",
            score=0.9 if merit_points else 0.6,
            rationale=f"Defense highlights {len(merit_points)} points of successful execution.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions, "debate_log": debate}

@traceable(name="TechLead")
def tech_lead_node(state: AgentState) -> dict:
    """Evaluates technical feasibility and long-term maintainability."""
    opinions = []
    debate = []
    for dim_id, ev in state.get("evidence", {}).items():
        # Dialectical logic: deterministic rules for conflict resolution
        is_complex = len(ev.content) > 200
        
        debate.append(f"[TechLead] Dimension {dim_id}: Architectural feasibility is {'high' if not is_complex else 'low due to complexity'}. We must prioritize stability.")
        
        opinions.append(JudicialOpinion(
            dimension_id=dim_id,
            verdict="partial" if is_complex else "pass",
            score=0.5 if is_complex else 0.85,
            rationale=f"TechLead evaluates complexity as {'high' if is_complex else 'manageable'}.",
            evidence_keys=[dim_id]
        ))
    return {"opinions": opinions, "debate_log": debate}
