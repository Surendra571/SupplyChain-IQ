"""SupplyChain IQ - Synthetic Data Generator CLI Entry Point."""

import sys
from pathlib import Path

# Ensure root on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_generator.generate import main, run_generation, compare_runs

if __name__ == "__main__":
    main()
