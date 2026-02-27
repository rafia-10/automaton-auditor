"""src/state.py — Rubric-compliant State Definitions."""
from __future__ import annotations

import operator
from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# --- Detective Output ---

class Evidence(BaseModel):
    """A single piece of forensic evidence collected by Detectives."""
    goal: str = Field(description="The specific goal this evidence addresses.")
    found: bool = Field(description="Whether the artifact exists.")
    content: Optional[str] = Field(default=None, description="The content of the evidence (e.g., code snippet).")
    location: str = Field(description="File path or commit hash.")
    rationale: str = Field(description="Rationale for confidence in the found evidence.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0 to 1.")

# --- Judge Output ---

class JudicialOpinion(BaseModel):
    """A structured opinion from one of the three judges."""
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str = Field(description="ID of the rubric criterion being judged.")
    score: int = Field(ge=1, le=5, description="Score from 1 to 5.")
    argument: str = Field(description="Detailed reasoning for the score.")
    cited_evidence: List[str] = Field(default_factory=list, description="List of location strings linked to evidence.")

# --- Chief Justice Output ---

class CriterionResult(BaseModel):
    """Final result for a specific rubric dimension."""
    dimension_id: str
    dimension_name: str
    final_score: int = Field(ge=1, le=5)
    judge_opinions: List[JudicialOpinion]
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Required when score variance > 2",
    )
    remediation: str = Field(
        description="Specific file-level instructions for improvement",
    )

class AuditReport(BaseModel):
    """The final synthesized audit report."""
    repo_url: str
    executive_summary: str
    overall_score: float
    criteria: List[CriterionResult]
    remediation_plan: str

# --- Graph State ---

class AgentState(TypedDict):
    """The complete state for the Automaton Auditor swarm."""
    repo_url: str
    pdf_path: str
    rubric_dimensions: List[Dict]
    # Use reducers to prevent parallel agents from overwriting data
    evidences: Annotated[
        Dict[str, List[Evidence]], operator.ior
    ]
    opinions: Annotated[
        List[JudicialOpinion], operator.add
    ]
    final_report: Optional[AuditReport]
    errors: Annotated[List[str], operator.add]

def initial_state(repo_url: str, pdf_path: str, rubric_dimensions: List[Dict] | None = None) -> AgentState:
    return {
        "repo_url": repo_url,
        "pdf_path": pdf_path,
        "rubric_dimensions": rubric_dimensions or [],
        "evidences": {},
        "opinions": [],
        "final_report": None,
        "errors": []
    }

__all__ = [
    "Evidence", "JudicialOpinion", "CriterionResult", 
    "AuditReport", "AgentState", "initial_state"
]