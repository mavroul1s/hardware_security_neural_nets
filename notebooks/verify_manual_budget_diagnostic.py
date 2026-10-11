"""Verify manually downloaded output against the nmavros account revision."""
from pathlib import Path
import verify_budget_diagnostic as verifier

if __name__ == '__main__':
    verifier.OUT = Path(__file__).resolve().parents[1]/'outputs/kaggle_budget_2026-10-11/manual'
    verifier.main()
