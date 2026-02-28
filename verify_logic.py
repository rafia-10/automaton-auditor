import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Mock Environment for Local Logic Test
os.environ["OPENAI_API_KEY"] = "sk-mock-key"

from src.state import initial_state, Evidence, JudicialOpinion
from src.nodes.optimizers import min_max_optimizer
from src.nodes.justice import chief_justice_node

def test_logic():
    print("Starting Logic Verification (Dry Run)...")
    
    # 1. Setup State
    state = initial_state(repo_url="https://github.com/test/repo", pdf_path="test.pdf")
    
    # 2. Inject Mock Evidence
    state["evidences"] = {
        "git_forensic_analysis": [Evidence(goal="Git", found=True, location="git", rationale="history ok", confidence=1.0)],
        "state_management_rigor": [Evidence(goal="State", found=True, location="state.py", rationale="Pydantic found", confidence=1.0, content="BaseModel operator.add")],
        "safe_tool_engineering": [Evidence(goal="Safety", found=False, location="tools/", rationale="os.system detected", confidence=1.0, content="os.system('rm -rf')")],
    }
    
    # 3. Inject Mock Opinions
    state["opinions"] = [
        # Dimension: Git
        JudicialOpinion(judge="Prosecutor", criterion_id="git_forensic_analysis", score=2, argument="Too few commits."),
        JudicialOpinion(judge="Defense", criterion_id="git_forensic_analysis", score=5, argument="Quality over quantity."),
        JudicialOpinion(judge="TechLead", criterion_id="git_forensic_analysis", score=4, argument="Clean history."),
        
        # Dimension: Safety (Critical Failure)
        JudicialOpinion(judge="Prosecutor", criterion_id="safe_tool_engineering", score=1, argument="Critical security flaw!"),
        JudicialOpinion(judge="Defense", criterion_id="safe_tool_engineering", score=2, argument="Easily fixed."),
        JudicialOpinion(judge="TechLead", criterion_id="safe_tool_engineering", score=1, argument="Unacceptable risk."),
    ]
    
    # 4. Run Optimizer
    print("Running MinMaxOptimizer...")
    opt_result = min_max_optimizer(state)
    state.update(opt_result)
    print(f"Flaws Detected: {state['architectural_flaws']}")
    
    # 5. Run Chief Justice
    print("Running Chief Justice Synthesis...")
    justice_result = chief_justice_node(state)
    report = justice_result["final_report"]
    
    # 6. Verify Report
    print("\n--- AUDIT REPORT SUMMARY ---")
    print(f"Overall Score: {report.overall_score}")
    print(f"Summary: {report.executive_summary[:100]}...")
    print(f"Remediation Items: {len(report.remediation_plan)}")
    
    # Check if file was written
    report_path = Path("audit/report_onself_generated/report.md")
    if report_path.exists():
        print(f"\nSUCCESS: Report generated at {report_path}")
    else:
        print("\nFAILURE: Report file not found.")

if __name__ == "__main__":
    test_logic()
