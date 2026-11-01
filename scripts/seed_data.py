"""SupplyChain IQ - Database Seeder Script.

Loads master, transactional, and event datasets from data/generated/ into PostgreSQL.
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_data")


def seed_database(scale: str = "starter"):
    sql_path = REPO_ROOT / "data" / "generated" / scale / "sql" / "insert_all.sql"
    if not sql_path.exists():
        logger.error(f"SQL seed file not found at: {sql_path}")
        return False

    logger.info(f"Reading SQL seed file from {sql_path}...")
    sql_content = sql_path.read_text(encoding="utf-8")

    logger.info("Connecting to database and executing batch inserts...")
    with engine.connect() as conn:
        with conn.begin():
            statements = [stmt.strip() for stmt in sql_content.split(";\n") if stmt.strip()]
            for i, stmt in enumerate(statements):
                conn.execute(text(stmt))
                if i % 100 == 0:
                    logger.info(f"  Executed {i}/{len(statements)} statements...")

    logger.info("Database seeding completed successfully!")
    return True


if __name__ == "__main__":
    scale_arg = sys.argv[1] if len(sys.argv) > 1 else "starter"
    seed_database(scale_arg)

