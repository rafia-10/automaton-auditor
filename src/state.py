"""state.py — Digital Courtroom graph state.

Pipeline: detectives → judges → verdict
"""
from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Domain models (self-contained, no external import)
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    """A single piece of auditor-collected evidence, tagged by rubric dimension."""
    dimension_id: str = Field(..., pattern=r"^(forensic|doc)_[a-z0-9_]+$")
    source: str = Field(..., min_length=1)
    kind: str = Field(..., pattern=r"^(repo|doc)\.[a-z0-9_]+$")
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class JudicialOpinion(BaseModel):
    """A structured ruling produced by a Judge node for one rubric dimension."""
    dimension_id: str = Field(..., pattern=r"^(forensic|doc)_[a-z0-9_]+$")
    verdict: str = Field(..., pattern=r"^(pass|fail|partial)$")
    score: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., min_length=10)
    evidence_keys: List[str] = Field(default_factory=list)
    ruled_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class FinalVerdict(BaseModel):
    """Aggregate verdict synthesised from all JudicialOpinions."""
    overall_score: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    summary: str = Field(..., min_length=20)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Sub-states — one per pipeline stage
# ---------------------------------------------------------------------------

class InputState(TypedDict):
    """Configuration injected before graph start."""
    repo_url: str
    pdf_paths: List[str]


class DetectiveState(TypedDict):
    """Output of the parallel detective nodes (fan-out → fan-in).

    evidence is Dict[dimension_id, Evidence] so each rubric dimension gets
    exactly one canonical Evidence entry.  operator.ior merges dicts from
    parallel branches (last writer wins per key).
    """
    evidence: Annotated[Dict[str, Evidence], operator.ior]
    repo_dir: Optional[str]
    errors: Annotated[List[str], operator.add]


class JudgeState(TypedDict):
    """Output of the judge nodes — one opinion per dimension."""
    opinions: Annotated[Dict[str, JudicialOpinion], operator.ior]


class VerdictState(TypedDict):
    """Terminal output produced by the Aggregator/Chief-Judge node."""
    verdict: Optional[FinalVerdict]


# ---------------------------------------------------------------------------
# Full composed graph state
# ---------------------------------------------------------------------------

class GraphState(InputState, DetectiveState, JudgeState, VerdictState):
    """Complete state flowing through the audit graph.

    Stages
    ------
    1. detectives  → populate DetectiveState.evidence  (fan-out / fan-in)
    2. judges      → populate JudgeState.opinions      (one per dimension)
    3. aggregator  → populate VerdictState.verdict
    """


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def initial_state(repo_url: str, pdf_paths: List[str] | None = None) -> GraphState:
    return GraphState(
        repo_url=repo_url,
        pdf_paths=pdf_paths or [],
        evidence={},
        repo_dir=None,
        errors=[],
        opinions={},
        verdict=None,
    )


# AgentState is the primary state used by the graph (aliased for requirements)
AgentState = GraphState


__all__ = [
    "Evidence", "JudicialOpinion", "FinalVerdict",
    "InputState", "DetectiveState", "JudgeState", "VerdictState",
    "GraphState", "AgentState", "initial_state",
]