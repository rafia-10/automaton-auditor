# Automaton Auditor

> **Week 2 TRP project** — A production-grade multi-agent swarm for code governance and repository auditing.

## Architecture

The system uses a hierarchical **Fan-Out/Fan-In** pattern implemented with LangGraph:

1.  **Detectives (Fan-Out)**: `RepoInvestigator`, `DocAnalyst`, and `VisionInspector` run in parallel to gather forensic evidence.
2.  **Judges (Fan-Out)**: `Prosecutor`, `Defense`, and `TechLead` personas evaluate the evidence from conflicting perspectives.
3.  **Supreme Court (Fan-In)**: The `ChiefJustice` synthesizes final verdicts using deterministic conflict-resolution rules.

## Core Features

-   **10-Dimension Forensic Suite**: Audits Git progression, state rigor, graph architecture, security safety, and theoretical depth.
-   **Dialectical Synthesis**: Resolves conflicts between adversarial agents (Prosecutor vs. Defense).
-   **Deterministic Scoring**: Weighted scoring (Tech Lead 2x) and security overrides for reliable governance.
-   **LangSmith Traceability**: Full observability into the swarm's decision-making process.

## Setup

1.  **Install Dependencies**:
    ```bash
    uv sync
    ```
2.  **Configure Environment**:
    ```bash
    cp .env.example .env
    # Add your OPENAI_API_KEY (supports OpenRouter endpoints)
    ```

## Usage Entry Points

### 1. Live Audit (`main.py`)
Run the full live audit on the configured repository. This requires active LLM credits.
```bash
uv run python3 main.py
```

### 2. Logic Verification (`verify_logic.py`)
Test the entire workflow's synthesis and reporting logic using mock data. **Recommended for quick validation without API costs.**
```bash
uv run python3 verify_logic.py
```

## Output
Audit reports are generated in Markdown format at:
`audit/report_onself_generated/report.md`

Includes:
- Executive Summary (Metacognition & Dialectical Synthesis)
- Overall Compliance Score
- Dissenting Opinions & Detailed Logic
- Remediation Plan
