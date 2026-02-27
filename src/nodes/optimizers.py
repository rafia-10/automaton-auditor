from __future__ import annotations
from langsmith import traceable
from ..state import AgentState, JudicialOpinion, Evidence
from typing import List

@traceable(name="MinMaxOptimizer")
def min_max_optimizer(state: AgentState) -> dict:
    """Identifies deep architectural flaws by cross-referencing evidence and opinions."""
    flaws = []
    # state["evidences"] is Dict[str, List[Evidence]]
    evidences = state.get("evidences", {})
    opinions: List[JudicialOpinion] = state.get("opinions", [])
    
    # 1. Cross-dimensional weakness check
    # Fail is score < 3
    failing_dims = list(set([o.criterion_id for o in opinions if o.score < 3]))
    if len(failing_dims) > 3:
        flaws.append(f"Systemic failure in core architecture: Multiple dimensions ({', '.join(failing_dims)}) showing critical flaws.")
    
    # 2. Evidence vs Opinion Discrepancy
    for dim_id, ev_list in evidences.items():
        if not ev_list: continue
        ev = ev_list[0]
        rel_opinions = [o for o in opinions if o.criterion_id == dim_id]
        # If evidence says not found but judges give high score
        if not ev.found and rel_opinions and any(o.score > 3 for o in rel_opinions):
            flaws.append(f"Potential False Positive in {dim_id}: High judge scores despite evidence reporting artifact not found.")
    
    # 3. Structural Overload
    total_loc = 0
    for ev_list in evidences.values():
        for ev in ev_list:
            if ev.content and "LOC:" in ev.content:
                try:
                    loc = int(ev.content.split("LOC:")[1].split()[0])
                    total_loc += loc
                except:
                    pass
    
    if total_loc > 5000:
        flaws.append(f"Architectural Complexity Warning: Large codebase detected ({total_loc} LOC), check for modularity risks.")

    return {"architectural_flaws": flaws}

min_max_optimizer.name = "min_max_optimizer"
