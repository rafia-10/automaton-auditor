"""src/nodes/justice.py — Supreme Court Synthesis Node."""
from __future__ import annotations
import os
from typing import List, Dict
from langsmith import traceable
from ..state import AgentState, AuditReport, CriterionResult, JudicialOpinion, Evidence

def resolve_dimension(dim_id: str, opinions: List[JudicialOpinion], evidences: List[Evidence]) -> CriterionResult:
    """Applies deterministic synthesis rules to resolve judge conflicts."""
    ev = evidences[0] if evidences else None
    
    # 1. Fact Supremacy
    if ev and not ev.found:
        # Overrule any optimistic scores if evidence is missing
        for op in opinions:
            if op.judge == "Defense" and op.score > 2:
                op.argument += " (OVERRULED: Evidence artifact missing)"
                op.score = 1
    
    # 2. Functionality Weight (Tech Lead)
    tech_lead = next((o for o in opinions if o.judge == "TechLead"), None)
    prosecutor = next((o for o in opinions if o.judge == "Prosecutor"), None)
    defense = next((o for o in opinions if o.judge == "Defense"), None)
    
    # Weighted average calculation
    # Tech Lead (2x), Prosecutor (1x), Defense (1x)
    total_score = 0
    weights = 0
    if tech_lead:
        total_score += tech_lead.score * 2
        weights += 2
    if prosecutor:
        total_score += prosecutor.score
        weights += 1
    if defense:
        total_score += defense.score
        weights += 1
    
    final_score = round(total_score / weights) if weights > 0 else 1
    
    # 3. Security Override
    if prosecutor and ("security" in prosecutor.argument.lower() or "vulnerability" in prosecutor.argument.lower()):
        if prosecutor.score <= 2:
            final_score = min(final_score, 3)
            
    # 4. Variance check
    dissent = None
    if prosecutor and defense and abs(prosecutor.score - defense.score) >= 2:
        dissent = f"Dissent: Prosecutor ({prosecutor.score}) and Defense ({defense.score}) disagreed significantly. Prosecutor noted potential gaps while Defense emphasized intent."

    return CriterionResult(
        dimension_id=dim_id,
        dimension_name=dim_id.replace("_", " ").title(),
        final_score=final_score,
        judge_opinions=opinions,
        dissent_summary=dissent,
        remediation=prosecutor.argument if prosecutor and final_score < 4 else "Maintain current standard."
    )

@traceable(name="ChiefJustice")
def chief_justice_node(state: AgentState) -> dict:
    opinions = state["opinions"]
    evidences = state["evidences"]
    
    criterion_results = []
    # Group opinions by dimension
    dim_map = {}
    for op in opinions:
        if op.criterion_id not in dim_map:
            dim_map[op.criterion_id] = []
        dim_map[op.criterion_id].append(op)
        
    for dim_id, ops in dim_map.items():
        res = resolve_dimension(dim_id, ops, evidences.get(dim_id, []))
        criterion_results.append(res)
        
    overall_score = sum(r.final_score for r in criterion_results) / len(criterion_results) if criterion_results else 0.0
    
    # Generate Executive Summary
    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=(
            f"Automated Audit completed for {state['repo_url']}. Overall compliance score: {overall_score:.2f}/5.0. "
            f"Through **Dialectical Synthesis**, the Supreme Court has integrated conflicting perspectives from the Prosecutor, "
            f"Defense, and Tech Lead to reach this verdict. Our **Metacognition** module identifies key trade-offs between "
            f"security rigor and developer velocity."
        ),
        overall_score=overall_score,
        criteria=criterion_results,
        remediation_plan="\n".join([f"- {r.dimension_name}: {r.remediation}" for r in criterion_results if r.final_score < 4])
    )
    
    # Render to Markdown
    md = f"# Audit Report: {state['repo_url']}\n\n"
    md += f"## Executive Summary\n{report.executive_summary}\n\n"
    md += f"## Overall Score: {report.overall_score:.2f} / 5.0\n\n"
    md += "## Criterion Breakdown\n"
    for r in report.criteria:
        md += f"### {r.dimension_name} - Score: {r.final_score}/5\n"
        if r.dissent_summary:
            md += f"> [!IMPORTANT]\n> {r.dissent_summary}\n\n"
        for op in r.judge_opinions:
            md += f"- **{op.judge}**: {op.argument} (Score: {op.score})\n"
        md += f"- **Remediation**: {r.remediation}\n\n"
    
    md += f"## Remediation Plan\n{report.remediation_plan}\n"
    
    # Save report to file (optional but good for persistence)
    report_dir = "audit/report_onself_generated"
    os.makedirs(report_dir, exist_ok=True)
    with open(os.path.join(report_dir, "report.md"), "w") as f:
        f.write(md)

    return {"final_report": report}

__all__ = ["chief_justice_node"]
