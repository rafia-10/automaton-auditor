from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    FAILED = "failed"


class Evidence(BaseModel):
    """Represents a piece of evidence collected by the auditor.

    Keep this model small and serializable so it can be persisted or
    passed between agents.
    """

    id: str
    source: str
    kind: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JudicialOpinion(BaseModel):
    """A synthesized opinion produced after analyzing evidence.

    Uses `evidence_ids` to refer to `Evidence` instances stored elsewhere.
    """

    id: str
    evidence_ids: List[str] = Field(default_factory=list)
    verdict: str
    rationale: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Lightweight runtime state for an agent/detector node.

    This contains ephemeral runtime fields and a small durable memory of
    observed evidence references and opinions.
    """

    id: str
    name: str
    status: AgentStatus = AgentStatus.IDLE
    memory_evidence_ids: List[str] = Field(default_factory=list)
    opinions_ids: List[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    config: Dict[str, Any] = Field(default_factory=dict)

    def add_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.memory_evidence_ids:
            self.memory_evidence_ids.append(evidence_id)
            self.touch()

    def add_opinion(self, opinion_id: str) -> None:
        if opinion_id not in self.opinions_ids:
            self.opinions_ids.append(opinion_id)
            self.touch()

    def touch(self) -> None:
        self.last_seen = datetime.utcnow()


__all__ = ["Evidence", "JudicialOpinion", "AgentState", "AgentStatus"]
