# Automaton Auditor

> **Week 2 TRP project** — A multi-agent system that audits GitHub repositories and PDF reports using LangGraph.

## Architecture

```
          ┌──────────────────────────────────────────────────┐
          │                   START                          │
          └──────────────┬───────────────────┬──────────────┘
                         │                   │
                         ▼                   ▼
             ┌─────────────────┐   ┌──────────────────┐
             │ RepoInvestigator│   │   DocAnalyst     │  ← parallel (fan-out)
             │                 │   │                  │
             │ • git clone     │   │ • load PDF       │
             │ • git log       │   │ • chunk text     │
             │ • AST analysis  │   │ • TF-IDF query   │
             └────────┬────────┘   └────────┬─────────┘
                      │                     │
                      └──────────┬──────────┘
                                 ▼
                    ┌────────────────────────┐
                    │  EvidenceAggregator    │  ← fan-in (operator.add merge)
                    └────────────────────────┘
                                 │
                                 ▼
                                END
```

## Project Structure

```
automaton-auditor/
├── src/
│   ├── __init__.py
│   ├── models.py          # Pydantic: Evidence, JudicialOpinion, AgentState
│   ├── state.py           # LangGraph GraphState TypedDict with reducers
│   ├── graph.py           # Compiled audit_graph (fan-out → fan-in)
│   ├── nodes/
│   │   ├── __init__.py
│   │   └── detectives.py  # repo_investigator + doc_analyst LangGraph nodes
│   └── tools/
│       ├── __init__.py
│       ├── repo_tools.py  # Sandboxed git clone, git log, AST graph
│       └── doc_tools.py   # PDF ingestion, chunker, TF-IDF retrieval
├── reports/               # Commit PDF reports here
├── pyproject.toml
├── .env.example
└── README.md
```

## Setup

### Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `git` on `$PATH`

### Install dependencies

```bash
# Clone this repo
git clone https://github.com/<your-org>/automaton-auditor.git
cd automaton-auditor

# Install all dependencies (creates .venv automatically)
uv sync

# (Optional) install dev dependencies
uv sync --extra dev
```

### Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

The only *required* key for the skeleton to run (no LLM nodes yet) is `GITHUB_TOKEN` (optional, increases rate limits).  Set `OPENAI_API_KEY` when you add LLM-based judge nodes.

## Running the Detective Graph

### Quickstart

```bash
# Audit a public GitHub repo (no PDFs)
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from src.graph import audit_graph
from src.state import initial_state

result = audit_graph.invoke(
    initial_state('https://github.com/langchain-ai/langgraph')
)
print(result['summary'])
"
```

### With PDF reports

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from src.graph import audit_graph
from src.state import initial_state

result = audit_graph.invoke(
    initial_state(
        repo_url='https://github.com/langchain-ai/langgraph',
        pdf_paths=['reports/interim_report.pdf'],
    )
)
print(result['summary'])
for ev in result['evidence']:
    print(f'  [{ev.kind}] {ev.source[:60]}')
"
```

### Streaming

```bash
uv run python -c "
from dotenv import load_dotenv; load_dotenv()
from src.graph import audit_graph
from src.state import initial_state

for chunk in audit_graph.stream(initial_state('https://github.com/langchain-ai/langgraph')):
    print(chunk)
"
```

## Development

```bash
# Lint
uv run ruff check src/

# Type-check
uv run mypy src/

# Tests
uv run pytest
```

## State Model

| Field        | Type                        | Reducer       | Description                          |
|--------------|-----------------------------|---------------|--------------------------------------|
| `repo_url`   | `str`                       | last-write    | Target GitHub URL                    |
| `pdf_paths`  | `list[str]`                 | last-write    | Paths to PDF reports                 |
| `repo_dir`   | `str \| None`               | last-write    | Temporary clone directory            |
| `evidence`   | `list[Evidence]`            | `operator.add`| Merged evidence from all detectives  |
| `opinions`   | `list[JudicialOpinion]`     | `operator.add`| Judge outputs (Week 3)               |
| `errors`     | `list[str]`                 | `operator.add`| Non-fatal errors from any node       |
| `summary`    | `str \| None`               | last-write    | Aggregator summary text              |

## Extending

- **Add a Judge node**: create `src/nodes/judges.py`, wire it after `evidence_aggregator`
- **Upgrade retrieval**: replace `query_chunks` in `doc_tools.py` with OpenAI embeddings + FAISS
- **Add LLM synthesis**: call `langchain_openai.ChatOpenAI` inside any node; state is already LangSmith-traceable
