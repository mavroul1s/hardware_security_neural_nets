"""Verify the single nmavros API run against its frozen account revision."""
from pathlib import Path
import verify_budget_diagnostic as verifier

if __name__ == '__main__':
    verifier.OUT = Path(__file__).resolve().parents[1]/'outputs/kaggle_budget_2026-10-11/api'
    verifier.main()
