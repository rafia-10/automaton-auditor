"""src/nodes/detectives.py — Forensic Detective Nodes."""
from __future__ import annotations
import os
from pathlib import Path
from langsmith import traceable

from ..state import Evidence, AgentState
from ..tools.doc_tools import ingest_pdf, extract_file_paths, verify_theoretical_depth
from ..tools.repo_tools import (
    clone_repo,
    cleanup_repo,
    check_git_progression,
    check_state_rigor,
    check_graph_orchestration,
    check_tool_safety,
    check_structured_output,
    check_judicial_nuance,
    check_justice_synthesis,
)

@traceable(name="repo_investigator")
def repo_investigator(state: AgentState) -> dict:
    url = state["repo_url"]
    evidences: dict[str, list[Evidence]] = {}
    errors: list[str] = []
    repo_dir = None

    try:
        repo_dir = clone_repo(url)
        
        # 1. Git Forensic Analysis
        ev_git = check_git_progression(repo_dir)
        evidences["git_forensic_analysis"] = [ev_git]
        
        # 2. State Management Rigor
        ev_state = check_state_rigor(repo_dir)
        evidences["state_management_rigor"] = [ev_state]
        
        # 3. Graph Orchestration
        ev_graph = check_graph_orchestration(repo_dir)
        evidences["graph_orchestration"] = [ev_graph]
        
        # 4. Safe Tool Engineering
        ev_safe = check_tool_safety(repo_dir)
        evidences["safe_tool_engineering"] = [ev_safe]
        
        # 5. Structured Output Enforcement
        ev_struct = check_structured_output(repo_dir)
        evidences["structured_output_enforcement"] = [ev_struct]
        
        # 6. Judicial Nuance
        ev_nuance = check_judicial_nuance(repo_dir)
        evidences["judicial_nuance"] = [ev_nuance]
        
        # 7. Chief Justice Synthesis
        ev_syn = check_justice_synthesis(repo_dir)
        evidences["chief_justice_synthesis"] = [ev_syn]

    except Exception as exc:
        errors.append(f"[repo_investigator] {type(exc).__name__}: {exc}")
    finally:
        if repo_dir:
            cleanup_repo(repo_dir)

    return {"evidences": evidences, "errors": errors}

@traceable(name="doc_analyst")
def doc_analyst(state: AgentState) -> dict:
    pdf_path = state.get("pdf_path")
    evidences: dict[str, list[Evidence]] = {}
    errors: list[str] = []

    if not pdf_path or not os.path.exists(pdf_path):
        return {"errors": ["PDF report missing or path invalid"]}

    try:
        chunks = ingest_pdf(pdf_path)
        
        # 1. Theoretical Depth
        depth_results = verify_theoretical_depth(chunks)
        content = "\n".join([f"{k}: {'Found' if v['found'] else 'Missing'}" for k, v in depth_results.items()])
        snippets = [s for k in depth_results for s in depth_results[k]['snippets']]
        
        ev_depth = Evidence(
            goal="Theoretical Depth (Documentation)",
            found=any(v['found'] for v in depth_results.values()),
            content=content + "\n\nSnippets:\n" + "\n---\n".join(snippets),
            location=pdf_path,
            rationale=f"Scanned for rubric keywords. Found {sum(1 for v in depth_results.values() if v['found'])}/4 keywords.",
            confidence=0.9
        )
        evidences["theoretical_depth"] = [ev_depth]
        
        # 2. Report Accuracy (Cross-Reference)
        # Note: This technically needs RepoInvestigator findings. 
        # But we can extract paths here and let the Judge/Chief Justice cross-ref.
        all_text = "\n".join(chunks)
        claimed_paths = extract_file_paths(all_text)
        
        ev_acc = Evidence(
            goal="Report Accuracy (Cross-Reference)",
            found=len(claimed_paths) > 0,
            content=f"Claimed file paths: {', '.join(claimed_paths)}",
            location=pdf_path,
            rationale=f"Extracted {len(claimed_paths)} potential file paths from report.",
            confidence=0.8
        )
        evidences["report_accuracy"] = [ev_acc]

    except Exception as exc:
        errors.append(f"[doc_analyst] {pdf_path}: {type(exc).__name__}: {exc}")

    return {"evidences": evidences, "errors": errors}

import re

@traceable(name="vision_inspector")
def vision_inspector(state: AgentState) -> dict:
    """Sophisticated VisionInspector: Scans for diagrams (Mermaid) and visual assets (png/jpg/svg)."""
    url = state["repo_url"]
    evidences: dict[str, list[Evidence]] = {}
    repo_dir = None
    visual_assets = []
    mermaid_diagrams = []

    try:
        repo_dir = clone_repo(url)
        
        # 1. Scan for Visual Media
        extensions = (".png", ".jpg", ".jpeg", ".svg", ".pdf", ".gif")
        for file_path in repo_dir.rglob("*"):
            if file_path.suffix.lower() in extensions:
                visual_assets.append(str(file_path.relative_to(repo_dir)))
        
        # 2. Scan for Mermaid Diagrams in Markdown
        mermaid_pattern = re.compile(r"```mermaid\s+(.*?)```", re.DOTALL)
        for md_file in repo_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                matches = mermaid_pattern.findall(content)
                if matches:
                    mermaid_diagrams.append({
                        "file": str(md_file.relative_to(repo_dir)),
                        "count": len(matches)
                    })
            except:
                continue

        # Construct Evidence
        ev_vision = Evidence(
            goal="Visual & Architectural Artifact Analysis",
            found=len(visual_assets) > 0 or len(mermaid_diagrams) > 0,
            content=(
                f"Detected {len(visual_assets)} image assets.\n"
                f"Detected {len(mermaid_diagrams)} files containing Mermaid diagrams.\n\n"
                f"Image Samples: {', '.join(visual_assets[:5])}...\n"
                f"Diagram Locations: {', '.join([d['file'] for d in mermaid_diagrams])}"
            ),
            location="Repository Assets",
            rationale=(
                f"VisionInspector successfully identified architectural diagrams and media assets. "
                f"Mermaid coverage: {len(mermaid_diagrams)} files."
            ),
            confidence=1.0
        )
        evidences["swarm_visual"] = [ev_vision]

    except Exception as exc:
        # Fallback to symbolic verification if clone fails
        ev_vision = Evidence(
            goal="Visual & Architectural Artifact Analysis",
            found=False,
            content=f"Forensic vision scan failed: {exc}",
            location="N/A",
            rationale="Simulated fallback for vision analysis.",
            confidence=0.1
        )
        evidences["swarm_visual"] = [ev_vision]
    finally:
        if repo_dir:
            cleanup_repo(repo_dir)

    return {"evidences": evidences}

__all__ = ["repo_investigator", "doc_analyst", "vision_inspector"]
