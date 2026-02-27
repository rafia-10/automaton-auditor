import os
import sys
from dotenv import load_dotenv

# Load .env first
load_dotenv()

from src.graph import audit_graph
from src.state import initial_state

def run():
    print("Initalizing Week 2 Audit...")
    
    # Input Configuration
    repo_url = "https://github.com/rafia-10/automaton-auditor"
    pdf_path = "reports/interim_report.pdf"
    
    # Construct initial state
    state = initial_state(
        repo_url=repo_url,
        pdf_paths=[pdf_path]
    )
    
    print(f"Running graph for: {repo_url}")
    print(f"Analyzing report: {pdf_path}")
    
    try:
        # Execute the graph
        # Using .invoke() as per LangGraph 0.2+ standards
        final_state = audit_graph.invoke(state)
        
        print("\nAudit Complete!")
        verdict = final_state.get("verdict")
        if verdict:
            print(f"Overall Score: {verdict.overall_score:.2f}")
            print(f"Passed: {verdict.passed}")
            print(f"Summary: {verdict.summary}")
            print(f"Dissent: {verdict.dissent_summary}")
        
        print("\nTrace should be captured in LangSmith (check your dashboard).")
        
    except Exception as e:
        print(f"Audit Execution Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
