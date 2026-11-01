"""SupplyChain IQ - Database Schema Initialization Script."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.scripts.init_db import main

if __name__ == "__main__":
    main()

