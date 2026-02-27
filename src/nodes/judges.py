"""src/nodes/judges.py — Judicial Persona Nodes using LLMs."""
from __future__ import annotations
import os
from typing import Any, List
from langsmith import traceable
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..state import AgentState, JudicialOpinion, Evidence

# --- LLM Setup ---

def get_model():
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = None
    model_name = "gpt-4o"
    if api_key.startswith("sk-or-v1"):
        base_url = "https://openrouter.ai/api/v1"
        model_name = "google/gemma-3-4b-it:free"
    
    return ChatOpenAI(
        model=model_name, 
        temperature=0, 
        openai_api_key=api_key,
        base_url=base_url,
        max_tokens=500
    ).with_structured_output(JudicialOpinion)

# --- Prosecutor ---

PROSECUTOR_PROMPT = """You are the PROSECUTOR in a Digital Courtroom.
Your philosophy is: "Trust No One. Assume Vibe Coding."
Your goal is to scrutinize evidence for gaps, security flaws, laziness, and bypassed structure.
If the evidence shows linear pipelines where parallelism was requested, charge "Orchestration Fraud".
If Judge nodes return freeform text, charge "Hallucination Liability".
Always look for the worst-case interpretation of the evidence.

Dimension being judged: {dimension_name}
Collected Evidence:
{evidence_content}

Render your verdict as a JudicialOpinion."""

@traceable(name="Prosecutor")
def prosecutor_node(state: AgentState) -> dict:
    model = get_model()
    prompt = ChatPromptTemplate.from_template(PROSECUTOR_PROMPT)
    chain = prompt | model
    
    new_opinions = []
    for dim_id, ev_list in state["evidences"].items():
        ev = ev_list[0] # Take first canonical evidence
        opinion = chain.invoke({
            "dimension_name": dim_id,
            "evidence_content": ev.content
        })
        opinion.judge = "Prosecutor"
        opinion.criterion_id = dim_id
        new_opinions.append(opinion)
    
    return {"opinions": new_opinions}

# --- Defense ---

DEFENSE_PROMPT = """You are the DEFENSE ATTORNEY in a Digital Courtroom.
Your philosophy is: "Reward Effort and Intent. Look for the 'Spirit of the Law'."
Your goal is to highlight creative workarounds, deep thought, and engineering process.
Even if the code is buggy, if the architecture shows deep understanding, argue for a "Master Thinker" profile.
Highlight strengths and mitigate failures as "learning iterations" or "syntactic hurdles".

Dimension being judged: {dimension_name}
Collected Evidence:
{evidence_content}

Render your verdict as a JudicialOpinion."""

@traceable(name="Defense")
def defense_node(state: AgentState) -> dict:
    model = get_model()
    prompt = ChatPromptTemplate.from_template(DEFENSE_PROMPT)
    chain = prompt | model
    
    new_opinions = []
    for dim_id, ev_list in state["evidences"].items():
        ev = ev_list[0]
        opinion = chain.invoke({
            "dimension_name": dim_id,
            "evidence_content": ev.content
        })
        opinion.judge = "Defense"
        opinion.criterion_id = dim_id
        new_opinions.append(opinion)
    
    return {"opinions": new_opinions}

# --- Tech Lead ---

TECHLEAD_PROMPT = """You are the TECH LEAD in a Digital Courtroom.
Your philosophy is: "Does it actually work? Is it maintainable?"
Your goal is to evaluate architectural soundness, code cleanliness, and practical viability.
Ignore "Vibe" or "Struggle". Focus on technical debt.
Is the operator.add reducer used? Are tool calls isolated?
You are the pragmatic tie-breaker between Prosecutor and Defense.

Dimension being judged: {dimension_name}
Collected Evidence:
{evidence_content}

Render your verdict as a JudicialOpinion."""

@traceable(name="TechLead")
def tech_lead_node(state: AgentState) -> dict:
    model = get_model()
    prompt = ChatPromptTemplate.from_template(TECHLEAD_PROMPT)
    chain = prompt | model
    
    new_opinions = []
    for dim_id, ev_list in state["evidences"].items():
        ev = ev_list[0]
        opinion = chain.invoke({
            "dimension_name": dim_id,
            "evidence_content": ev.content
        })
        opinion.judge = "TechLead"
        opinion.criterion_id = dim_id
        new_opinions.append(opinion)
    
    return {"opinions": new_opinions}

__all__ = ["prosecutor_node", "defense_node", "tech_lead_node"]
