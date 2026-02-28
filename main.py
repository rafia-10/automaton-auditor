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
        pdf_path=pdf_path
    )
    
    print(f"Running graph for: {repo_url}")
    print(f"Analyzing report: {pdf_path}")
    
    try:
        # Execute the graph
        final_state = audit_graph.invoke(state)
        
        print("\nAudit Complete!")
        report = final_state.get("final_report")
        if report:
            print(f"Overall Score: {report.overall_score:.2f}")
            print(f"Summary: {report.executive_summary}")
            print("\nAudit report generated in audit/report_onself_generated/report.md")
        
        print("\nTrace should be captured in LangSmith (check your dashboard).")
        
    except Exception as e:
        print(f"Audit Execution Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
