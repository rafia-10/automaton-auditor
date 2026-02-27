from __future__ import annotations
from langsmith import traceable
from ..state import AgentState

@traceable(name="MinMaxOptimizer")
def min_max_optimizer(state: AgentState) -> dict:
    """Identifies deep architectural flaws by cross-referencing evidence and opinions."""
    flaws = []
    evidence = state.get("evidence", {})
    opinions = state.get("opinions", [])
    
    # Logic: Look for "Blind Spots" where evidence exists but opinions are overly optimistic
    # or where multiple dimensions show structural weakness.
    
    # 1. Cross-dimensional weakness check
    failing_dims = [o.dimension_id for o in opinions if o.verdict == "fail"]
    if len(failing_dims) > 2:
        flaws.append(f"Systemic failure in core architecture: Multiple dimensions ({', '.join(failing_dims)}) showing critical flaws.")
    
    # 2. Evidence vs Opinion Discrepancy
    for dim_id, ev in evidence.items():
        rel_opinions = [o for o in opinions if o.dimension_id == dim_id]
        if rel_opinions and all(o.score > 0.8 for o in rel_opinions) and "missing" in ev.content.lower():
            flaws.append(f"Potential False Positive in {dim_id}: High judge scores despite evidence mentioning 'missing' components.")
    
    # 3. Structural Overload
    if any(len(ev.content) > 1000 for ev in evidence.values()):
        flaws.append("Architectural Complexity Warning: Data bloat detected in evidence nodes, suggesting lack of modularity.")

    return {"architectural_flaws": flaws}

min_max_optimizer.name = "min_max_optimizer"
